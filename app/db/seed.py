# app/db/seed.py
import json
from app.db.database import SessionLocal, Base, engine
from app.db.models import MockGovernmentRegistry

def seed_database():
    db = SessionLocal()
    
    print("\n[+] Wiping old government registry data...")
    db.query(MockGovernmentRegistry).delete()
    db.commit()

    print("[+] Seeding Mock Government Registry (Comprehensive Standards)...")
    
    records = [
        # =================================================================
        # PROFILE 1: The Golden Standard (Fully Compliant Enterprise)
        # Target: Passes all OCR and AI verification checks.
        # =================================================================
        MockGovernmentRegistry(
            entity_name="NEXGEN AI ROBOTICS LLP",
            pan="AAAFN5678K",
            pan_status="ACTIVE",
            gstin="07AAAFN5678K1ZQ",
            gst_registered_address="42, Okhla Industrial Area Phase 3, New Delhi, Delhi 110020",
            gst_status="ACTIVE",
            udyam_number="UDYAM-DL-01-0023456",
            msme_type="MEDIUM",
            cin="U72900DL2023PTC412345",
            date_of_incorporation="2023-01-15",
            dipp_number="DIPP12345",
            startup_recognition_status="APPROVED",
            # We pack the remaining 10+ government APIs into a metadata JSON block 
            # to simulate a massive API Setu / DigiLocker aggregate response.
            metadata_json=json.dumps({
                "mca21": {"company_status": "Active", "class": "Private", "directors": ["RAJ KUMAR", "PRIYA CHOUDHARY"]},
                "director_aadhaar_status": "[Aadhaar Redacted]", # Digitally signed and verified
                "epfo": {"establishment_code": "DL/CPM/1234567/000", "compliance_status": "FILED_UPTO_DATE"},
                "esic": {"employer_code": "11000123450000101", "status": "ACTIVE"},
                "nsic": {"registration_number": "NSIC/DEL/2024/001", "valid_till": "2028-12-31"},
                "make_in_india": {"local_content_percentage": 85.0, "class_type": "Class-I Local Supplier"},
                "bis_dpiit": {"certification_no": "CM/L-1234567", "status": "VALID"}
            })
        ),

        # =================================================================
        # PROFILE 2: The Exempted Startup
        # Target: Triggers startup exemption rules in your compliance engine.
        # =================================================================
        MockGovernmentRegistry(
            entity_name="QUANTUM AEROSPACE PVT LTD",
            pan="BBBCQ1111Z",
            pan_status="ACTIVE",
            gstin="29BBBCQ1111Z1Z5",
            gst_registered_address="101, Electronic City Phase 1, Bengaluru, Karnataka 560100",
            gst_status="ACTIVE",
            udyam_number="UDYAM-KR-03-0098765",
            msme_type="MICRO",
            cin="U73100KA2025PTC999999",
            date_of_incorporation="2025-08-22",
            dipp_number="DIPP98765",
            startup_recognition_status="APPROVED",
            metadata_json=json.dumps({
                "mca21": {"company_status": "Active", "class": "Private", "directors": ["ANITA SHARMA"]},
                "director_aadhaar_status": "[Aadhaar Redacted]",
                "epfo": {"establishment_code": "KR/BGL/9999999/000", "compliance_status": "EXEMPT_NEW_ENTITY"},
                "esic": {"employer_code": "41000999990000101", "status": "EXEMPT_NEW_ENTITY"},
                "nsic": {"registration_number": None, "valid_till": None},
                "make_in_india": {"local_content_percentage": 100.0, "class_type": "Class-I Local Supplier"},
                "bis_dpiit": {"certification_no": "PENDING_INSPECTION", "status": "PROVISIONAL"}
            })
        ),

        # =================================================================
        # PROFILE 3: The Fraud/Defaulter (High Risk)
        # Target: Designed to fail OCR cross-checks and trigger risk alerts.
        # =================================================================
        MockGovernmentRegistry(
            entity_name="SHADOW CORP SUPPLIERS",
            pan="CCCPX9999F",
            pan_status="ACTIVE",
            gstin="24CCCPX9999F1ZT",
            gst_registered_address="9, GIDC, Surat, Gujarat 395001",
            gst_status="SUSPENDED", # Fails active GST requirement
            udyam_number=None,      # Fails MSME requirement
            msme_type=None,
            cin="L74999GJ2010PLC040000",
            date_of_incorporation="2010-03-12",
            dipp_number=None,
            startup_recognition_status=None,
            metadata_json=json.dumps({
                "mca21": {"company_status": "Strike Off", "class": "Public", "directors": ["UNKNOWN"]},
                "director_aadhaar_status": "[Aadhaar Redacted]", # Flagged for mismatch
                "epfo": {"establishment_code": "GJ/SRT/4444444/000", "compliance_status": "DEFAULT_3_YEARS"},
                "esic": {"employer_code": "39000444440000101", "status": "SUSPENDED"},
                "nsic": {"registration_number": "REVOKED", "valid_till": "2021-01-01"},
                "make_in_india": {"local_content_percentage": 15.0, "class_type": "Non-Local Supplier"},
                "bis_dpiit": {"certification_no": None, "status": "UNREGISTERED"}
            })
        )
    ]
    
    db.add_all(records)
    db.commit()
    print(f"[+] Successfully seeded {len(records)} Mock Government Profiles.")
    db.close()
    print("[+] Database is clean and ready for API-driven End-to-End Testing.\n")

if __name__ == "__main__":
    Base.metadata.create_all(bind=engine)
    seed_database()