# app/api/routes/tenders.py
from fastapi import APIRouter, Depends, status
from sqlalchemy.orm import Session
from typing import List
from app.db.database import get_db
from app.db.schemas import TenderCreateRequest, TenderResponse, UserRole
from app.db.models import User, Tender
from app.services.tender_service import create_tender
from app.api.deps import require_role

router = APIRouter()

@router.post("/", response_model=TenderResponse, status_code=status.HTTP_201_CREATED)
def publish_tender(
    request: TenderCreateRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_role([UserRole.TENDER_CREATOR]))
):
    return create_tender(db, current_user, request)

@router.get("/me", response_model=List[TenderResponse])
def get_my_tenders(
    db: Session = Depends(get_db),
    current_user: User = Depends(require_role([UserRole.TENDER_CREATOR]))
):
    if not current_user.tender_creator_profile:
        return []
        
    from app.db.models import BidSubmission
    tenders = db.query(Tender).filter(Tender.creator_id == current_user.tender_creator_profile.id).all()
    for t in tenders:
        t.total_requirements = len(t.requirements)
        t.mandatory_requirements = sum(1 for r in t.requirements if r.mandatory)
        t.bidders = db.query(BidSubmission).filter(BidSubmission.tender_id == t.id, BidSubmission.status != "DRAFT").count()
    return tenders

@router.get("/", response_model=List[TenderResponse])
def get_all_tenders(status_filter: str = None, db: Session = Depends(get_db)):
    from app.db.models import BidSubmission
    from datetime import datetime
    
    query = db.query(Tender)
    now = datetime.utcnow()
    
    if status_filter == "upcoming":
        query = query.filter(Tender.publish_date != None, Tender.publish_date > now)
    elif status_filter == "current":
        query = query.filter((Tender.publish_date == None) | (Tender.publish_date <= now))
        query = query.filter((Tender.bid_deadline == None) | (Tender.bid_deadline >= now))
        
    tenders = query.all()
    for t in tenders:
        t.total_requirements = len(t.requirements)
        t.mandatory_requirements = sum(1 for r in t.requirements if r.mandatory)
        t.bidders = db.query(BidSubmission).filter(BidSubmission.tender_id == t.id, BidSubmission.status != "DRAFT").count()
    return tenders