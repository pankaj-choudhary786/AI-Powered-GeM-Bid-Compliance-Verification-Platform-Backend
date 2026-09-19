# tests/test_auth.py
from fastapi.testclient import TestClient
from app.main import app
from app.db.database import Base, engine, SessionLocal
from app.db.schemas import UserRole
import pytest

client = TestClient(app)

@pytest.fixture(autouse=True)
def setup_db():
    Base.metadata.create_all(bind=engine)
    yield
    # Clean up test DB after if needed, omitted here to keep dummy data intact

def test_signup_and_login():
    # 1. Signup Bidder
    client.post("/api/auth/signup", json={
        "email": "test_bidder@test.com", "password": "password123", "role": "BIDDER"
    })
    
    # 2. Login Bidder successfully
    res = client.post("/api/auth/login", json={
        "email": "test_bidder@test.com", "password": "password123", "selected_role": "BIDDER"
    })
    assert res.status_code == 200
    assert "access_token" in res.json()
    assert res.json()["redirect_to"] == "/bidder/dashboard"

def test_role_mismatch():
    res = client.post("/api/auth/login", json={
        "email": "test_bidder@test.com", "password": "password123", "selected_role": "PROCUREMENT_OFFICER"
    })
    assert res.status_code == 403
    assert "Role mismatch" in res.json()["detail"]

def test_lockout():
    email = "lockout_test@test.com"
    client.post("/api/auth/signup", json={"email": email, "password": "password123", "role": "BIDDER"})
    
    # Fail 5 times
    for _ in range(5):
        res = client.post("/api/auth/login", json={"email": email, "password": "wrong", "selected_role": "BIDDER"})
    
    # 6th time should be a lockout error, even with correct password
    res = client.post("/api/auth/login", json={"email": email, "password": "password123", "selected_role": "BIDDER"})
    assert res.status_code == 403
    assert res.json()["detail"]["code"] == "ACCOUNT_LOCKED"