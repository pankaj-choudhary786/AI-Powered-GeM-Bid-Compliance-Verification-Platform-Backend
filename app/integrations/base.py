# app/integrations/base.py
import os
import json
import uuid
from datetime import datetime, timezone

RAW_SOURCES_DIR = "data/raw_sources"
os.makedirs(RAW_SOURCES_DIR, exist_ok=True)

def persist_raw_source_payload(source_name: str, identifier: str, raw_payload: dict) -> str:
    """Saves raw external response to disk for legal audit trails."""
    timestamp = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S")
    unique_id = uuid.uuid4().hex[:6].upper()
    filename = f"{source_name}_{identifier}_{timestamp}_{unique_id}.json"
    file_path = os.path.join(RAW_SOURCES_DIR, filename)

    with open(file_path, "w", encoding="utf-8") as f:
        json.dump(raw_payload, f, indent=2)

    return file_path