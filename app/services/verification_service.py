# app/services/verification_service.py
import uuid
from sqlalchemy.orm import Session
from fastapi import HTTPException, status
from app.db.models import (
    BidSubmission, ExtractedField, GovernmentSourceRecord, 
    VerificationResult, BidderDocument, SourceType, ComplianceResult
)
from app.integrations.gst import verify_gstin
from app.integrations.pan_income_tax import verify_pan
from app.integrations.udyam import verify_udyam

def execute_cross_document_matching(db: Session, application_id: str):
    """
    True AI Pipeline Orchestrator:
    1. Checks if AI background processing is complete.
    2. Fetches whatever data the AI OCR extracted from the PDFs.
    3. Pings the Government JSON Mock DBs using the AI-extracted IDs.
    4. Computes compliance scores, risk levels, and UI Evidence Graph.
    """
    submission = db.query(BidSubmission).filter(BidSubmission.application_id == application_id).first()
    if not submission:
        return {"status": "FAILED", "reason": "Application not found", "results": []}
        
    # ---------------------------------------------------------
    # 1. ASYNCHRONOUS STATE CHECK
    # ---------------------------------------------------------
    documents = db.query(BidderDocument).filter(BidderDocument.submission_id == submission.id).all()
    
    if not documents:
        return {"status": "FAILED", "reason": "No documents uploaded yet. Cannot verify.", "results": []}

    pending_docs = [doc for doc in documents if doc.processing_status in ["UPLOADED", "PROCESSING"]]
    if pending_docs:
        return {
            "status": "PROCESSING",
            "reason": f"AI is currently scanning {len(pending_docs)} document(s). Please wait...",
            "pending_count": len(pending_docs),
            "total_documents": len(documents)
        }

    # ---------------------------------------------------------
    # 2. FETCH AI OCR EXTRACTIONS FROM UPLOADED PDFs
    # ---------------------------------------------------------
    doc_ids = [doc.id for doc in documents]
    extracted_fields = db.query(ExtractedField).filter(ExtractedField.document_id.in_(doc_ids)).all()

    if not extracted_fields:
        return {"status": "FAILED", "reason": "AI finished, but no data extracted from PDFs.", "results": []}

    # ---------------------------------------------------------
    # 3. DIRECTLY VERIFY AI EXTRACTIONS AGAINST MOCK GOVT DB
    # ---------------------------------------------------------
    # We are checking for the 3 core tender requirements
    expected_doc_types = ["PAN", "GSTIN", "UDYAM"]
    verification_summary = []

    for doc_type in expected_doc_types:
        # STEP A: What did the AI find in the PDF for this document type?
        extracted_value = "NOT_FOUND"
        best_confidence = 0.0
        req_id = "REQ-UNKNOWN"

        for field in extracted_fields:
            safe_field_key = str(field.field_key or "").strip().upper()
            if doc_type in safe_field_key:
                extracted_value = str(field.normalized_value or "").strip().upper()
                best_confidence = float(field.confidence) if field.confidence else 0.98
                if field.document and hasattr(field.document, "requirement_id") and field.document.requirement_id:
                    req_id = field.document.requirement_id
                break

        # STEP B: Ask the Government Database if the AI's extracted ID is real
        gov_expected_val = "NOT_FOUND_IN_GOVT_DB"
        is_match = False
        gov_status = "NOT_FOUND"

        if extracted_value != "NOT_FOUND":
            if doc_type == "PAN":
                res = verify_pan(db, extracted_value)
                if res.get("valid"):
                    gov_expected_val = res.get("pan", extracted_value)
                    is_match = True
                    gov_status = res.get("status", "ACTIVE")
            
            elif doc_type == "GSTIN":
                res = verify_gstin(db, extracted_value)
                if res.get("matched"):
                    gov_expected_val = res.get("gstin", extracted_value)
                    is_match = True
                    gov_status = res.get("status", "ACTIVE")
                    
            elif doc_type == "UDYAM":
                res = verify_udyam(db, extracted_value)
                if res.get("matched"):
                    gov_expected_val = res.get("udyam_number", extracted_value)
                    is_match = True
                    gov_status = res.get("status", "ACTIVE")

            # Store the API trace in the database
            if not db.query(GovernmentSourceRecord).filter_by(identifier_value=extracted_value).first():
                db.add(GovernmentSourceRecord(
                    source_record_id=f"GOV-{doc_type}-{uuid.uuid4().hex[:8].upper()}",
                    submission_id=submission.id,  # <--- FIX: This is the missing constraint
                    source_name=f"{doc_type}_REGISTRY",
                    source_type=SourceType.MOCK,
                    identifier_type=doc_type,
                    identifier_value=extracted_value,
                    status=gov_status
                ))

        compliance_status = ComplianceResult.PASS if is_match else ComplianceResult.FAIL

        # Persist verification result
        verification_record = VerificationResult(
            verification_id=f"VER-{uuid.uuid4().hex[:8].upper()}",
            submission_id=submission.id,
            requirement_id=req_id,
            result=compliance_status,
            detected_value=extracted_value,
            expected_value=gov_expected_val,
            confidence=best_confidence,
            reason="Verified directly in Govt Database" if is_match else "Extracted ID not found in Govt Database",
            requires_human_review=not is_match
        )
        db.add(verification_record)

        verification_summary.append({
            "field_type": doc_type,
            "ocr_extracted_value": extracted_value,
            "government_expected_value": gov_expected_val,
            "match": is_match,
            "confidence": round(best_confidence, 3)
        })

    db.commit()

    # ---------------------------------------------------------
    # 4. CALCULATE AGGREGATED SCORE & RISK LEVEL
    # ---------------------------------------------------------
    total_checks = len(verification_summary)
    passed_checks = sum(1 for result in verification_summary if result["match"])
    overall_score_percentage = (passed_checks / total_checks * 100) if total_checks > 0 else 0.0
    is_fully_compliant = (overall_score_percentage == 100.0)

    if overall_score_percentage == 100.0:
        risk_level = "LOW_RISK"
    elif overall_score_percentage >= 70.0:
        risk_level = "MEDIUM_RISK"
    else:
        risk_level = "HIGH_RISK"

    # ---------------------------------------------------------
    # 5. GENERATE EVIDENCE GRAPH (React Flow / D3)
    # ---------------------------------------------------------
    nodes = []
    edges = []
    root_id = f"node-app-{application_id}"
    nodes.append({
        "id": root_id,
        "type": "application",
        "data": {"label": f"Bid Application: {application_id}"},
        "position": {"x": 300, "y": 20}
    })

    for idx, item in enumerate(verification_summary):
        f_type = item["field_type"]
        matched = item["match"]
        x_pos = 100 + (idx * 260)

        ocr_id = f"node-ocr-{f_type.lower()}"
        nodes.append({
            "id": ocr_id,
            "type": "ocr_extraction",
            "data": {"label": f"OCR Extracted ({f_type}):\n{item['ocr_extracted_value']}", "confidence": item["confidence"]},
            "position": {"x": x_pos, "y": 140}
        })
        edges.append({"id": f"edge-app-{ocr_id}", "source": root_id, "target": ocr_id})

        gov_id = f"node-gov-{f_type.lower()}"
        nodes.append({
            "id": gov_id,
            "type": "government_record",
            "data": {"label": f"Govt JSON Record:\n{item['government_expected_value']}"},
            "position": {"x": x_pos, "y": 260}
        })

        rule_id = f"node-rule-{f_type.lower()}"
        nodes.append({
            "id": rule_id,
            "type": "compliance_verdict",
            "data": {
                "label": f"{f_type} Verification: {'PASS' if matched else 'FAIL'}",
                "status": "PASS" if matched else "FAIL",
                "color": "#10B981" if matched else "#EF4444"
            },
            "position": {"x": x_pos, "y": 380}
        })
        edges.append({"id": f"edge-{ocr_id}-{rule_id}", "source": ocr_id, "target": rule_id})
        edges.append({"id": f"edge-{gov_id}-{rule_id}", "source": gov_id, "target": rule_id})

    evidence_graph = {"nodes": nodes, "edges": edges}

    return {
        "status": "VERIFICATION_COMPLETED",
        "application_id": application_id,
        "total_checks_executed": total_checks,
        "passed_checks": passed_checks,
        "overall_compliance_score": f"{overall_score_percentage:.1f}%",
        "risk_level": risk_level,
        "is_fully_compliant": is_fully_compliant,
        "results": verification_summary,
        "evidence_graph": evidence_graph
    }