# app/services/verification_service.py
import uuid
import json
from sqlalchemy.orm import Session
from app.db.models import (
    BidSubmission, ExtractedField, GovernmentSourceRecord, 
    VerificationResult, BidderDocument, SourceType, ComplianceResult,
    ScoreRiskAssessment, StandardDocumentType, CrossDocumentFinding
)
from app.integrations.gst import verify_gstin
from app.integrations.pan_income_tax import verify_pan
from app.integrations.udyam import verify_udyam
from app.integrations.blacklist import check_debarment
from app.compliance.consistency import check_name_consistency

def execute_cross_document_matching(db: Session, application_id: str):
    submission = db.query(BidSubmission).filter(BidSubmission.application_id == application_id).first()
    if not submission:
        return {"status": "FAILED", "reason": "Application not found", "results": []}
        
    documents = db.query(BidderDocument).filter(BidderDocument.submission_id == submission.id).all()
    if not documents:
        return {"status": "FAILED", "reason": "No documents uploaded yet.", "results": []}

    pending_docs = [doc for doc in documents if doc.processing_status in ["UPLOADED", "PROCESSING"]]
    if pending_docs:
        return {"status": "PROCESSING", "reason": f"AI is scanning {len(pending_docs)} document(s)...", "pending_count": len(pending_docs)}

    doc_ids = [doc.id for doc in documents]
    extracted_fields = db.query(ExtractedField).filter(ExtractedField.document_id.in_(doc_ids)).all()

    verification_summary = []
    
    pan_entity_name = None
    gst_entity_name = None
    is_blacklisted = False
    debarment_reason = ""

    for req in submission.tender.requirements:
        # 🚨 FIX 2: Safely convert SQLite Enum String to raw string
        doc_enum_raw = req.standard_document_type
        doc_enum_str = doc_enum_raw.value if hasattr(doc_enum_raw, 'value') else str(doc_enum_raw)
        doc_enum_str = doc_enum_str.split('.')[-1]

        if doc_enum_str not in ["PAN_CARD", "GST_CERTIFICATE", "UDYAM_REGISTRATION"]:
            continue

        doc_type_key = "PAN" if doc_enum_str == "PAN_CARD" else "GSTIN" if doc_enum_str == "GST_CERTIFICATE" else "UDYAM"

        extracted_value = "NOT_FOUND"
        best_confidence = 0.0

        for field in extracted_fields:
            if doc_type_key in str(field.field_key or "").strip().upper():
                extracted_value = str(field.normalized_value or "").strip().upper()
                best_confidence = float(field.confidence) if field.confidence else 0.98
                break

        gov_expected_val = "NOT_FOUND_IN_GOVT_DB"
        is_match = False
        gov_status = "NOT_FOUND"

        if extracted_value != "NOT_FOUND":
            if doc_type_key == "PAN":
                debarment = check_debarment(pan=extracted_value)
                if debarment.get("is_blacklisted"):
                    is_blacklisted = True
                    debarment_reason = debarment.get("reason", "")

            # 🚨 FIX 3: Capture the correct dictionary keys from your Integration adapters
            if doc_type_key == "PAN":
                res = verify_pan(db, extracted_value)
                if res.get("valid"):
                    gov_expected_val = res.get("pan", extracted_value)
                    pan_entity_name = res.get("name", "")  # Mapped correctly to pan_income_tax.py
                    is_match = True
                    gov_status = res.get("status", "ACTIVE")
            
            elif doc_type_key == "GSTIN":
                res = verify_gstin(db, extracted_value)
                if res.get("matched"):
                    gov_expected_val = res.get("gstin", extracted_value)
                    gst_entity_name = res.get("legal_name", "") # Mapped correctly to gst.py
                    is_match = True
                    gov_status = res.get("status", "ACTIVE")
                    
            elif doc_type_key == "UDYAM":
                res = verify_udyam(db, extracted_value)
                if res.get("matched"):
                    gov_expected_val = res.get("udyam_number", extracted_value)
                    is_match = True
                    gov_status = res.get("status", "ACTIVE")

            if not db.query(GovernmentSourceRecord).filter_by(identifier_value=extracted_value).first():
                db.add(GovernmentSourceRecord(
                    source_record_id=f"GOV-{doc_type_key}-{uuid.uuid4().hex[:8].upper()}",
                    submission_id=submission.id,
                    source_name=f"{doc_type_key}_REGISTRY",
                    source_type=SourceType.MOCK,
                    identifier_type=doc_type_key,
                    identifier_value=extracted_value,
                    status=gov_status
                ))

        db.add(VerificationResult(
            verification_id=f"VER-{uuid.uuid4().hex[:8].upper()}",
            submission_id=submission.id,
            requirement_id=req.id,
            result=ComplianceResult.PASS if is_match else ComplianceResult.FAIL,
            detected_value=extracted_value,
            expected_value=gov_expected_val,
            confidence=best_confidence,
            reason="Verified directly in Govt Database" if is_match else "Extracted ID not found",
            requires_human_review=not is_match
        ))

        verification_summary.append({
            "field_type": doc_type_key,
            "ocr_extracted_value": extracted_value,
            "government_expected_value": gov_expected_val,
            "match": is_match,
            "confidence": round(best_confidence, 3)
        })

    # Cross-Document Intelligence Check
    if pan_entity_name and gst_entity_name:
        consistency_res = check_name_consistency(pan_entity_name, gst_entity_name)
        if not consistency_res["match"]:
            db.add(CrossDocumentFinding(
                finding_id=f"CDF-{uuid.uuid4().hex[:8].upper()}",
                submission_id=submission.id,
                finding_type="ENTITY_NAME_MISMATCH",
                severity="HIGH",
                status=ComplianceResult.NEEDS_REVIEW,
                compared_data=json.dumps({"pan_name": pan_entity_name, "gst_name": gst_entity_name}),
                reason=f"Identity mismatch between PAN and GSTIN. Similarity: {consistency_res['score']}%",
                confidence=consistency_res['score'] / 100.0
            ))

    total_checks = len(verification_summary)
    passed_checks = sum(1 for result in verification_summary if result["match"])
    overall_score_percentage = (passed_checks / total_checks * 100) if total_checks > 0 else 0.0
    is_fully_compliant = (overall_score_percentage == 100.0) and not is_blacklisted

    if is_blacklisted:
        risk_level = "HIGH_RISK"
        overall_score_percentage = 0.0 
    else:
        risk_level = "LOW_RISK" if overall_score_percentage == 100.0 else "MEDIUM_RISK" if overall_score_percentage >= 70.0 else "HIGH_RISK"

    score_record = db.query(ScoreRiskAssessment).filter(ScoreRiskAssessment.submission_id == submission.id).first()
    if not score_record:
        db.add(ScoreRiskAssessment(
            submission_id=submission.id,
            compliance_score=overall_score_percentage,
            risk_level=risk_level,
            risk_score=100.0 - overall_score_percentage,
            score_breakdown_json=json.dumps({"passed": passed_checks, "total": total_checks}),
            risk_signals_json=json.dumps({"blacklisted": is_blacklisted, "debarment_reason": debarment_reason})
        ))
    else:
        score_record.compliance_score = overall_score_percentage
        score_record.risk_level = risk_level
        score_record.risk_signals_json = json.dumps({"blacklisted": is_blacklisted, "debarment_reason": debarment_reason})
        
    submission.status = "VERIFIED"
    db.commit()

    nodes, edges = [], []
    root_id = f"node-app-{application_id}"
    nodes.append({"id": root_id, "type": "application", "data": {"label": f"Bid Application: {application_id}"}, "position": {"x": 300, "y": 20}})

    for idx, item in enumerate(verification_summary):
        f_type = item["field_type"]
        matched = item["match"]
        x_pos = 100 + (idx * 260)
        ocr_id = f"node-ocr-{f_type.lower()}"
        nodes.append({"id": ocr_id, "type": "ocr_extraction", "data": {"label": f"OCR ({f_type}):\n{item['ocr_extracted_value']}", "confidence": item["confidence"]}, "position": {"x": x_pos, "y": 140}})
        edges.append({"id": f"edge-app-{ocr_id}", "source": root_id, "target": ocr_id})
        gov_id = f"node-gov-{f_type.lower()}"
        nodes.append({"id": gov_id, "type": "government_record", "data": {"label": f"Govt Record:\n{item['government_expected_value']}"}, "position": {"x": x_pos, "y": 260}})
        rule_id = f"node-rule-{f_type.lower()}"
        nodes.append({"id": rule_id, "type": "compliance_verdict", "data": {"label": f"{f_type}: {'PASS' if matched else 'FAIL'}", "status": "PASS" if matched else "FAIL", "color": "#10B981" if matched else "#EF4444"}, "position": {"x": x_pos, "y": 380}})
        edges.append({"id": f"edge-{ocr_id}-{rule_id}", "source": ocr_id, "target": rule_id})
        edges.append({"id": f"edge-{gov_id}-{rule_id}", "source": gov_id, "target": rule_id})

    if is_blacklisted:
        blacklist_id = "node-rule-blacklist"
        nodes.append({"id": blacklist_id, "type": "compliance_verdict", "data": {"label": f"DEBARMENT MATCH\n{debarment_reason}", "status": "FAIL", "color": "#B91C1C"}, "position": {"x": 300, "y": -100}})
        edges.append({"id": f"edge-app-{blacklist_id}", "source": root_id, "target": blacklist_id})

    return {
        "status": "VERIFICATION_COMPLETED",
        "application_id": application_id,
        "is_fully_compliant": is_fully_compliant,
        "overall_compliance_score": f"{overall_score_percentage:.1f}%",
        "risk_level": risk_level,
        "results": verification_summary,
        "evidence_graph": {"nodes": nodes, "edges": edges}
    }