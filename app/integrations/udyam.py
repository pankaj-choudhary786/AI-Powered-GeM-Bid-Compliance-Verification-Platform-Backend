# app/integrations/udyam.py
import json
import logging
from sqlalchemy.orm import Session
from app.core.config import settings

logger = logging.getLogger(__name__)

def verify_udyam(db: Session, udyam_number: str) -> dict:
    """
    Adapter for Ministry of MSME Udyam verification.
    Reads ground-truth data directly from mock Udyam registry JSON.
    """
    if not udyam_number:
        return {"matched": False, "status": "MISSING", "error": "No Udyam number provided"}

    clean_udyam = str(udyam_number).strip().upper()

    if settings.USE_MOCK_DATA:
        file_path = settings.get_mock_file("udyam_schema.json")
        try:
            if file_path.exists():
                with open(file_path, "r", encoding="utf-8") as f:
                    udyam_registry = json.load(f)
                    
                record = udyam_registry.get(clean_udyam)
                if record:
                    return {
                        "matched": True,
                        "udyam_number": record.get("udyamRegistrationNumber", clean_udyam),
                        "status": "ACTIVE",
                        "enterprise_name": record.get("enterpriseName"),
                        "enterprise_type": record.get("enterpriseType"),
                        "major_activity": record.get("majorActivity"),
                        "data": record
                    }
        except Exception as e:
            logger.error(f"Error reading Udyam mock JSON at {file_path}: {e}")

        return {
            "matched": False,
            "udyam_number": clean_udyam,
            "status": "NOT_FOUND",
            "error": "Udyam registration not found in MSME Registry"
        }
    else:
        raise NotImplementedError("Live MSME Udyam API not configured.")