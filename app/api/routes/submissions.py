# app/api/routes/submissions.py
from fastapi import APIRouter, Depends, status
from sqlalchemy.orm import Session
from app.db.database import get_db
from app.db.schemas import ApplicationCreateRequest, ApplicationResponse, UserRole
from app.db.models import User
from app.services.tender_service import create_bid_submission
from app.api.deps import require_role

router = APIRouter()

from typing import List

@router.post("/", response_model=ApplicationResponse, status_code=status.HTTP_201_CREATED)
def initiate_application(
    request: ApplicationCreateRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_role([UserRole.BIDDER]))
):
    from app.services.tender_service import create_bid_submission
    return create_bid_submission(db, current_user, request)

@router.get("/me", response_model=List[ApplicationResponse])
def get_my_applications_route(
    db: Session = Depends(get_db),
    current_user: User = Depends(require_role([UserRole.BIDDER]))
):
    from app.services.tender_service import get_my_applications
    return get_my_applications(db, current_user)

@router.get("/{application_id}", response_model=ApplicationResponse)
def get_application_route(
    application_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_role([UserRole.BIDDER]))
):
    from app.services.tender_service import get_application_by_id
    return get_application_by_id(db, current_user, application_id)

@router.post("/{application_id}/submit", response_model=ApplicationResponse)
def submit_application_route(
    application_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_role([UserRole.BIDDER]))
):
    from app.services.tender_service import submit_application
    return submit_application(db, current_user, application_id)