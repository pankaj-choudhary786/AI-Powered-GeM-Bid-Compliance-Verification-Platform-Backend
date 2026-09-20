# app/api/routes/documents.py
import json
from typing import Optional
from fastapi import APIRouter, Depends, UploadFile, File, Form, status, HTTPException, BackgroundTasks
from sqlalchemy.orm import Session

from app.db.database import get_db, SessionLocal
from app.db.schemas import DocumentUploadResponse, UserRole
from app.db.models import User
from app.services.document_service import upload_document
from app.api.deps import require_role
from app.services.document_processing_service import process_and_extract_document

router = APIRouter()


def _run_background_pipeline(doc_id):
    """Executes the heavy AI preprocessing & OCR in an isolated database session."""
    bg_db = SessionLocal()
    try:
        process_and_extract_document(bg_db, doc_id)
    except Exception as e:
        print(f"[!] AI Document Extraction Pipeline Error for Document ID {doc_id}: {e}")
    finally:
        bg_db.close()


@router.post("/upload", response_model=DocumentUploadResponse, status_code=status.HTTP_201_CREATED)
def upload_evidence_file(
    background_tasks: BackgroundTasks,
    application_id: str = Form(...),
    requirement_id: str = Form(...),
    metadata_json: Optional[str] = Form(None, description="Stringified JSON for custom doc types"),
    file: UploadFile = File(...),
    db: Session = Depends(get_db),
    current_user: User = Depends(require_role([UserRole.BIDDER]))
):
    """Securely uploads, hashes, and attaches evidence to an application,
    then automatically triggers OpenCV enhancement and PaddleOCR in the background."""
    
    # 1. Validate custom metadata JSON if provided
    if metadata_json:
        try:
            json.loads(metadata_json)
        except json.JSONDecodeError:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST, 
                detail="metadata_json must be a valid JSON string"
            )

    # 2. Save physical file and record in database
    uploaded_doc = upload_document(db, current_user, file, application_id, requirement_id, metadata_json)

    # 3. Safely extract ID (handles both dict and ORM model instances)
    if isinstance(uploaded_doc, dict):
        doc_id = uploaded_doc.get("id") or uploaded_doc.get("document_id")
    else:
        doc_id = getattr(uploaded_doc, "id", None) or getattr(uploaded_doc, "document_id", None)

    # 4. Schedule the AI Pipeline
    if doc_id is not None:
        background_tasks.add_task(_run_background_pipeline, doc_id)
    else:
        print("[!] Warning: doc_id was None, background task was not scheduled.")

    return uploaded_doc