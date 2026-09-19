# app/services/tender_service.py
from sqlalchemy.orm import Session
from fastapi import HTTPException, status
from datetime import datetime, timezone
import uuid
from app.db.models import Tender, TenderRequirement, User, TenderCreatorProfile, BidderProfile, BidSubmission
from app.db.schemas import TenderCreateRequest, ApplicationCreateRequest
from app.core.exceptions import RoleMismatchException

def _generate_id(prefix: str) -> str:
    year = datetime.now(timezone.utc).year
    random_hex = uuid.uuid4().hex[:6].upper()
    return f"{prefix}-{year}-{random_hex}"

def create_tender(db: Session, current_user: User, tender_data: TenderCreateRequest):
    creator_profile = db.query(TenderCreatorProfile).filter(TenderCreatorProfile.user_id == current_user.id).first()
    if not creator_profile:
        raise RoleMismatchException(expected_role="TENDER_CREATOR", actual_role=current_user.role)

    new_tender = Tender(
        tender_id=_generate_id("TND"),
        creator_id=creator_profile.id,
        title=tender_data.title,
        description=tender_data.description,
        category=tender_data.category,
        location=tender_data.location,
        bid_deadline=tender_data.bid_deadline,
        application_capacity=tender_data.application_capacity,
        status="PUBLISHED",
        publish_date=datetime.now(timezone.utc)
    )
    db.add(new_tender)
    db.flush() 

    for req in tender_data.requirements:
        new_req = TenderRequirement(
            requirement_id=_generate_id("REQ"),
            tender_id=new_tender.id,
            requirement_name=req.requirement_name,
            description=req.description,
            mandatory=req.mandatory,
            evidence_type=req.evidence_type,
            accepted_formats=req.accepted_formats,
            validation_rule_type=req.validation_rule_type,
            operator=req.operator,
            required_value=req.required_value,
            unit=req.unit,
            weight=req.weight,
            display_order=req.display_order
        )
        db.add(new_req)

    db.commit()
    db.refresh(new_tender)
    
    # Compute schema counters dynamically
    new_tender.total_requirements = len(new_tender.requirements)
    new_tender.mandatory_requirements = sum(1 for r in new_tender.requirements if r.mandatory)
    
    return new_tender

def create_bid_submission(db: Session, current_user: User, request: ApplicationCreateRequest):
    bidder_profile = db.query(BidderProfile).filter(BidderProfile.user_id == current_user.id).first()
    if not bidder_profile:
        raise RoleMismatchException(expected_role="BIDDER", actual_role=current_user.role)

    tender = db.query(Tender).filter(Tender.tender_id == request.tender_id).first()
    if not tender:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Tender not found.")

    if tender.status != "PUBLISHED":
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Tender is not currently accepting bids.")

    # Check for duplicate applications
    existing_submission = db.query(BidSubmission).filter(
        BidSubmission.tender_id == tender.id,
        BidSubmission.bidder_id == bidder_profile.id
    ).first()
    if existing_submission:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="You have already submitted an application for this tender.")

    # Crash-Test Lab: Atomic capacity check
    current_applications = db.query(BidSubmission).filter(BidSubmission.tender_id == tender.id).count()
    if current_applications >= tender.application_capacity:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=f"Capacity reached. Tender is limited to {tender.application_capacity} applications.")

    new_submission = BidSubmission(
        application_id=_generate_id("APP"),
        bidder_id=bidder_profile.id,
        tender_id=tender.id,
        status="DRAFT"
    )
    
    db.add(new_submission)
    db.commit()
    db.refresh(new_submission)
    return new_submission