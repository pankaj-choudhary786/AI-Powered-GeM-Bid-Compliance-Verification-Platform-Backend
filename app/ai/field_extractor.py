# app/ai/field_extractor.py
import re

# Comprehensive Indian Government Regex Patterns
PATTERNS = {
    "PAN": r"[A-Z]{5}[0-9]{4}[A-Z]{1}",
    "GSTIN": r"[0-9]{2}[A-Z]{5}[0-9]{4}[A-Z]{1}[1-9A-Z]{1}Z[0-9A-Z]{1}",
    "UDYAM": r"UDYAM-[A-Z]{2}-[0-9]{2}-[0-9]{7}",
    "CIN": r"[L|U]{1}[0-9]{5}[A-Z]{2}[0-9]{4}[A-Z]{3}[0-9]{6}", # MCA21 Format
    "DIPP": r"DIPP[0-9]{5,6}", # Startup India Format
    "TURNOVER_CR": r"(?:Turnover|Revenue).*?(?:Rs\.?|INR|₹)?\s*([0-9]+(?:\.[0-9]+)?)\s*(?:Cr|Crore)"
}

def extract_key_fields(ocr_data: list[dict], page_num: int) -> list[dict]:
    found_fields = []
    
    for block in ocr_data:
        text = block["text"]
        for field_key, pattern in PATTERNS.items():
            match = re.search(pattern, text, re.IGNORECASE)
            if match:
                value = match.group(1) if field_key == "TURNOVER_CR" else match.group(0)
                found_fields.append({
                    "field_key": field_key,
                    "field_label": f"Extracted {field_key}",
                    "raw_value": text,
                    "normalized_value": value.upper(),
                    "confidence": block["confidence"],
                    "page_number": page_num,
                    "bounding_box": block["bounding_box"]
                })
                
    return found_fields