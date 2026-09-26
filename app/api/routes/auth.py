# app/api/routes/auth.py
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from app.db.database import get_db
from app.db.schemas import SignupRequest, LoginRequest, TokenResponse, UserResponse, FullProfileResponse, ProfileUpdateRequest
from app.db.models import User, BidderProfile, TenderCreatorProfile, ProcurementOfficerProfile
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

@router.get("/profile", response_model=FullProfileResponse)
def get_profile(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    profile = None
    if current_user.role.value == "BIDDER":
        profile = current_user.bidder_profile
        if not profile:
            profile = BidderProfile(user_id=current_user.id, company_name=current_user.email.split('@')[0])
            db.add(profile)
            db.commit()
            db.refresh(profile)
    elif current_user.role.value == "TENDER_CREATOR":
        profile = current_user.tender_creator_profile
        if not profile:
            profile = TenderCreatorProfile(user_id=current_user.id, department="Not Provided")
            db.add(profile)
            db.commit()
            db.refresh(profile)
    elif current_user.role.value == "PROCUREMENT_OFFICER":
        profile = current_user.officer_profile
        if not profile:
            profile = ProcurementOfficerProfile(user_id=current_user.id, department="Not Provided", designation="Not Provided")
            db.add(profile)
            db.commit()
            db.refresh(profile)

    if not profile:
        raise HTTPException(status_code=404, detail="Profile not found")

    return {
        "user": current_user,
        "profile": profile
    }

@router.put("/profile", response_model=FullProfileResponse)
def update_profile(
    request: ProfileUpdateRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    profile = None
    if current_user.role.value == "BIDDER":
        profile = current_user.bidder_profile
        if not profile:
            profile = BidderProfile(user_id=current_user.id, company_name=current_user.email.split('@')[0])
            db.add(profile)
        if request.company_name is not None:
            profile.company_name = request.company_name
        if request.gstin is not None:
            profile.gstin = request.gstin
        if request.pan is not None:
            profile.pan = request.pan
        if request.udyam_number is not None:
            profile.udyam_number = request.udyam_number
        if request.registered_address is not None:
            profile.registered_address = request.registered_address

    elif current_user.role.value == "TENDER_CREATOR":
        profile = current_user.tender_creator_profile
        if not profile:
            profile = TenderCreatorProfile(user_id=current_user.id, department="Not Provided")
            db.add(profile)
        if request.department is not None:
            profile.department = request.department
        if request.ministry is not None:
            profile.ministry = request.ministry

    elif current_user.role.value == "PROCUREMENT_OFFICER":
        profile = current_user.officer_profile
        if not profile:
            profile = ProcurementOfficerProfile(user_id=current_user.id, department="Not Provided", designation="Not Provided")
            db.add(profile)
        if request.department is not None:
            profile.department = request.department
        if request.designation is not None:
            profile.designation = request.designation

    if not profile:
        raise HTTPException(status_code=404, detail="Profile not found")

    db.commit()
    db.refresh(profile)

    return {
        "user": current_user,
        "profile": profile
    }

from pydantic import BaseModel
class WishlistRequest(BaseModel):
    tender_id: str

@router.get("/wishlist")
def get_wishlist(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    if current_user.role.value != "BIDDER" or not current_user.bidder_profile:
        return []
    meta = current_user.bidder_profile.meta_data or {}
    return meta.get("wishlist", [])

@router.post("/wishlist")
def toggle_wishlist(
    request: WishlistRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    if current_user.role.value != "BIDDER" or not current_user.bidder_profile:
        raise HTTPException(status_code=400, detail="Only bidders can have a wishlist")
    
    meta = current_user.bidder_profile.meta_data or {}
    wishlist = meta.get("wishlist", [])
    
    if request.tender_id in wishlist:
        wishlist.remove(request.tender_id)
    else:
        wishlist.append(request.tender_id)
        
    meta["wishlist"] = wishlist
    current_user.bidder_profile.meta_data = meta
    db.commit()
    
    return {"wishlist": wishlist}

@router.post("/logout")
def logout():
    return {"message": "Successfully logged out. Please delete the token on the client side."}