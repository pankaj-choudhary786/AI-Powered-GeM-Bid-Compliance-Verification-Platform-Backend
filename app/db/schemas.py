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

class LockoutStatusResponse(BaseModel):
    locked: bool
    remaining_seconds: int = 0
    message: str

# ==========================================
# 2. TENDERS & REQUIREMENTS
# ==========================================

class RequirementCreateRequest(BaseModel):
    requirement_name: str
    description: Optional[str] = None
    mandatory: bool = True
    evidence_type: str  # FILE, LINK, STRUCTURED_VALUE
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
    bid_deadline: Optional[datetime] = None
    application_capacity: int = 100
    requirements: List[RequirementCreateRequest] = []

class TenderResponse(BaseModel):
    tender_id: str
    title: str
    description: Optional[str] = None
    category: Optional[str] = None
    status: TenderStatus
    publish_date: Optional[datetime] = None
    bid_deadline: Optional[datetime] = None
    application_capacity: int
    requirements: List[RequirementResponse] = []

    class Config:
        from_attributes = True

# ==========================================
# 3. BIDDER SUBMISSIONS & DOCUMENTS
# ==========================================

class ApplicationCreateRequest(BaseModel):
    tender_id: str

class DocumentUploadResponse(BaseModel):
    document_id: str
    requirement_id: str
    file_name: str
    processing_status: str
    sha256: str

class ApplicationResponse(BaseModel):
    application_id: str
    tender_id: str
    bidder_id: str
    status: ApplicationStatus
    submitted_at: Optional[datetime] = None
    documents: List[DocumentUploadResponse] = []

    class Config:
        from_attributes = True

# ==========================================
# 4. VERIFICATION & AI EXTRACTION
# ==========================================

class ExtractedFieldResponse(BaseModel):
    extracted_field_id: str
    field_key: str
    field_label: Optional[str] = None
    raw_value: Optional[str] = None
    normalized_value: Optional[str] = None
    confidence: float
    page_number: int

    class Config:
        from_attributes = True

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

    class Config:
        from_attributes = True

class CrossDocumentFindingResponse(BaseModel):
    finding_id: str
    finding_type: str
    severity: str
    status: ComplianceResult
    compared_data: str
    reason: str
    confidence: float

    class Config:
        from_attributes = True

# ==========================================
# 5. EVIDENCE GRAPH (INNOVATION 3)
# ==========================================

class EvidenceNodeSchema(BaseModel):
    id: str
    type: str  # TENDER_REQUIREMENT, DOCUMENT, EXTRACTED_FIELD, RULE, RESULT
    label: str
    data: Optional[Dict[str, Any]] = None

class EvidenceEdgeSchema(BaseModel):
    id: str
    source: str
    target: str
    label: str  # SATISFIED_BY, EXTRACTED_FROM, EVALUATED_BY

class EvidenceGraphResponse(BaseModel):
    nodes: List[EvidenceNodeSchema]
    edges: List[EvidenceEdgeSchema]

# ==========================================
# 6. SCORE, RISK & OFFICER DASHBOARD
# ==========================================

class ScoreComponentSchema(BaseModel):
    requirement_name: str
    weight: int
    result: str
    score_awarded: float

class RiskSignalSchema(BaseModel):
    signal: str
    severity: str
    impact: str

class ScoreRiskResponse(BaseModel):
    compliance_score: float
    risk_level: str
    risk_score: float
    components: List[ScoreComponentSchema]
    signals: List[RiskSignalSchema]

class AIRecommendationResponse(BaseModel):
    recommendation_id: str
    recommendation_type: str
    message: str
    severity: str

    class Config:
        from_attributes = True

class BidderComparisonItem(BaseModel):
    application_id: str
    bidder_id: str
    company_name: str
    compliance_score: float
    risk_level: str
    passed_count: int
    failed_count: int
    review_count: int
    application_status: ApplicationStatus

class OfficerDecisionRequest(BaseModel):
    decision: OfficerDecisionType
    comments: str

class OfficerDecisionResponse(BaseModel):
    decision_id: str
    application_id: str
    decision: OfficerDecisionType
    comments: str
    decided_at: datetime

    class Config:
        from_attributes = True

# ==========================================
# 7. AUDIT & NOTIFICATIONS
# ==========================================

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

class NotificationResponse(BaseModel):
    notification_id: str
    title: str
    message: str
    is_read: bool
    created_at: datetime

    class Config:
        from_attributes = True