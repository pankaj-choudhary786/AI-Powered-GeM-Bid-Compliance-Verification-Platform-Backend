# app/integrations/pan_income_tax.py
from sqlalchemy.orm import Session
from app.db.models import MockGovernmentRegistry

def verify_pan(db: Session, pan_number: str) -> dict:
    """
    Adapter for the Income Tax PAN API. 
    Currently routes to the API Setu MockGovernmentRegistry for testing.
    """
    # Simulate API call to the government database
    record = db.query(MockGovernmentRegistry).filter(MockGovernmentRegistry.pan == pan_number).first()
    
    if record:
        return {
            "valid": True,
            "pan": record.pan,
            "status": record.pan_status or "ACTIVE",
            "name": record.entity_name
        }
    
    return {
        "valid": False,
        "pan": pan_number,
        "status": "NOT_FOUND",
        "name": None
    }