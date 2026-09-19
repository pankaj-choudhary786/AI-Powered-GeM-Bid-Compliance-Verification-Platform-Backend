# app/api/routes/submissions.py
from fastapi import APIRouter, Depends, status
from sqlalchemy.orm import Session
from app.db.database import get_db
from app.db.schemas import ApplicationCreateRequest, ApplicationResponse, UserRole
from app.db.models import User
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