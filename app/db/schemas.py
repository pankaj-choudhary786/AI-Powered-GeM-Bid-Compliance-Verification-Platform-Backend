# app/db/schemas.py
from pydantic import BaseModel, EmailStr, Field
from typing import List, Optional, Any, Dict
from datetime import datetime
from enum import Enum

# ==========================================
# SHARED ENUMS
# ==========================================

class UserRole(str, Enum):
    BIDDER = "BIDDER"
    TENDER_CREATOR = "TENDER_CREATOR"
    PROCUREMENT_OFFICER = "PROCUREMENT_OFFICER"

class TenderStatus(str, Enum):
    DRAFT = "DRAFT"
    PUBLISHED = "PUBLISHED"
    BIDDING_OPEN = "BIDDING_OPEN"
    BIDDING_CLOSED = "BIDDING_CLOSED"
    UNDER_EVALUATION = "UNDER_EVALUATION"
    DECISION = "DECISION"
    COMPLETED = "COMPLETED"

class ApplicationStatus(str, Enum):
    DRAFT = "DRAFT"
    SUBMITTED = "SUBMITTED"
    PROCESSING = "PROCESSING"
    VERIFIED = "VERIFIED"
    UNDER_REVIEW = "UNDER_REVIEW"
    DECIDED = "DECIDED"

class ComplianceResult(str, Enum):
    PASS = "PASS"
    FAIL = "FAIL"
    NEEDS_REVIEW = "NEEDS_REVIEW"
    MISSING = "MISSING"
    PENDING = "PENDING"

class OfficerDecisionType(str, Enum):
    QUALIFIED = "QUALIFIED"
    DISQUALIFIED = "DISQUALIFIED"
    NEEDS_FURTHER_REVIEW = "NEEDS_FURTHER_REVIEW"

# ==========================================
# 1. AUTHENTICATION & USERS
# ==========================================

class SignupRequest(BaseModel):
    email: EmailStr
    password: str = Field(..., min_length=8)
    role: UserRole
    company_name: Optional[str] = None
    department: Optional[str] = None
    designation: Optional[str] = None
    gstin: Optional[str] = None
    pan: Optional[str] = None
    udyam_number: Optional[str] = None
    registered_address: Optional[str] = None

class LoginRequest(BaseModel):
    email: EmailStr
    password: str
    selected_role: UserRole

class UserResponse(BaseModel):
    user_id: str
    email: EmailStr
    role: UserRole
    account_status: str
    class Config:
        from_attributes = True

class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    user: UserResponse
    redirect_to: str

class BidderProfileResponse(BaseModel):
    bidder_id: str
    company_name: str
    email: Optional[str] = None
    gstin: Optional[str] = None
    pan: Optional[str] = None
    udyam_number: Optional[str] = None
    registered_address: Optional[str] = None
    class Config:
        from_attributes = True

# ==========================================
# 2. TENDERS & REQUIREMENTS
# ==========================================

class RequirementCreateRequest(BaseModel):
    requirement_name: str
    description: Optional[str] = None
    mandatory: bool = True
    evidence_type: str
    accepted_formats: str = "pdf,jpg,png"
    validation_rule_type: Optional[str] = None
    operator: Optional[str] = None
    required_value: Optional[str] = None
    unit: Optional[str] = None
    weight: int = 10
    display_order: int = 0

class RequirementResponse(RequirementCreateRequest):
    requirement_id: str
    class Config:
        from_attributes = True

class TenderCreateRequest(BaseModel):
    title: str
    description: Optional[str] = None
    category: Optional[str] = None
    location: Optional[str] = None
    bid_deadline: Optional[datetime] = None
    application_capacity: int = 100
    requirements: List[RequirementCreateRequest] = []

class TenderResponse(BaseModel):
    tender_id: str
    title: str
    description: Optional[str] = None
    category: Optional[str] = None
    location: Optional[str] = None
    status: TenderStatus
    publish_date: Optional[datetime] = None
    bid_deadline: Optional[datetime] = None
    application_capacity: int
    total_requirements: int = 0
    mandatory_requirements: int = 0
    requirements: List[RequirementResponse] = []
    class Config:
        from_attributes = True

# ==========================================
# 3. VERIFICATION & AI EXTRACTION
# ==========================================

class BoundingBoxSchema(BaseModel):
    x1: float
    y1: float
    x2: float
    y2: float

class ExtractedFieldResponse(BaseModel):
    extracted_field_id: str
    document_id: str
    field_key: str
    field_label: Optional[str] = None
    raw_value: Optional[str] = None
    normalized_value: Optional[str] = None
    confidence: float
    page_number: int
    bounding_box: Optional[BoundingBoxSchema] = None
    class Config:
        from_attributes = True

class FieldComparisonSchema(BaseModel):
    field_key: str
    field_label: str
    ocr_value: Optional[str] = None
    ocr_normalized_value: Optional[str] = None
    ocr_confidence: Optional[float] = None
    database_value: Optional[str] = None
    database_normalized_value: Optional[str] = None
    database_source: Optional[str] = None
    expected_value: Optional[str] = None
    operator: Optional[str] = None
    unit: Optional[str] = None
    match_status: str
    mismatch_reason: Optional[str] = None
    document_id: Optional[str] = None
    extracted_field_id: Optional[str] = None

class VerificationResultResponse(BaseModel):
    verification_id: str
    requirement_id: str
    result: ComplianceResult
    rule_expression: Optional[str] = None
    detected_value: Optional[str] = None
    expected_value: Optional[str] = None
    confidence: float
    reason: str
    requires_human_review: bool
    field_comparisons: List[FieldComparisonSchema] = []
    class Config:
        from_attributes = True

# ==========================================
# 4. DOCUMENTS & SUBMISSIONS
# ==========================================

class DocumentUploadResponse(BaseModel):
    document_id: str
    requirement_id: str
    original_file_name: str
    mime_type: str
    file_size_bytes: int
    sha256: str
    processing_status: str
    uploaded_at: datetime

class DocumentAnalysisSchema(DocumentUploadResponse):
    extracted_fields: List[ExtractedFieldResponse] = []

class RequirementAnalysisSchema(BaseModel):
    requirement: RequirementResponse
    documents: List[DocumentAnalysisSchema] = []
    compliance_result: Optional[VerificationResultResponse] = None

class ComparedDocumentSchema(BaseModel):
    document_id: str
    file_name: str
    field_key: str
    extracted_value: str
    normalized_value: str

class CrossDocumentFindingResponse(BaseModel):
    finding_id: str
    finding_type: str
    severity: str
    status: ComplianceResult
    compared_documents: List[ComparedDocumentSchema] = []
    reason: str
    confidence: float
    class Config:
        from_attributes = True

class GovernmentVerificationResponse(BaseModel):
    source_record_id: str
    source_name: str
    source_type: str
    identifier_type: str
    identifier_value: str
    status: str
    matched: bool
    response_data: Dict[str, Any] = {}
    checked_at: datetime
    class Config:
        from_attributes = True

# ==========================================
# 5. EVIDENCE GRAPH & RECOMMENDATIONS
# ==========================================

class EvidenceNodeSchema(BaseModel):
    id: str
    type: str 
    label: str
    data: Optional[Dict[str, Any]] = None

class EvidenceEdgeSchema(BaseModel):
    id: str
    source: str
    target: str
    label: str

class EvidenceGraphResponse(BaseModel):
    nodes: List[EvidenceNodeSchema]
    edges: List[EvidenceEdgeSchema]

class AIRecommendationResponse(BaseModel):
    recommendation_id: str
    recommendation_type: str
    message: str
    severity: str
    created_at: datetime
    class Config:
        from_attributes = True

class OfficerDecisionResponse(BaseModel):
    decision_id: str
    decision: OfficerDecisionType
    comments: str
    officer_id: str
    decided_at: datetime
    class Config:
        from_attributes = True

class AuditLogResponse(BaseModel):
    audit_id: str
    actor_user_id: str
    actor_role: str
    action: str
    entity_type: str
    entity_id: str
    details_json: Optional[str] = None
    created_at: datetime
    class Config:
        from_attributes = True

# ==========================================
# 6. THE DASHBOARD MEGA-SCHEMA
# ==========================================

class ApplicationDashboardResponse(BaseModel):
    application_id: str
    application_status: ApplicationStatus
    submitted_at: Optional[datetime] = None
    tender: TenderResponse
    bidder: BidderProfileResponse
    requirements_analysis: List[RequirementAnalysisSchema] = []
    cross_document_findings: List[CrossDocumentFindingResponse] = []
    government_verifications: List[GovernmentVerificationResponse] = []
    ai_recommendations: List[AIRecommendationResponse] = []
    evidence_graph: Optional[EvidenceGraphResponse] = None
    decision: Optional[OfficerDecisionResponse] = None
    audit_trail: List[AuditLogResponse] = []