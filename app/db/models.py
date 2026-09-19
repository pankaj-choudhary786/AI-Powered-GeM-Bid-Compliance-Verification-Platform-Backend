# app/db/models.py
from sqlalchemy import (
    Column, Integer, String, Boolean, DateTime,
    ForeignKey, Float, Text, Enum
)
from sqlalchemy.orm import relationship
from datetime import datetime
import enum
from .database import Base

# ==========================================
# ENUMS
# ==========================================

class UserRole(str, enum.Enum):
    BIDDER = "BIDDER"
    TENDER_CREATOR = "TENDER_CREATOR"
    PROCUREMENT_OFFICER = "PROCUREMENT_OFFICER"

class AccountStatus(str, enum.Enum):
    ACTIVE = "ACTIVE"
    INACTIVE = "INACTIVE"
    LOCKED = "LOCKED"
    SUSPENDED = "SUSPENDED"

class TenderStatus(str, enum.Enum):
    DRAFT = "DRAFT"
    PUBLISHED = "PUBLISHED"
    BIDDING_OPEN = "BIDDING_OPEN"
    BIDDING_CLOSED = "BIDDING_CLOSED"
    UNDER_EVALUATION = "UNDER_EVALUATION"
    DECISION = "DECISION"
    COMPLETED = "COMPLETED"

class ApplicationStatus(str, enum.Enum):
    DRAFT = "DRAFT"
    SUBMITTED = "SUBMITTED"
    PROCESSING = "PROCESSING"
    VERIFIED = "VERIFIED"
    UNDER_REVIEW = "UNDER_REVIEW"
    DECIDED = "DECIDED"

class OfficerDecisionType(str, enum.Enum):
    QUALIFIED = "QUALIFIED"
    DISQUALIFIED = "DISQUALIFIED"
    NEEDS_FURTHER_REVIEW = "NEEDS_FURTHER_REVIEW"

class SourceType(str, enum.Enum):
    OFFICIAL_API = "OFFICIAL_API"
    AUTHORIZED_API = "AUTHORIZED_API"
    PUBLIC_SOURCE = "PUBLIC_SOURCE"
    MANUAL_IMPORT = "MANUAL_IMPORT"
    MOCK = "MOCK"

class ComplianceResult(str, enum.Enum):
    PASS = "PASS"
    FAIL = "FAIL"
    NEEDS_REVIEW = "NEEDS_REVIEW"
    MISSING = "MISSING"
    PENDING = "PENDING"

# ==========================================
# 1. CORE AUTH & USER PROFILES
# ==========================================

class User(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(String(32), unique=True, index=True, nullable=False)
    email = Column(String(255), unique=True, index=True, nullable=False)
    hashed_password = Column(String(255), nullable=False)
    role = Column(Enum(UserRole), nullable=False)
    account_status = Column(Enum(AccountStatus), default=AccountStatus.ACTIVE, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)

    bidder_profile = relationship("BidderProfile", back_populates="user", uselist=False, cascade="all, delete-orphan")
    tender_creator_profile = relationship("TenderCreatorProfile", back_populates="user", uselist=False, cascade="all, delete-orphan")
    officer_profile = relationship("ProcurementOfficerProfile", back_populates="user", uselist=False, cascade="all, delete-orphan")
    notifications = relationship("Notification", back_populates="user", cascade="all, delete-orphan")


class LoginAttempt(Base):
    __tablename__ = "login_attempts"

    id = Column(Integer, primary_key=True, index=True)
    email = Column(String(255), index=True, nullable=False)
    failed_count = Column(Integer, default=0, nullable=False)
    lockout_until = Column(DateTime, nullable=True)
    last_attempt_at = Column(DateTime, default=datetime.utcnow, nullable=False)


class BidderProfile(Base):
    __tablename__ = "bidder_profiles"

    id = Column(Integer, primary_key=True, index=True)
    bidder_id = Column(String(32), unique=True, index=True, nullable=False)
    user_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    company_name = Column(String(255), nullable=False)
    gstin = Column(String(15), nullable=True)
    pan = Column(String(10), nullable=True)
    udyam_number = Column(String(30), nullable=True)
    registered_address = Column(Text, nullable=True)

    user = relationship("User", back_populates="bidder_profile")
    submissions = relationship("BidSubmission", back_populates="bidder", cascade="all, delete-orphan")


class TenderCreatorProfile(Base):
    __tablename__ = "tender_creator_profiles"

    id = Column(Integer, primary_key=True, index=True)
    creator_id = Column(String(32), unique=True, index=True, nullable=False)
    user_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    department = Column(String(255), nullable=False)
    ministry = Column(String(255), nullable=True)

    user = relationship("User", back_populates="tender_creator_profile")
    tenders = relationship("Tender", back_populates="creator", cascade="all, delete-orphan")


class ProcurementOfficerProfile(Base):
    __tablename__ = "procurement_officer_profiles"

    id = Column(Integer, primary_key=True, index=True)
    officer_id = Column(String(32), unique=True, index=True, nullable=False)
    user_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    designation = Column(String(255), nullable=False)
    department = Column(String(255), nullable=False)

    user = relationship("User", back_populates="officer_profile")
    decisions = relationship("OfficerDecision", back_populates="officer")

# ==========================================
# 2. TENDERS & DYNAMIC REQUIREMENTS
# ==========================================

class Tender(Base):
    __tablename__ = "tenders"

    id = Column(Integer, primary_key=True, index=True)
    tender_id = Column(String(32), unique=True, index=True, nullable=False)
    creator_id = Column(Integer, ForeignKey("tender_creator_profiles.id", ondelete="CASCADE"), nullable=False)
    title = Column(String(255), nullable=False)
    description = Column(Text, nullable=True)
    category = Column(String(100), nullable=True)
    location = Column(String(255), nullable=True) # Added for Schema
    publish_date = Column(DateTime, nullable=True)
    bid_deadline = Column(DateTime, nullable=True)
    application_capacity = Column(Integer, default=100, nullable=False)
    status = Column(Enum(TenderStatus), default=TenderStatus.DRAFT, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)

    creator = relationship("TenderCreatorProfile", back_populates="tenders")
    requirements = relationship("TenderRequirement", back_populates="tender", cascade="all, delete-orphan")
    documents = relationship("TenderDocument", back_populates="tender", cascade="all, delete-orphan")
    submissions = relationship("BidSubmission", back_populates="tender", cascade="all, delete-orphan")


class TenderRequirement(Base):
    __tablename__ = "tender_requirements"

    id = Column(Integer, primary_key=True, index=True)
    requirement_id = Column(String(32), unique=True, index=True, nullable=False)
    tender_id = Column(Integer, ForeignKey("tenders.id", ondelete="CASCADE"), nullable=False)
    requirement_name = Column(String(255), nullable=False)
    description = Column(Text, nullable=True)
    mandatory = Column(Boolean, default=True, nullable=False)
    evidence_type = Column(String(50), nullable=False)
    accepted_formats = Column(String(100), default="pdf,jpg,png")
    validation_rule_type = Column(String(50), nullable=True)
    operator = Column(String(10), nullable=True)
    required_value = Column(String(255), nullable=True)
    unit = Column(String(50), nullable=True)
    weight = Column(Integer, default=10, nullable=False)
    display_order = Column(Integer, default=0, nullable=False)

    tender = relationship("Tender", back_populates="requirements")
    documents = relationship("BidderDocument", back_populates="requirement")
    verification_results = relationship("VerificationResult", back_populates="requirement")


class TenderDocument(Base):
    __tablename__ = "tender_documents"

    id = Column(Integer, primary_key=True, index=True)
    document_id = Column(String(32), unique=True, index=True, nullable=False)
    tender_id = Column(Integer, ForeignKey("tenders.id", ondelete="CASCADE"), nullable=False)
    file_name = Column(String(255), nullable=False)
    storage_path = Column(String(500), nullable=False)
    file_size_bytes = Column(Integer, nullable=False)
    sha256 = Column(String(64), nullable=False)
    uploaded_at = Column(DateTime, default=datetime.utcnow, nullable=False)

    tender = relationship("Tender", back_populates="documents")

# ==========================================
# 3. BIDDER SUBMISSIONS & DOCUMENTS
# ==========================================

class BidSubmission(Base):
    __tablename__ = "bid_submissions"

    id = Column(Integer, primary_key=True, index=True)
    application_id = Column(String(32), unique=True, index=True, nullable=False)
    bidder_id = Column(Integer, ForeignKey("bidder_profiles.id", ondelete="CASCADE"), nullable=False)
    tender_id = Column(Integer, ForeignKey("tenders.id", ondelete="CASCADE"), nullable=False)
    status = Column(Enum(ApplicationStatus), default=ApplicationStatus.DRAFT, nullable=False)
    submitted_at = Column(DateTime, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)

    bidder = relationship("BidderProfile", back_populates="submissions")
    tender = relationship("Tender", back_populates="submissions")
    documents = relationship("BidderDocument", back_populates="submission", cascade="all, delete-orphan")
    verification_results = relationship("VerificationResult", back_populates="submission", cascade="all, delete-orphan")
    cross_document_findings = relationship("CrossDocumentFinding", back_populates="submission", cascade="all, delete-orphan")
    government_verifications = relationship("GovernmentSourceRecord", back_populates="submission", cascade="all, delete-orphan") # Added relationship
    score_risk = relationship("ScoreRiskAssessment", back_populates="submission", uselist=False, cascade="all, delete-orphan")
    ai_recommendations = relationship("AIRecommendation", back_populates="submission", cascade="all, delete-orphan")
    officer_decision = relationship("OfficerDecision", back_populates="submission", uselist=False, cascade="all, delete-orphan")


class BidderDocument(Base):
    __tablename__ = "bidder_documents"

    id = Column(Integer, primary_key=True, index=True)
    document_id = Column(String(32), unique=True, index=True, nullable=False)
    submission_id = Column(Integer, ForeignKey("bid_submissions.id", ondelete="CASCADE"), nullable=False)
    requirement_id = Column(Integer, ForeignKey("tender_requirements.id", ondelete="CASCADE"), nullable=False)
    original_file_name = Column(String(255), nullable=False)
    stored_file_name = Column(String(255), nullable=False)
    storage_path = Column(String(500), nullable=False)
    enhanced_storage_path = Column(String(500), nullable=True)
    mime_type = Column(String(100), nullable=False)
    file_size_bytes = Column(Integer, nullable=False)
    sha256 = Column(String(64), nullable=False)
    processing_status = Column(String(50), default="UPLOADED", nullable=False)
    uploaded_at = Column(DateTime, default=datetime.utcnow, nullable=False)

    submission = relationship("BidSubmission", back_populates="documents")
    requirement = relationship("TenderRequirement", back_populates="documents")
    extracted_fields = relationship("ExtractedField", back_populates="document", cascade="all, delete-orphan")

# ==========================================
# 4. AI EXTRACTION & VERIFICATION DATA
# ==========================================

class ExtractedField(Base):
    __tablename__ = "extracted_fields"

    id = Column(Integer, primary_key=True, index=True)
    extracted_field_id = Column(String(32), unique=True, index=True, nullable=False)
    document_id = Column(Integer, ForeignKey("bidder_documents.id", ondelete="CASCADE"), nullable=False)
    field_key = Column(String(100), nullable=False)
    field_label = Column(String(255), nullable=True)
    raw_value = Column(Text, nullable=True)
    normalized_value = Column(Text, nullable=True)
    confidence = Column(Float, nullable=False)
    page_number = Column(Integer, default=1, nullable=False)
    bounding_box = Column(Text, nullable=True)

    document = relationship("BidderDocument", back_populates="extracted_fields")


class GovernmentSourceRecord(Base):
    __tablename__ = "government_source_records"

    id = Column(Integer, primary_key=True, index=True)
    source_record_id = Column(String(32), unique=True, index=True, nullable=False)
    submission_id = Column(Integer, ForeignKey("bid_submissions.id", ondelete="CASCADE"), nullable=False) # Linked to Submission
    source_name = Column(String(100), nullable=False)
    source_type = Column(Enum(SourceType), default=SourceType.MOCK, nullable=False)
    identifier_type = Column(String(50), nullable=False)
    identifier_value = Column(String(100), nullable=False)
    status = Column(String(50), nullable=False)
    matched = Column(Boolean, default=False, nullable=False) # Added for Schema
    response_data_json = Column(Text, nullable=True) # Added to store full JSON response
    raw_payload_path = Column(String(500), nullable=True)
    checked_at = Column(DateTime, default=datetime.utcnow, nullable=False)

    submission = relationship("BidSubmission", back_populates="government_verifications")


class VerificationResult(Base):
    __tablename__ = "verification_results"

    id = Column(Integer, primary_key=True, index=True)
    verification_id = Column(String(32), unique=True, index=True, nullable=False)
    submission_id = Column(Integer, ForeignKey("bid_submissions.id", ondelete="CASCADE"), nullable=False)
    requirement_id = Column(Integer, ForeignKey("tender_requirements.id", ondelete="CASCADE"), nullable=False)
    result = Column(Enum(ComplianceResult), nullable=False)
    rule_expression = Column(String(255), nullable=True)
    detected_value = Column(Text, nullable=True)
    expected_value = Column(Text, nullable=True)
    confidence = Column(Float, nullable=False)
    reason = Column(Text, nullable=False)
    requires_human_review = Column(Boolean, default=False, nullable=False)
    field_comparisons_json = Column(Text, nullable=True) # Added to store OCR vs DB diffs

    submission = relationship("BidSubmission", back_populates="verification_results")
    requirement = relationship("TenderRequirement", back_populates="verification_results")


class CrossDocumentFinding(Base):
    __tablename__ = "cross_document_findings"

    id = Column(Integer, primary_key=True, index=True)
    finding_id = Column(String(32), unique=True, index=True, nullable=False)
    submission_id = Column(Integer, ForeignKey("bid_submissions.id", ondelete="CASCADE"), nullable=False)
    finding_type = Column(String(100), nullable=False)
    severity = Column(String(20), nullable=False)
    status = Column(Enum(ComplianceResult), nullable=False)
    compared_data = Column(Text, nullable=False) 
    reason = Column(Text, nullable=False)
    confidence = Column(Float, nullable=False)

    submission = relationship("BidSubmission", back_populates="cross_document_findings")

# ==========================================
# 5. EVIDENCE GRAPH
# ==========================================

class EvidenceNode(Base):
    __tablename__ = "evidence_nodes"
    id = Column(Integer, primary_key=True, index=True)
    node_id = Column(String(64), unique=True, index=True, nullable=False)
    submission_id = Column(String(32), index=True, nullable=False)
    node_type = Column(String(50), nullable=False)
    label = Column(String(255), nullable=False)
    metadata_json = Column(Text, nullable=True)


class EvidenceEdge(Base):
    __tablename__ = "evidence_edges"
    id = Column(Integer, primary_key=True, index=True)
    edge_id = Column(String(64), unique=True, index=True, nullable=False)
    submission_id = Column(String(32), index=True, nullable=False)
    source_node_id = Column(String(64), nullable=False)
    target_node_id = Column(String(64), nullable=False)
    relationship_type = Column(String(50), nullable=False)

# ==========================================
# 6. SCORE, RISK, DECISION & AUDIT
# ==========================================

class ScoreRiskAssessment(Base):
    __tablename__ = "score_risk_assessments"
    id = Column(Integer, primary_key=True, index=True)
    submission_id = Column(Integer, ForeignKey("bid_submissions.id", ondelete="CASCADE"), nullable=False)
    compliance_score = Column(Float, nullable=False)
    risk_level = Column(String(20), nullable=False)
    risk_score = Column(Float, nullable=False)
    score_breakdown_json = Column(Text, nullable=False)
    risk_signals_json = Column(Text, nullable=False)
    calculated_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    submission = relationship("BidSubmission", back_populates="score_risk")


class AIRecommendation(Base):
    __tablename__ = "ai_recommendations"
    id = Column(Integer, primary_key=True, index=True)
    recommendation_id = Column(String(32), unique=True, index=True, nullable=False)
    submission_id = Column(Integer, ForeignKey("bid_submissions.id", ondelete="CASCADE"), nullable=False)
    recommendation_type = Column(String(50), nullable=False)
    message = Column(Text, nullable=False)
    severity = Column(String(20), nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    submission = relationship("BidSubmission", back_populates="ai_recommendations")


class OfficerDecision(Base):
    __tablename__ = "officer_decisions"
    id = Column(Integer, primary_key=True, index=True)
    decision_id = Column(String(32), unique=True, index=True, nullable=False)
    submission_id = Column(Integer, ForeignKey("bid_submissions.id", ondelete="CASCADE"), nullable=False)
    officer_id = Column(Integer, ForeignKey("procurement_officer_profiles.id"), nullable=False)
    decision = Column(Enum(OfficerDecisionType), nullable=False)
    comments = Column(Text, nullable=False)
    decided_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    submission = relationship("BidSubmission", back_populates="officer_decision")
    officer = relationship("ProcurementOfficerProfile", back_populates="decisions")


class AuditLog(Base):
    __tablename__ = "audit_logs"
    id = Column(Integer, primary_key=True, index=True)
    audit_id = Column(String(32), unique=True, index=True, nullable=False)
    actor_user_id = Column(String(32), nullable=False)
    actor_role = Column(String(50), nullable=False)
    action = Column(String(100), nullable=False)
    entity_type = Column(String(50), nullable=False)
    entity_id = Column(String(32), nullable=False)
    details_json = Column(Text, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)


class Notification(Base):
    __tablename__ = "notifications"
    id = Column(Integer, primary_key=True, index=True)
    notification_id = Column(String(32), unique=True, index=True, nullable=False)
    user_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    title = Column(String(255), nullable=False)
    message = Column(Text, nullable=False)
    is_read = Column(Boolean, default=False, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    user = relationship("User", back_populates="notifications")