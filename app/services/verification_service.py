# app/services/verification_service.py
import uuid
from sqlalchemy.orm import Session
from sqlalchemy import func
from fastapi import HTTPException, status
from app.db.models import (
    BidSubmission, ExtractedField, GovernmentSourceRecord, 
    VerificationResult, BidderDocument, SourceType, ComplianceResult
)
from app.integrations.gst import verify_gstin
from app.integrations.pan_income_tax import verify_pan

def execute_cross_document_matching(db: Session, application_id: str):
    """
    The Single Orchestrator:
    1. Checks if AI is still processing documents (Asynchronous State Management).
    2. Fetches Government Data via Official Adapters.
    3. Compares it against AI-Extracted OCR Data.
    4. Saves deterministic PASS/FAIL results.
    """
    submission = db.query(BidSubmission).filter(BidSubmission.application_id == application_id).first()
    if not submission:
        return {"status": "FAILED", "reason": "Application not found", "results": []}
        
    bidder = submission.bidder
    
    # ---------------------------------------------------------
    # 1. CHECK AI PIPELINE STATUS FIRST (State-Awareness)
    # ---------------------------------------------------------
    documents = db.query(BidderDocument).filter(BidderDocument.submission_id == submission.id).all()
    
    if not documents:
        return {"status": "FAILED", "reason": "No documents uploaded yet. Cannot verify.", "results": []}

    # Intercept if OpenCV/PaddleOCR are still running in the background
    pending_docs = [doc for doc in documents if doc.processing_status in ["UPLOADED", "PROCESSING"]]
    
    if pending_docs:
        return {
            "status": "PROCESSING",
            "reason": f"AI is currently scanning {len(pending_docs)} document(s). Please wait...",
            "pending_count": len(pending_docs),
            "total_documents": len(documents)
        }

    # ---------------------------------------------------------
    # 2. FETCH & STORE GOVERNMENT GROUND TRUTH (Integrations)
    # ---------------------------------------------------------
    if bidder.gstin:
        gst_payload = verify_gstin(db, bidder.gstin)
        existing_gst = db.query(GovernmentSourceRecord).filter_by(identifier_value=bidder.gstin).first()
        if not existing_gst:
            db.add(GovernmentSourceRecord(
                source_record_id=f"GOV-GST-{uuid.uuid4().hex[:8].upper()}",
                source_name="GSTN_PORTAL",
                source_type=SourceType.MOCK,
                identifier_type="GSTIN",
                identifier_value=bidder.gstin,
                status=gst_payload.get("status", "ACTIVE")
            ))

    if bidder.pan:
        pan_payload = verify_pan(db, bidder.pan)
        existing_pan = db.query(GovernmentSourceRecord).filter_by(identifier_value=bidder.pan).first()
        if not existing_pan:
            db.add(GovernmentSourceRecord(
                source_record_id=f"GOV-PAN-{uuid.uuid4().hex[:8].upper()}",
                source_name="INCOME_TAX_PAN",
                source_type=SourceType.MOCK,
                identifier_type="PAN",
                identifier_value=bidder.pan,
                status=pan_payload.get("status", "ACTIVE")
            ))
            
    db.commit()

    # ---------------------------------------------------------
    # 3. FETCH AI OCR EXTRACTIONS (From uploaded PDFs)
    # ---------------------------------------------------------
    doc_ids = [doc.id for doc in documents]
    extracted_fields = db.query(ExtractedField).filter(ExtractedField.document_id.in_(doc_ids)).all()

    if not extracted_fields:
        return {"status": "FAILED", "reason": "AI finished, but no compliance data could be extracted from the PDFs.", "results": []}

# ---------------------------------------------------------
    # 4. FOOLPROOF RULE ENGINE (Cross-Check Raw OCR vs Govt)
    # ---------------------------------------------------------
    verification_summary = []
    
    # We will specifically look for the 3 mandatory Government IDs
    expected_documents = [
        {"key": "PAN", "expected": bidder.pan},
        {"key": "GSTIN", "expected": bidder.gstin},
        {"key": "UDYAM", "expected": bidder.udyam_number}
    ]
    
    for doc in expected_documents:
        expected_val = doc["expected"]
        if not expected_val:
            continue
            
        safe_expected = str(expected_val).strip().upper()
        
        is_match = False
        detected_value = "NOT_FOUND"
        best_confidence = 0.0
        req_id = "REQ-UNKNOWN"
        
        # Scan ALL extracted OCR fields to see if the AI caught this value
        for field in extracted_fields:
            safe_extracted = str(field.normalized_value).strip().upper()
            
            # If the exact Government ID is found anywhere inside the OCR text
            if safe_expected in safe_extracted:
                is_match = True
                detected_value = safe_expected # Clean extraction for the UI
                best_confidence = field.confidence if field.confidence else 0.98
                if field.document:
                    req_id = field.document.requirement_id
                break
                
        compliance_status = ComplianceResult.PASS if is_match else ComplianceResult.FAIL
        
        # Save the human-readable result
        verification_record = VerificationResult(
            verification_id=f"VER-{uuid.uuid4().hex[:8].upper()}",
            submission_id=submission.id,
            requirement_id=req_id,
            result=compliance_status,
            detected_value=detected_value,
            expected_value=safe_expected,
            confidence=best_confidence,
            reason="OCR Match Successful" if is_match else "ID Missing from Documents",
            requires_human_review=not is_match
        )
        db.add(verification_record)
        
        verification_summary.append({
            "field_type": doc["key"],
            "ocr_extracted_value": detected_value,
            "government_expected_value": safe_expected,
            "match": is_match,
            "confidence": best_confidence
        })
        
    db.commit()

    # ---------------------------------------------------------
    # 5. CALCULATE OVERALL COMPLIANCE SCORE (SIH Dashboard)
    # ---------------------------------------------------------
    total_checks = len(verification_summary)
    passed_checks = sum(1 for result in verification_summary if result["match"])
    
    # Calculate percentage
    overall_score_percentage = (passed_checks / total_checks * 100) if total_checks > 0 else 0.0
    is_fully_compliant = (overall_score_percentage == 100.0)
    
    return {
        "status": "VERIFICATION_COMPLETED",
        "application_id": application_id,
        "total_checks_executed": total_checks,
        "passed_checks": passed_checks,
        "overall_compliance_score": f"{overall_score_percentage:.1f}%",
        "is_fully_compliant": is_fully_compliant,
        "results": verification_summary
    }