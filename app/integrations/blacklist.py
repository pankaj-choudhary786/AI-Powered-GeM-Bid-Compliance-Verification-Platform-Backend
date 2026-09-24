# app/integrations/blacklist.py
import json
from typing import Dict, Any
from app.core.config import settings

def check_debarment(pan: str = None, company_name: str = None) -> Dict[str, Any]:
    """
    Checks if a given PAN or Company Name is on the GeM/CPPP Debarment list.
    """
    if settings.USE_MOCK_DATA:
        # 🚨 THE FIX: Uses your config to find the exact path to government_verification/
        file_path = settings.get_mock_file("blacklist_schema.json")
        
        if not file_path.exists():
            # If the file is missing or named wrong, it will now yell in the console
            print(f"\n[!] CRITICAL ERROR: Blacklist file NOT FOUND at {file_path}")
            return {"is_blacklisted": False, "reason": "Registry not found"}
            
        try:
            with open(file_path, "r", encoding="utf-8") as f:
                data = json.load(f)
                
            for entity in data.get("debarred_entities", []):
                # Safe string comparison to prevent type errors
                if pan and str(entity.get("pan")).upper() == str(pan).upper():
                    return {"is_blacklisted": True, "reason": entity.get("reason")}
                
                if company_name and str(entity.get("company_name")).upper() == str(company_name).upper():
                    return {"is_blacklisted": True, "reason": entity.get("reason")}
                    
        except Exception as e:
            print(f"[!] Error reading blacklist JSON: {e}")
            
    return {"is_blacklisted": False, "reason": None}