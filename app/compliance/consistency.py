# app/compliance/consistency.py
import difflib
from typing import Dict, Any

def check_name_consistency(name1: str, name2: str) -> Dict[str, Any]:
    """
    Innovation 2: Cross-Document Intelligence.
    Compares names across different government registries to detect identity spoofing.
    """
    if not name1 or not name2:
        return {"match": False, "score": 0.0, "status": "MISSING_DATA"}

    # Normalize strings: uppercase and strip common corporate suffixes
    def normalize(text: str) -> str:
        text = str(text).upper().strip()
        for word in [" PVT", " LTD", " LLP", " PRIVATE", " LIMITED"]:
            text = text.replace(word, "")
        return text.strip()

    norm1 = normalize(name1)
    norm2 = normalize(name2)
    
    # Calculate similarity ratio (0.0 to 1.0)
    similarity = difflib.SequenceMatcher(None, norm1, norm2).ratio()
    
    # Threshold for accepting as the same entity (e.g., 85% match)
    is_match = similarity >= 0.85
    
    return {
        "match": is_match,
        "score": round(similarity * 100, 2),
        "status": "PASS" if is_match else "NEEDS_REVIEW"
    }