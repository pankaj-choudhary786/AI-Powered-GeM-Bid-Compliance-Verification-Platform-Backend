# app/api/routes/submissions.py
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from app.db.database import get_db
from app.db.schemas import (
    ApplicationCreateRequest, 
    ApplicationResponse, 
    UserRole, 
    ApplicationDashboardResponse, 
    ApplicationStatus
)
from app.db.models import User, BidSubmission
from app.services.tender_service import create_bid_submission
from app.api.deps import require_role

router = APIRouter()

@router.post("/", response_model=ApplicationResponse, status_code=status.HTTP_201_CREATED)
def initiate_application(
    request: ApplicationCreateRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_role([UserRole.BIDDER]))
):
    return create_bid_submission(db, current_user, request)


@router.get("/{application_id}", response_model=ApplicationDashboardResponse, status_code=status.HTTP_200_OK)
def get_application_dashboard(
    application_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_role([UserRole.BIDDER, UserRole.PROCUREMENT_OFFICER]))
):
    """
    Fetches the complete dashboard view for a specific application.
    """
    submission = db.query(BidSubmission).filter(BidSubmission.application_id == application_id).first()
    
    if not submission:
        raise HTTPException(status_code=404, detail="Application not found")

    # Security Guard: A Bidder can only view their own submissions
    if current_user.role == UserRole.BIDDER and submission.bidder.user_id != current_user.id:
        raise HTTPException(status_code=403, detail="Access denied. This is not your application.")

    # 🚨 AI RECOMMENDATION MASKING LOGIC 🚨
    # By default, we hide the recommendations (empty list)
    visible_recommendations = []
    
    # We only reveal them IF the Officer has made a final decision, OR if the user is the Officer.
    if submission.status == ApplicationStatus.DECIDED or current_user.role == UserRole.PROCUREMENT_OFFICER:
        visible_recommendations = submission.ai_recommendations

    return {
        "application_id": submission.application_id,
        "display_id": submission.display_id,
        "application_status": submission.status,
        "submitted_at": submission.submitted_at,
        "tender": submission.tender,
        "bidder": submission.bidder,
        "requirements_analysis": [], 
        "cross_document_findings": submission.cross_document_findings,
        "government_verifications": submission.government_verifications,
        "ai_recommendations": visible_recommendations,  
        "decision": submission.officer_decision,
        "audit_trail": [] 
    }