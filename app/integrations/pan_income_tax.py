# app/integrations/pan_income_tax.py
import json
import logging
from sqlalchemy.orm import Session
from app.core.config import settings

logger = logging.getLogger(__name__)

def verify_pan(db: Session, pan_number: str) -> dict:
    """
    Adapter for Income Tax PAN verification.
    Reads ground-truth data directly from mock PAN registry JSON.
    """
    if not pan_number:
        return {"valid": False, "status": "MISSING", "error": "No PAN provided"}

    clean_pan = str(pan_number).strip().upper()

    if settings.USE_MOCK_DATA:
        file_path = settings.get_mock_file("pan_schema.json")
        try:
            if file_path.exists():
                with open(file_path, "r", encoding="utf-8") as f:
                    pan_registry = json.load(f)
                    
                record = pan_registry.get(clean_pan)
                if record:
                    return {
                        "valid": True,
                        "pan": record.get("pan_number", clean_pan),
                        "status": record.get("status", "ACTIVE"),
                        "name": record.get("full_name"),
                        "category": record.get("category"),
                        "data": record
                    }
        except Exception as e:
            logger.error(f"Error reading PAN mock JSON at {file_path}: {e}")

        return {
            "valid": False,
            "pan": clean_pan,
            "status": "NOT_FOUND",
            "name": None,
            "error": "PAN not registered in Government Registry"
        }
    else:
        raise NotImplementedError("Live Income Tax API credentials not configured.")