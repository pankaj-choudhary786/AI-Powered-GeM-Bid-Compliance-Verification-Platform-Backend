# app/api/routes/documents.py
from fastapi import APIRouter, Depends, UploadFile, File, Form, status, HTTPException
from sqlalchemy.orm import Session
from typing import Optional
import json
from app.db.database import get_db
from app.db.schemas import DocumentUploadResponse, UserRole
from app.db.models import User
from app.services.document_service import upload_document
from app.api.deps import require_role

router = APIRouter()

@router.post("/upload", response_model=DocumentUploadResponse, status_code=status.HTTP_201_CREATED)
def upload_evidence_file(
    application_id: str = Form(...),
    requirement_id: str = Form(...),
    metadata_json: Optional[str] = Form(None, description="Stringified JSON for custom doc types"),
    file: UploadFile = File(...),
    db: Session = Depends(get_db),
    current_user: User = Depends(require_role([UserRole.BIDDER]))
):
    """Securely uploads, hashes, and attaches evidence to an application."""
    if metadata_json:
        try:
            json.loads(metadata_json)
        except json.JSONDecodeError:
            raise HTTPException(status_code=400, detail="metadata_json must be a valid JSON string")
            
    return upload_document(db, current_user, file, application_id, requirement_id, metadata_json)