# app/api/routes/verifications.py
from fastapi import APIRouter, Depends, status
from sqlalchemy.orm import Session
from app.db.database import get_db
from app.db.models import User
from app.db.schemas import UserRole
from app.api.deps import require_role
from app.services.government_verification_service import run_government_verification

router = APIRouter()

@router.post("/api/verifications/documents/{application_id}")
def verify_documents_against_government_data(application_id: str, db: Session = Depends(get_db)):
    # 1. Run OCR on all documents linked to the application
    ocr_results = run_ocr_pipeline(db, application_id)
    
    # 2. Cross-match OCR results against the government source records
    match_results = execute_cross_document_matching(db, application_id)
    
    return {
        "status": "COMPLETED",
        "documents_processed": len(ocr_results),
        "matches_found": match_results
    }