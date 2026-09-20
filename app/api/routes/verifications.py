# app/api/routes/verifications.py
from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.responses import JSONResponse
from sqlalchemy.orm import Session
from app.db.database import get_db
from app.services.verification_service import execute_cross_document_matching

router = APIRouter()

@router.post("/documents/{application_id}")
def verify_documents_against_government_data(application_id: str, db: Session = Depends(get_db)):
    """
    Executes the automated compliance check. If documents are still in the OCR queue,
    returns a 202 PROCESSING state so the frontend can display a loading spinner.
    """
    matching_results = execute_cross_document_matching(db, application_id)
    
    if isinstance(matching_results, dict):
        if matching_results.get("status") == "PROCESSING":
            # Return HTTP 202 to tell the frontend: "Accepted, but still working"
            return JSONResponse(
                status_code=status.HTTP_202_ACCEPTED, 
                content=matching_results
            )
            
        elif matching_results.get("status") == "FAILED":
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST, 
                detail=matching_results.get("reason", "Verification failed.")
            )
            
    return matching_results