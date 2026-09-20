# tests/test_documents.py
import pytest
from fastapi.testclient import TestClient
from app.main import app
from app.api.deps import get_current_user
from app.db.models import User
import io

client = TestClient(app)

# Override the base authentication dependency instead of the role checker
def mock_get_current_user():
    return User(id=1, user_id="USR-TEST", role="BIDDER")

# Apply the override to bypass the JWT token check
app.dependency_overrides[get_current_user] = mock_get_current_user

def test_upload_rejection_for_exe_files():
    # Simulate a malicious executable file payload
    fake_exe = io.BytesIO(b"MZ\x90\x00\x03\x00\x00\x00\x04\x00\x00\x00\xFF\xFF")
    
    response = client.post(
        "/api/documents/upload",
        data={
            "application_id": "APP-TEST-123",
            "requirement_id": "REQ-TEST-123"
        },
        files={
            "file": ("virus.exe", fake_exe, "application/x-msdownload")
        }
    )
    
    # 1. Assert the server successfully reaches the logic and returns a 400 Bad Request
    assert response.status_code == 400
    
    # 2. Assert the rejection message specifically names the MIME type limit
    assert "Rejected" in response.json()["detail"]
    assert "application/x-msdownload" in response.json()["detail"]