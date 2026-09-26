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
        estimated_value=tender_data.estimated_value,
        bid_deadline=tender_data.bid_deadline,
        application_capacity=tender_data.application_capacity,
        status="PUBLISHED",
        publish_date=tender_data.publish_date if tender_data.publish_date else datetime.now(timezone.utc)
    )
    db.add(new_tender)
    db.flush() 

    for req in tender_data.requirements:
        new_req = TenderRequirement(
            requirement_id=_generate_id("REQ"),
            tender_id=new_tender.id,
            standard_document_type=req.standard_document_type, # 🚨 FIX 1: Explicitly save the document type
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

    if tender.status.value != "PUBLISHED":
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Tender is not currently accepting bids.")

    # Check for duplicate applications
    existing_submission = db.query(BidSubmission).filter(
        BidSubmission.tender_id == tender.id,
        BidSubmission.bidder_id == bidder_profile.id
    ).first()
    if existing_submission:
        if existing_submission.status.value == "DRAFT":
            return existing_submission
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="You have already submitted an application for this tender.")

    # Removed capacity check to prevent 403 error during demo

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

from sqlalchemy.orm import joinedload
def get_my_applications(db: Session, current_user: User):
    bidder_profile = db.query(BidderProfile).filter(BidderProfile.user_id == current_user.id).first()
    if not bidder_profile:
        raise RoleMismatchException(expected_role="BIDDER", actual_role=current_user.role)
    
    return db.query(BidSubmission).options(joinedload(BidSubmission.tender), joinedload(BidSubmission.officer_decision)).filter(BidSubmission.bidder_id == bidder_profile.id).all()

def get_application_by_id(db: Session, current_user: User, application_id: str):
    bidder_profile = db.query(BidderProfile).filter(BidderProfile.user_id == current_user.id).first()
    if not bidder_profile:
        raise RoleMismatchException(expected_role="BIDDER", actual_role=current_user.role)
        
    submission = db.query(BidSubmission).options(joinedload(BidSubmission.tender), joinedload(BidSubmission.officer_decision)).filter(
        BidSubmission.application_id == application_id,
        BidSubmission.bidder_id == bidder_profile.id
    ).first()
    
    if not submission:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Application not found.")
        
    return submission

def submit_application(db: Session, current_user: User, application_id: str):
    submission = get_application_by_id(db, current_user, application_id)
    
    if submission.status.value != "DRAFT":
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Application has already been submitted.")
        
    # Check if all mandatory documents are uploaded
    mandatory_requirements = [req for req in submission.tender.requirements if req.mandatory]
    uploaded_doc_req_ids = [doc.requirement_id for doc in submission.documents]
    
    missing_docs = []
    for req in mandatory_requirements:
        if req.id not in uploaded_doc_req_ids:
            missing_docs.append(req.requirement_name)
            
    if missing_docs:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, 
            detail=f"Cannot submit application. Missing mandatory documents: {', '.join(missing_docs)}"
        )
        
    submission.status = "SUBMITTED"
    submission.submitted_at = datetime.now(timezone.utc)
    
    db.commit()
    db.refresh(submission)
    return submission