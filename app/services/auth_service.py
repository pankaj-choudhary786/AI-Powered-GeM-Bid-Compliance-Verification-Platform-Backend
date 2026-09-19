# app/services/auth_service.py
from sqlalchemy.orm import Session
from datetime import datetime, timedelta, timezone
import uuid
from app.db.models import User, BidderProfile, TenderCreatorProfile, ProcurementOfficerProfile, LoginAttempt, UserRole
from app.core.security import get_password_hash, verify_password
from app.core.exceptions import InvalidCredentialsException, RoleMismatchException, AccountLockedException
from app.core.config import settings

def _generate_id(prefix: str) -> str:
    year = datetime.utcnow().year
    random_hex = uuid.uuid4().hex[:6].upper()
    return f"{prefix}-{year}-{random_hex}"

def check_login_attempts(db: Session, email: str):
    attempt = db.query(LoginAttempt).filter(LoginAttempt.email == email).first()
    if not attempt:
        attempt = LoginAttempt(email=email)
        db.add(attempt)
        db.commit()
        db.refresh(attempt)
    
    if attempt.lockout_until and attempt.lockout_until.replace(tzinfo=timezone.utc) > datetime.now(timezone.utc):
        remaining = (attempt.lockout_until.replace(tzinfo=timezone.utc) - datetime.now(timezone.utc)).seconds
        raise AccountLockedException(remaining_seconds=remaining)
    return attempt

def record_failed_login(db: Session, attempt: LoginAttempt):
    attempt.failed_count += 1
    attempt.last_attempt_at = datetime.utcnow()
    if attempt.failed_count >= settings.MAX_LOGIN_ATTEMPTS:
        attempt.lockout_until = datetime.utcnow() + timedelta(minutes=settings.LOCKOUT_MINUTES)
    db.commit()

def clear_login_attempts(db: Session, attempt: LoginAttempt):
    attempt.failed_count = 0
    attempt.lockout_until = None
    db.commit()

def create_user(db: Session, signup_data):
    # Create Base User
    new_user = User(
        user_id=_generate_id("USR"),
        email=signup_data.email,
        hashed_password=get_password_hash(signup_data.password),
        role=signup_data.role
    )
    db.add(new_user)
    db.flush() # Get ID without committing yet

    # Create Specific Profile based on Role
    if signup_data.role == UserRole.BIDDER:
        profile = BidderProfile(
            bidder_id=_generate_id("BID"),
            user_id=new_user.id,
            company_name=signup_data.company_name or "New Company"
        )
    elif signup_data.role == UserRole.TENDER_CREATOR:
        profile = TenderCreatorProfile(
            creator_id=_generate_id("TCR"),
            user_id=new_user.id,
            department=signup_data.department or "General Dept"
        )
    elif signup_data.role == UserRole.PROCUREMENT_OFFICER:
        profile = ProcurementOfficerProfile(
            officer_id=_generate_id("POF"),
            user_id=new_user.id,
            designation=signup_data.designation or "Officer",
            department=signup_data.department or "Procurement Dept"
        )
    
    db.add(profile)
    db.commit()
    db.refresh(new_user)
    return new_user

def authenticate_user(db: Session, login_data):
    attempt = check_login_attempts(db, login_data.email)
    
    user = db.query(User).filter(User.email == login_data.email).first()
    if not user or not verify_password(login_data.password, user.hashed_password):
        record_failed_login(db, attempt)
        raise InvalidCredentialsException()

    if user.role != login_data.selected_role:
        record_failed_login(db, attempt)
        raise RoleMismatchException(expected_role=login_data.selected_role, actual_role=user.role)

    clear_login_attempts(db, attempt)
    return user