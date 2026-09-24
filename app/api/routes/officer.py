# app/api/routes/officer.py
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from typing import List, Dict, Any
from app.db.database import get_db
from app.db.models import User, BidSubmission, Tender, ScoreRiskAssessment, OfficerDecision, ProcurementOfficerProfile
from app.api.deps import require_role
from app.db.schemas import UserRole, OfficerDecisionType
from datetime import datetime, timezone
import uuid

router = APIRouter()

@router.get("/tenders/{tender_id}/bidders", status_code=status.HTTP_200_OK)
def get_bidder_leaderboard(
    tender_id: str, 
    db: Session = Depends(get_db),
    current_user: User = Depends(require_role([UserRole.PROCUREMENT_OFFICER]))
) -> List[Dict[str, Any]]:
    """
    Fetches all bidders for a specific tender, sorted by Compliance Score.
    This powers the Officer Dashboard comparison view.
    """
    tender = db.query(Tender).filter(Tender.tender_id == tender_id).first()
    if not tender:
        raise HTTPException(status_code=404, detail="Tender not found")

    submissions = db.query(BidSubmission).filter(BidSubmission.tender_id == tender.id).all()
    
    leaderboard = []
    for sub in submissions:
        # Fetch score if verification has run, otherwise default to 0
        score = sub.score_risk.compliance_score if sub.score_risk else 0.0
        risk = sub.score_risk.risk_level if sub.score_risk else "PENDING"
        
        leaderboard.append({
            "application_id": sub.application_id,
            "bidder_company": sub.bidder.company_name,
            "status": sub.status.value,
            "compliance_score": score,
            "risk_level": risk,
            "submitted_at": sub.submitted_at
        })

    # Sort dynamically: Highest score first. If tied, lowest risk wins.
    leaderboard.sort(key=lambda x: (x["compliance_score"], x["risk_level"] == "LOW_RISK"), reverse=True)
    return leaderboard

@router.post("/applications/{application_id}/decision", status_code=status.HTTP_201_CREATED)
def record_officer_decision(
    application_id: str,
    decision: OfficerDecisionType,
    comments: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_role([UserRole.PROCUREMENT_OFFICER]))
):
    """
    Records the final Human-in-the-Loop procurement decision.
    """
    submission = db.query(BidSubmission).filter(BidSubmission.application_id == application_id).first()
    if not submission:
        raise HTTPException(status_code=404, detail="Application not found")

    officer_profile = db.query(ProcurementOfficerProfile).filter(ProcurementOfficerProfile.user_id == current_user.id).first()
    
    # Upsert the decision
    existing_decision = db.query(OfficerDecision).filter(OfficerDecision.submission_id == submission.id).first()
    
    if existing_decision:
        existing_decision.decision = decision
        existing_decision.comments = comments
        existing_decision.decided_at = datetime.now(timezone.utc)
    else:
        new_decision = OfficerDecision(
            decision_id=f"DEC-{uuid.uuid4().hex[:8].upper()}",
            submission_id=submission.id,
            officer_id=officer_profile.id,
            decision=decision,
            comments=comments
        )
        db.add(new_decision)
    
    # Update overarching submission status
    submission.status = "DECIDED"
    db.commit()
    
    return {"status": "SUCCESS", "message": f"Decision {decision.value} recorded successfully."}