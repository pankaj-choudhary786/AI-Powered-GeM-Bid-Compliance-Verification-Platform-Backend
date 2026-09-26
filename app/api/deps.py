# app/api/deps.py
from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from sqlalchemy.orm import Session
from app.db.database import get_db
from app.db.models import User, UserRole
from app.core.security import decode_access_token

security = HTTPBearer()

def get_current_user(credentials: HTTPAuthorizationCredentials = Depends(security), db: Session = Depends(get_db)) -> User:
    token = credentials.credentials
    payload = decode_access_token(token)
    
    if payload is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired authentication token.",
            headers={"WWW-Authenticate": "Bearer"},
        )
        
    user_email = payload.get("sub")
    user = db.query(User).filter(User.email == user_email).first()
    
    if user is None:
        raise HTTPException(status_code=401, detail="User not found")
        
    return user

def require_role(allowed_roles: list[UserRole]):
    def role_checker(current_user: User = Depends(get_current_user)):
        # Convert both to string values to avoid Enum vs String mismatch
        user_role_str = current_user.role.value if hasattr(current_user.role, 'value') else str(current_user.role)
        allowed_roles_str = [r.value if hasattr(r, 'value') else str(r) for r in allowed_roles]
        
        if user_role_str not in allowed_roles_str:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Access denied. Requires one of: {allowed_roles_str}"
            )
        return current_user
    return role_checker