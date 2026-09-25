# app/services/verification_service.py
import uuid
import json
from sqlalchemy.orm import Session
from app.db.models import (
    BidSubmission, ExtractedField, GovernmentSourceRecord,
    VerificationResult, BidderDocument, SourceType, ComplianceResult,
    ScoreRiskAssessment, CrossDocumentFinding, AIRecommendation
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
        return {"status": "PROCESSING", "reason": f"AI is scanning {len(pending_docs)} document(s)..."}

    doc_ids = [doc.id for doc in documents]
    extracted_fields = db.query(ExtractedField).filter(ExtractedField.document_id.in_(doc_ids)).all()

    verification_summary = []
    
    pan_entity_name = None
    gst_entity_name = None
    udyam_entity_name = None
    is_blacklisted = False
    debarment_reason = ""

    for req in submission.tender.requirements:
        doc_enum_raw = req.standard_document_type
        doc_enum_str = doc_enum_raw.value if hasattr(doc_enum_raw, 'value') else str(doc_enum_raw)
        doc_enum_str = doc_enum_str.split('.')[-1]

        name_upper = str(req.requirement_name or "").upper()
        if "PAN" in doc_enum_str or "PAN" in name_upper:
            doc_type_key = "PAN"
        elif "GST" in doc_enum_str or "GST" in name_upper:
            doc_type_key = "GSTIN"
        elif "UDYAM" in doc_enum_str or "MSME" in doc_enum_str or "UDYAM" in name_upper or "MSME" in name_upper:
            doc_type_key = "UDYAM"
        else:
            continue

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
                    debarment_reason = debarment.get("reason", "Statutory debarment detected")

            if doc_type_key == "PAN":
                res = verify_pan(db, extracted_value)
                if res.get("valid"):
                    gov_expected_val = res.get("pan", extracted_value)
                    pan_entity_name = res.get("name") or res.get("full_name") or ""
                    is_match = True
                    gov_status = res.get("status", "ACTIVE")
            
            elif doc_type_key == "GSTIN":
                res = verify_gstin(db, extracted_value)
                if res.get("matched"):
                    gov_expected_val = res.get("gstin", extracted_value)
                    gst_entity_name = res.get("legal_name") or res.get("trade_name") or ""
                    is_match = True
                    gov_status = res.get("status", "ACTIVE")
                    
            elif doc_type_key == "UDYAM":
                res = verify_udyam(db, extracted_value)
                if res.get("matched"):
                    gov_expected_val = res.get("udyam_number", extracted_value)
                    udyam_entity_name = res.get("enterprise_name", "")
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
                    status=gov_status,
                    matched=is_match
                ))

        db.add(VerificationResult(
            verification_id=f"VER-{uuid.uuid4().hex[:8].upper()}",
            submission_id=submission.id,
            requirement_id=req.id,
            result=ComplianceResult.PASS if is_match else ComplianceResult.FAIL,
            detected_value=extracted_value,
            expected_value=gov_expected_val,
            confidence=best_confidence,
            reason="Verified directly in Govt Database" if is_match else "Extracted ID not found in Govt Database",
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
    identity_spoofed = False
    mismatch_reasons = []

    if pan_entity_name and gst_entity_name:
        res_pan_gst = check_name_consistency(pan_entity_name, gst_entity_name)
        if not res_pan_gst["match"]:
            identity_spoofed = True
            mismatch_reasons.append(f"PAN ('{pan_entity_name}') != GSTIN ('{gst_entity_name}')")

    if pan_entity_name and udyam_entity_name:
        res_pan_udyam = check_name_consistency(pan_entity_name, udyam_entity_name)
        if not res_pan_udyam["match"]:
            identity_spoofed = True
            mismatch_reasons.append(f"PAN ('{pan_entity_name}') != UDYAM ('{udyam_entity_name}')")

    if gst_entity_name and udyam_entity_name:
        res_gst_udyam = check_name_consistency(gst_entity_name, udyam_entity_name)
        if not res_gst_udyam["match"]:
            identity_spoofed = True
            mismatch_reasons.append(f"GSTIN ('{gst_entity_name}') != UDYAM ('{udyam_entity_name}')")

    if identity_spoofed:
        full_reason = " | ".join(mismatch_reasons)
        db.add(CrossDocumentFinding(
            finding_id=f"CDF-{uuid.uuid4().hex[:8].upper()}",
            submission_id=submission.id,
            finding_type="ENTITY_NAME_MISMATCH",
            severity="HIGH",
            status=ComplianceResult.NEEDS_REVIEW,
            compared_data=json.dumps({
                "pan_name": pan_entity_name,
                "gst_name": gst_entity_name,
                "udyam_name": udyam_entity_name
            }),
            reason=full_reason,
            confidence=0.99
        ))

    # EXACT PROPORTIONAL SCORING FORMULA
    total_uploaded_documents = len(documents)
    total_matched_documents = sum(1 for result in verification_summary if result["match"])
    
    if total_uploaded_documents > 0:
        overall_score_percentage = (total_matched_documents / total_uploaded_documents) * 100
    else:
        overall_score_percentage = 0.0

    is_fraud = is_blacklisted or identity_spoofed

    # Assign Status without forcing the score to 0
    if is_fraud:
        risk_level = "HIGH_RISK"
        submission.status = "FRAUD_DETECTED"
        is_fully_compliant = False
    else:
        risk_level = "LOW_RISK" if overall_score_percentage == 100.0 else "MEDIUM_RISK" if overall_score_percentage >= 70.0 else "HIGH_RISK"
        submission.status = "EVALUATED"
        is_fully_compliant = (overall_score_percentage == 100.0)

    # NEW: AI RECOMMENDATION ENGINE
    # Only generate recommendations if the score is not 100% or if fraud is detected
    if not is_fully_compliant or is_fraud:
        
        # Clear old recommendations for this submission before creating new ones
        db.query(AIRecommendation).filter(AIRecommendation.submission_id == submission.id).delete()
        
        for item in verification_summary:
            if not item["match"]:
                doc_type = item["field_type"]
                db.add(AIRecommendation(
                    recommendation_id=f"REC-{uuid.uuid4().hex[:8].upper()}",
                    submission_id=submission.id,
                    recommendation_type="DOCUMENT_MISMATCH",
                    message=f"Your {doc_type} document failed verification. In the future, please ensure the uploaded document is completely legible and the ID matches the official Government registry exactly.",
                    severity="MEDIUM"
                ))
        
        if identity_spoofed:
            db.add(AIRecommendation(
                recommendation_id=f"REC-{uuid.uuid4().hex[:8].upper()}",
                submission_id=submission.id,
                recommendation_type="IDENTITY_DISCREPANCY",
                message="We detected differing legal entity names across your submitted documents. Please ensure your company name is updated and uniformly registered across your PAN, GST, and MSME Udyam profiles.",
                severity="HIGH"
            ))
            
        if is_blacklisted:
            db.add(AIRecommendation(
                recommendation_id=f"REC-{uuid.uuid4().hex[:8].upper()}",
                submission_id=submission.id,
                recommendation_type="STATUTORY_DEBARMENT",
                message="Your entity is currently flagged on a government debarment/blacklist. You must resolve this status with the issuing authority before applying for future tenders.",
                severity="HIGH"
            ))

    score_record = db.query(ScoreRiskAssessment).filter(ScoreRiskAssessment.submission_id == submission.id).first()
    if not score_record:
        db.add(ScoreRiskAssessment(
            submission_id=submission.id,
            compliance_score=overall_score_percentage,
            risk_level=risk_level,
            risk_score=100.0 - overall_score_percentage,
            score_breakdown_json=json.dumps({"passed": total_matched_documents, "total_uploaded": total_uploaded_documents}),
            risk_signals_json=json.dumps({
                "blacklisted": is_blacklisted,
                "debarment_reason": debarment_reason,
                "identity_spoofed": identity_spoofed,
                "mismatch_reasons": mismatch_reasons
            })
        ))
    else:
        score_record.compliance_score = overall_score_percentage
        score_record.risk_level = risk_level
        score_record.risk_score = 100.0 - overall_score_percentage
        score_record.risk_signals_json = json.dumps({
            "blacklisted": is_blacklisted,
            "debarment_reason": debarment_reason,
            "identity_spoofed": identity_spoofed,
            "mismatch_reasons": mismatch_reasons
        })
        
    db.commit()

    return {
        "status": submission.status.value,
        "application_id": application_id,
        "is_fully_compliant": is_fully_compliant,
        "overall_compliance_score": f"{overall_score_percentage:.1f}%",
        "risk_level": risk_level,
        "results": verification_summary
    }