# app/integrations/gst.py
import json
from sqlalchemy.orm import Session
from app.core.config import settings
from app.db.models import MockGovernmentRegistry
from app.integrations.base import persist_raw_source_payload

def verify_gstin(db: Session, gstin: str) -> dict:
    if not gstin:
        return {"matched": False, "status": "MISSING", "error": "No GSTIN provided"}

    if settings.USE_MOCK_DATA:
        record = db.query(MockGovernmentRegistry).filter(MockGovernmentRegistry.gstin == gstin).first()
        if not record or not record.raw_gst_payload:
            raw_payload = {"valid": False, "error": "GSTIN not found in registry"}
            file_path = persist_raw_source_payload("GSTN", gstin, raw_payload)
            return {
                "matched": False,
                "status": "NOT_FOUND",
                "raw_payload_path": file_path,
                "data": raw_payload
            }

        raw_payload = json.loads(record.raw_gst_payload)
        file_path = persist_raw_source_payload("GSTN", gstin, raw_payload)

        return {
            "matched": True,
            "status": record.gst_status,
            "legal_name": raw_payload.get("lgnm"),
            "trade_name": raw_payload.get("tradeNam"),
            "taxpayer_type": raw_payload.get("dty"),
            "raw_payload_path": file_path,
            "data": raw_payload
        }
    else:
        # Placeholder for live HTTPX call when live credentials are provided
        raise NotImplementedError("Live GST API keys not configured.")