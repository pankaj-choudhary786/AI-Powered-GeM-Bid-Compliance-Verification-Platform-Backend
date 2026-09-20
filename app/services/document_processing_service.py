# app/services/document_processing_service.py
import uuid
import json
from sqlalchemy.orm import Session
from app.db.models import BidderDocument, ExtractedField
from app.ai.preprocessing import preprocess_document
from app.ai.ocr import extract_text_with_boxes
from app.ai.field_extractor import extract_key_fields

def process_and_extract_document(db: Session, document_id):
    # 1. Fetch document record (handles both int ID and string document_id)
    if isinstance(document_id, int) or (isinstance(document_id, str) and document_id.isdigit()):
        doc_record = db.query(BidderDocument).filter(BidderDocument.id == int(document_id)).first()
    else:
        doc_record = db.query(BidderDocument).filter(BidderDocument.document_id == str(document_id)).first()

    if not doc_record:
        print(f"[-] Document with identifier '{document_id}' not found in database.")
        return None
        
    print(f"\n=======================================================")
    print(f"[AI PIPELINE STARTED] Document: {doc_record.original_file_name} ({doc_record.document_id})")
    print(f"=======================================================")

    # 2. OpenCV Preprocessing (Deskew, Denoise, Binarize)
    print(" -> [Step 1/3] OpenCV Image Enhancement...")
    processed_image_paths = preprocess_document(doc_record.storage_path, doc_record.document_id)
    print(f"    [+] Saved enhanced image(s): {processed_image_paths}")

    total_extracted_fields = []

    # 3. PaddleOCR & Field Extraction
    for idx, img_path in enumerate(processed_image_paths):
        page_num = idx + 1
        print(f" -> [Step 2/3] Running PaddleOCR on page {page_num}...")
        ocr_blocks = extract_text_with_boxes(img_path)
        print(f"    [+] PaddleOCR detected {len(ocr_blocks)} text block(s).")

        print(f" -> [Step 3/3] Extracting key compliance fields via Regex...")
        extracted_entities = extract_key_fields(ocr_blocks, page_num)
        print(f"    [+] Extracted: {[e['field_key'] + ': ' + e['normalized_value'] for e in extracted_entities]}")

        # 4. Save to Database
        for entity in extracted_entities:
            field_record = ExtractedField(
                extracted_field_id=f"EXT-{uuid.uuid4().hex[:8].upper()}",
                document_id=doc_record.id,
                field_key=entity["field_key"],
                field_label=entity["field_label"],
                raw_value=entity["raw_value"],
                normalized_value=entity["normalized_value"],
                confidence=entity["confidence"],
                page_number=entity["page_number"],
                bounding_box=json.dumps(entity["bounding_box"])
            )
            db.add(field_record)
            total_extracted_fields.append(field_record)

    # Update document status
    doc_record.processing_status = "EXTRACTED"
    doc_record.enhanced_storage_path = processed_image_paths[0] if processed_image_paths else None

    db.commit()
    print(f"[AI PIPELINE COMPLETED] Successfully stored {len(total_extracted_fields)} field(s) in database.\n")
    return total_extracted_fields