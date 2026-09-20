# app/integrations/pan.py
import json
from sqlalchemy.orm import Session
from app.core.config import settings
from app.db.models import MockGovernmentRegistry
from app.integrations.base import persist_raw_source_payload

def verify_pan(db: Session, pan: str) -> dict:
    if not pan:
        return {"matched": False, "status": "MISSING", "error": "No PAN provided"}

    if settings.USE_MOCK_DATA:
        record = db.query(MockGovernmentRegistry).filter(MockGovernmentRegistry.pan == pan).first()
        
        if not record or not record.raw_pan_payload:
            raw_payload = {"valid": False, "error": "PAN not found in registry"}
            file_path = persist_raw_source_payload("PAN", pan, raw_payload)
            return {
                "matched": False,
                "status": "NOT_FOUND",
                "raw_payload_path": file_path,
                "data": raw_payload,
                "metadata": {}
            }

        raw_payload = json.loads(record.raw_pan_payload)
        file_path = persist_raw_source_payload("PAN", pan, raw_payload)

        return {
            "matched": True,
            "status": record.pan_status,
            "legal_name": raw_payload.get("name"),
            "category": raw_payload.get("category"),
            "raw_payload_path": file_path,
            "data": raw_payload,
            "metadata": record.metadata_dict # Added safe metadata retrieval
        }
    else:
        raise NotImplementedError("Live PAN API keys not configured.")