# scripts/seed_mock_gov_registry.py
import json
from app.db.database import SessionLocal, engine, Base
from app.db.models import MockGovernmentRegistry

Base.metadata.create_all(bind=engine)

def seed():
    db = SessionLocal()
    
    # Check if already seeded
    if db.query(MockGovernmentRegistry).count() > 0:
        print("[*] Mock Government Registry already seeded. Skipping.")
        db.close()
        return

    records = [
        # Scenario 1: Clean High-Value OEM (The Gold Standard)
        MockGovernmentRegistry(
            entity_name="BHARAT INFOTECH PRIVATE LIMITED",
            pan="AAACB1234D",
            gstin="27AAACB1234D1Z5",
            udyam_number="UDYAM-MH-18-0098765",
            cin="U72200MH2015PTC261234",
            gst_status="Active",
            pan_status="E",
            udyam_status="Verified",
            blacklisted=False,
            annual_turnover_cr=45.0,
            enterprise_type="Medium",
            startup_recognized=False,
            raw_gst_payload=json.dumps({
                "valid": True,
                "gstin": "27AAACB1234D1Z5",
                "lgnm": "BHARAT INFOTECH PRIVATE LIMITED",
                "tradeNam": "BHARAT COMPUTERS",
                "sts": "Active",
                "rgdt": "10/05/2015",
                "dty": "Regular",
                "pradr": {"addr": {"bno": "101", "st": "MIDC", "loc": "Andheri East", "pncd": "400093", "stcd": "Maharashtra"}}
            }),
            raw_pan_payload=json.dumps({
                "pan": "AAACB1234D",
                "name": "BHARAT INFOTECH PRIVATE LIMITED",
                "status": "E",
                "category": "C"
            }),
            raw_udyam_payload=json.dumps({
                "valid": True,
                "reg": "UDYAM-MH-18-0098765",
                "entity": "BHARAT INFOTECH PRIVATE LIMITED",
                "enterpriseType": "Medium"
            }),
            raw_gem_payload=json.dumps({
                "bidder_id": "GEM-BID-1001",
                "seller_name": "BHARAT INFOTECH PRIVATE LIMITED",
                "incident_history": {"total_incidents": 0, "blacklisted": False}
            }),
            metadata_json=json.dumps({
                "iso_certifications": ["ISO 9001:2015", "ISO 27001:2022"],
                "epfo_code": "MH/BAN/0012345/000",
                "esic_code": "31000123450000101",
                "dpiit_recognized": False,
                "security_clearance": "Level-2"
            })
        ),

        # Scenario 2: Startup / Micro Enterprise (Exemption Candidate)
        MockGovernmentRegistry(
            entity_name="NEXGEN AI ROBOTICS LLP",
            pan="AAAFN5678K",
            gstin="07AAAFN5678K1ZQ",
            udyam_number="UDYAM-DL-01-0023456",
            cin=None,
            gst_status="Active",
            pan_status="E",
            udyam_status="Verified",
            blacklisted=False,
            annual_turnover_cr=1.2,
            enterprise_type="Micro",
            startup_recognized=True,
            raw_gst_payload=json.dumps({
                "valid": True,
                "gstin": "07AAAFN5678K1ZQ",
                "lgnm": "NEXGEN AI ROBOTICS LLP",
                "tradeNam": "NEXGEN LABS",
                "sts": "Active",
                "rgdt": "01/01/2023",
                "dty": "Regular",
                "pradr": {"addr": {"bno": "42", "st": "Okhla Phase 3", "loc": "New Delhi", "pncd": "110020", "stcd": "Delhi"}}
            }),
            raw_pan_payload=json.dumps({
                "pan": "AAAFN5678K",
                "name": "NEXGEN AI ROBOTICS LLP",
                "status": "E",
                "category": "F"
            }),
            raw_udyam_payload=json.dumps({
                "valid": True,
                "reg": "UDYAM-DL-01-0023456",
                "entity": "NEXGEN AI ROBOTICS LLP",
                "enterpriseType": "Micro"
            }),
            raw_gem_payload=json.dumps({
                "bidder_id": "GEM-BID-2002",
                "seller_name": "NEXGEN AI ROBOTICS LLP",
                "incident_history": {"total_incidents": 0, "blacklisted": False}
            }),
            metadata_json=json.dumps({
                "dpiit_number": "DIPP12345",
                "incubator": "IIT Delhi Technology Business Incubator",
                "prior_experience_exemption_eligible": True,
                "turnover_relaxation_applied": True
            })
        ),

        # Scenario 3: Tax Defaulter / Suspended GST
        MockGovernmentRegistry(
            entity_name="DELTA SUPPLIERS ENTERPRISE",
            pan="AABFD9999M",
            gstin="24AABFD9999M1ZT",
            udyam_number=None,
            cin=None,
            gst_status="Suspended",
            pan_status="E",
            udyam_status=None,
            blacklisted=False,
            annual_turnover_cr=8.5,
            enterprise_type=None,
            startup_recognized=False,
            raw_gst_payload=json.dumps({
                "valid": True,
                "gstin": "24AABFD9999M1ZT",
                "lgnm": "DELTA SUPPLIERS ENTERPRISE",
                "tradeNam": "DELTA TRADERS",
                "sts": "Suspended",
                "rgdt": "12/03/2019",
                "dty": "Regular",
                "pradr": {"addr": {"bno": "9", "st": "GIDC", "loc": "Surat", "pncd": "395001", "stcd": "Gujarat"}}
            }),
            raw_pan_payload=json.dumps({
                "pan": "AABFD9999M",
                "name": "DELTA SUPPLIERS ENTERPRISE",
                "status": "E",
                "category": "P"
            }),
            raw_udyam_payload=None,
            raw_gem_payload=json.dumps({
                "bidder_id": "GEM-BID-3003",
                "seller_name": "DELTA SUPPLIERS ENTERPRISE",
                "incident_history": {"total_incidents": 1, "blacklisted": False}
            }),
            metadata_json=json.dumps({})
        ),

        # Scenario 4: Blacklisted Vendor
        MockGovernmentRegistry(
            entity_name="APEX GLOBAL CONTRACTS LTD",
            pan="AAACA5555L",
            gstin="06AAACA5555L1Z1",
            udyam_number=None,
            cin="L74999HR2010PLC040000",
            gst_status="Active",
            pan_status="E",
            udyam_status=None,
            blacklisted=True,
            annual_turnover_cr=120.0,
            enterprise_type=None,
            startup_recognized=False,
            raw_gst_payload=json.dumps({
                "valid": True,
                "gstin": "06AAACA5555L1Z1",
                "lgnm": "APEX GLOBAL CONTRACTS LTD",
                "tradeNam": "APEX CONTRACTS",
                "sts": "Active",
                "rgdt": "15/09/2010",
                "dty": "Regular",
                "pradr": {"addr": {"bno": "15", "st": "Sector 18", "loc": "Gurugram", "pncd": "122001", "stcd": "Haryana"}}
            }),
            raw_pan_payload=json.dumps({
                "pan": "AAACA5555L",
                "name": "APEX GLOBAL CONTRACTS LTD",
                "status": "E",
                "category": "C"
            }),
            raw_udyam_payload=None,
            raw_gem_payload=json.dumps({
                "bidder_id": "GEM-BID-4004",
                "seller_name": "APEX GLOBAL CONTRACTS LTD",
                "incident_history": {"total_incidents": 5, "blacklisted": True}
            }),
            metadata_json=json.dumps({
                "blacklisting_reason": "Failure to deliver critical infrastructure supplies",
                "blacklisted_until": "2028-12-31"
            })
        ),

        # Scenario 5: Identity Mismatch / Fraud Check (PAN and GSTIN do not align)
        MockGovernmentRegistry(
            entity_name="SHADOW CORP TRADING",
            pan="AAACX9999F", 
            gstin="29AAACP1111Z1Z5", # PAN embedded in GSTIN is AAACP1111Z, not AAACX9999F
            udyam_number=None,
            cin=None,
            gst_status="Active",
            pan_status="E",
            udyam_status=None,
            blacklisted=False,
            annual_turnover_cr=3.0,
            enterprise_type=None,
            startup_recognized=False,
            raw_gst_payload=json.dumps({
                "valid": True,
                "gstin": "29AAACP1111Z1Z5",
                "lgnm": "UNKNOWN ENTITY PVT LTD", # Name mismatch
                "tradeNam": "SHADOW CORP",
                "sts": "Active",
                "rgdt": "20/11/2021",
                "dty": "Regular",
                "pradr": {"addr": {"bno": "77", "st": "Ring Road", "loc": "Bengaluru", "pncd": "560001", "stcd": "Karnataka"}}
            }),
            raw_pan_payload=json.dumps({
                "pan": "AAACX9999F",
                "name": "SHADOW CORP TRADING",
                "status": "E",
                "category": "C"
            }),
            raw_udyam_payload=None,
            raw_gem_payload=json.dumps({
                "bidder_id": "GEM-BID-5005",
                "seller_name": "SHADOW CORP TRADING",
                "incident_history": {"total_incidents": 0, "blacklisted": False}
            }),
            metadata_json=json.dumps({
                "custom_risk_tags": ["HIGH_RISK_IDENTITY_MISMATCH"]
            })
        )
    ]

    db.add_all(records)
    db.commit()
    print(f"[+] Successfully seeded {len(records)} realistic Government Registry benchmark scenarios.")
    db.close()

if __name__ == "__main__":
    seed()