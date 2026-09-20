# app/services/government_verification_service.py
import uuid
import json
from datetime import datetime, timezone
from sqlalchemy.orm import Session
from fastapi import HTTPException, status
from app.db.models import BidSubmission, GovernmentSourceRecord, SourceType
from app.integrations.gst import verify_gstin
from app.integrations.pan import verify_pan

def run_government_verification(db: Session, application_id: str) -> dict:
    submission = db.query(BidSubmission).filter(BidSubmission.application_id == application_id).first()
    if not submission:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Application not found")

    bidder = submission.bidder
    year = datetime.now(timezone.utc).year
    results = []

    # 1. Run GST Verification
    if bidder.gstin:
        gst_result = verify_gstin(db, bidder.gstin)
        source_rec_gst = GovernmentSourceRecord(
            source_record_id=f"GOV-{year}-{uuid.uuid4().hex[:6].upper()}",
            submission_id=submission.id,
            source_name="GSTN_PORTAL",
            source_type=SourceType.MOCK,
            identifier_type="GSTIN",
            identifier_value=bidder.gstin,
            status=gst_result.get("status", "UNKNOWN"),
            matched=gst_result.get("matched", False),
            response_data_json=json.dumps(gst_result.get("data", {})),
            raw_payload_path=gst_result.get("raw_payload_path")
        )
        db.add(source_rec_gst)
        results.append({"source": "GSTN", "result": gst_result})

    # 2. Run PAN Verification
    if bidder.pan:
        pan_result = verify_pan(db, bidder.pan)
        source_rec_pan = GovernmentSourceRecord(
            source_record_id=f"GOV-{year}-{uuid.uuid4().hex[:6].upper()}",
            submission_id=submission.id,
            source_name="INCOME_TAX_PAN",
            source_type=SourceType.MOCK,
            identifier_type="PAN",
            identifier_value=bidder.pan,
            status=pan_result.get("status", "UNKNOWN"),
            matched=pan_result.get("matched", False),
            response_data_json=json.dumps(pan_result.get("data", {})),
            raw_payload_path=pan_result.get("raw_payload_path")
        )
        db.add(source_rec_pan)
        results.append({"source": "PAN", "result": pan_result})

    db.commit()

    return {
        "application_id": application_id,
        "checks_executed": len(results),
        "results": results
    }