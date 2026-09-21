# app/api/routes/auth.py
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from app.db.database import get_db
from app.db.schemas import SignupRequest, LoginRequest, TokenResponse, UserResponse
from app.db.models import User
from app.services.auth_service import create_user, authenticate_user
from app.core.security import create_access_token
from app.api.deps import get_current_user

router = APIRouter()

@router.post("/signup", response_model=UserResponse, status_code=status.HTTP_201_CREATED)
def signup(request: SignupRequest, db: Session = Depends(get_db)):
    existing_user = db.query(User).filter(User.email == request.email).first()
    if existing_user:
        raise HTTPException(status_code=400, detail="Email already registered")
    
    user = create_user(db, request)
    return user

@router.post("/login", response_model=TokenResponse)
def login(request: LoginRequest, db: Session = Depends(get_db)):
    user = authenticate_user(db, request)
    
    access_token = create_access_token(data={"sub": user.email, "role": user.role})
    
    redirect_map = {
        "BIDDER": "/bidder/dashboard",
        "TENDER_CREATOR": "/creator/dashboard",
        "PROCUREMENT_OFFICER": "/officer/dashboard"
    }
    
    return {
        "access_token": access_token,
        "token_type": "bearer",
        "user": user,
        "redirect_to": redirect_map.get(user.role, "/")
    }

@router.get("/me", response_model=UserResponse)
def get_me(current_user: User = Depends(get_current_user)):
    return current_user

@router.post("/logout")
def logout():
    return {"message": "Successfully logged out. Please delete the token on the client side."}