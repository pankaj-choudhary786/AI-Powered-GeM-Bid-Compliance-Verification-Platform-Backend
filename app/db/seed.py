# app/db/seed.py
from app.db.database import SessionLocal, Base, engine
from app.db.schemas import SignupRequest, UserRole
from app.services.auth_service import create_user
from app.db.models import User

def seed_database():
    db = SessionLocal()
    print("Seeding demo accounts...")
    
    accounts = [
        SignupRequest(email="bidder@test.com", password="password123", role=UserRole.BIDDER, company_name="Test Bidder Pvt Ltd"),
        SignupRequest(email="creator@test.com", password="password123", role=UserRole.TENDER_CREATOR, department="Ministry of Testing"),
        SignupRequest(email="officer@test.com", password="password123", role=UserRole.PROCUREMENT_OFFICER, designation="Chief Officer")
    ]
    
    for acc in accounts:
        if not db.query(User).filter(User.email == acc.email).first():
            create_user(db, acc)
            print(f"Created {acc.role}: {acc.email}")
        else:
            print(f"Skipped {acc.email} (already exists)")
            
    db.close()
    print("Seeding complete.")

if __name__ == "__main__":
    Base.metadata.create_all(bind=engine)
    seed_database()