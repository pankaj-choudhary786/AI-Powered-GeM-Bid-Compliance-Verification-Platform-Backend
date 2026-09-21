# app/integrations/gst.py
import json
import logging
from sqlalchemy.orm import Session
from app.core.config import settings

logger = logging.getLogger(__name__)

def verify_gstin(db: Session, gstin: str) -> dict:
    """
    Adapter for GST Network (GSTN) verification.
    Reads ground-truth data directly from mock GSTN registry JSON.
    """
    if not gstin:
        return {"matched": False, "status": "MISSING", "error": "No GSTIN provided"}

    clean_gstin = str(gstin).strip().upper()

    if settings.USE_MOCK_DATA:
        file_path = settings.get_mock_file("gstn_schema.json")
        try:
            if file_path.exists():
                with open(file_path, "r", encoding="utf-8") as f:
                    gst_registry = json.load(f)
                    
                record = gst_registry.get(clean_gstin)
                if record:
                    return {
                        "matched": True,
                        "gstin": record.get("gstin", clean_gstin),
                        "status": record.get("sts", "Active").upper(),
                        "legal_name": record.get("lgnm"),
                        "trade_name": record.get("tradeNam"),
                        "taxpayer_type": record.get("dty"),
                        "data": record
                    }
        except Exception as e:
            logger.error(f"Error reading GSTN mock JSON at {file_path}: {e}")

        return {
            "matched": False,
            "gstin": clean_gstin,
            "status": "NOT_FOUND",
            "error": "GSTIN not found in Government GSTN Registry"
        }
    else:
        raise NotImplementedError("Live GST API keys not configured.")