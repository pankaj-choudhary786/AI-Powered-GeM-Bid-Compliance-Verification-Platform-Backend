# app/services/document_service.py
import os
import shutil
import hashlib
import uuid
import json
from datetime import datetime, timezone
from fastapi import UploadFile, HTTPException, status
from sqlalchemy.orm import Session
from app.db.models import BidderDocument, BidSubmission, TenderRequirement, BidderProfile, User
from app.core.exceptions import RoleMismatchException

UPLOAD_DIR = "storage/bidder_documents"
ALLOWED_MIME_TYPES = {"application/pdf", "image/jpeg", "image/png"}
MAX_FILE_SIZE_BYTES = 10 * 1024 * 1024  # 10 MB

os.makedirs(UPLOAD_DIR, exist_ok=True)

def upload_document(db: Session, current_user: User, file: UploadFile, application_id: str, requirement_id: str, metadata_string: str = None):
    # 1. PERIMETER VALIDATION
    if file.content_type not in ALLOWED_MIME_TYPES:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=f"Rejected: {file.content_type}. Only PDF, JPG, and PNG allowed.")

    file.file.seek(0, 2)
    file_size = file.file.tell()
    file.file.seek(0)
    
    if file_size > MAX_FILE_SIZE_BYTES:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="File exceeds 10MB limit.")

    # 2. VERIFY BIDDER & APPLICATION
    bidder = db.query(BidderProfile).filter(BidderProfile.user_id == current_user.id).first()
    if not bidder:
        raise RoleMismatchException(expected_role="BIDDER", actual_role=current_user.role)

    submission = db.query(BidSubmission).filter(
        BidSubmission.application_id == application_id,
        BidSubmission.bidder_id == bidder.id
    ).first()
    if not submission:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Application not found or access denied.")

    req = db.query(TenderRequirement).filter(
        TenderRequirement.requirement_id == requirement_id,
        TenderRequirement.tender_id == submission.tender_id
    ).first()
    if not req:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Requirement not found for this tender.")

    # 3. CRYPTOGRAPHIC FINGERPRINTING (SHA-256)
    sha256_hash = hashlib.sha256()
    while chunk := file.file.read(8192):
        sha256_hash.update(chunk)
    file.file.seek(0)
    file_hash = sha256_hash.hexdigest()

    # 4. SECURE PHYSICAL STORAGE
    year = datetime.now(timezone.utc).year
    doc_id = f"DOC-{year}-{uuid.uuid4().hex[:6].upper()}"
    file_ext = os.path.splitext(file.filename)[1]
    stored_file_name = f"{doc_id}{file_ext}"
    file_path = os.path.join(UPLOAD_DIR, stored_file_name)

    with open(file_path, "wb") as buffer:
        shutil.copyfileobj(file.file, buffer)

    # 5. DATABASE REGISTRATION
    new_doc = BidderDocument(
        document_id=doc_id,
        submission_id=submission.id,
        requirement_id=req.id,
        original_file_name=file.filename,
        stored_file_name=stored_file_name,
        storage_path=file_path,
        mime_type=file.content_type,
        file_size_bytes=file_size,
        sha256=file_hash,
        metadata_json=metadata_string,
        processing_status="UPLOADED"
    )
    db.add(new_doc)
    db.flush()
    
    new_doc.display_id = f"DOC-{new_doc.id:04d}"
    db.commit()
    db.refresh(new_doc)

    metadata_dict = json.loads(new_doc.metadata_json) if new_doc.metadata_json else None

    return {
        "id": new_doc.id,  # Database primary key needed by background workers
        "document_id": new_doc.document_id,
        "display_id": new_doc.display_id,
        "requirement_id": req.requirement_id,
        "original_file_name": new_doc.original_file_name,
        "mime_type": new_doc.mime_type,
        "file_size_bytes": new_doc.file_size_bytes,
        "sha256": new_doc.sha256,
        "processing_status": new_doc.processing_status,
        "meta_data": metadata_dict,
        "metadata": metadata_dict,
        "uploaded_at": new_doc.uploaded_at
    }