"""
Tests for the webhook endpoint.
"""
import json
import hashlib
import hmac
import pytest
from fastapi.testclient import TestClient
from app.main import app
from app.config import config


client = TestClient(app)

WEBHOOK_SECRET = "testsecret"
VALID_MESSAGE = {
    "message_id": "m1",
    "from": "+919876543210",
    "to": "+14155550100",
    "ts": "2025-01-15T10:00:00Z",
    "text": "Hello"
}


def get_signature(body: dict, secret: str) -> str:
    """Compute HMAC-SHA256 signature."""
    body_bytes = json.dumps(body).encode()
    return hmac.new(
        secret.encode(),
        body_bytes,
        hashlib.sha256,
    ).hexdigest()


@pytest.fixture
def setup_env(monkeypatch):
    """Set env vars for tests."""
    monkeypatch.setenv("WEBHOOK_SECRET", WEBHOOK_SECRET)
    monkeypatch.setenv("DATABASE_URL", "sqlite:////tmp/test.db")


def test_webhook_valid_signature(setup_env):
    """Valid signature should work"""
    body = VALID_MESSAGE.copy()
    signature = get_signature(body, WEBHOOK_SECRET)
    
    response = client.post(
        "/webhook",
        json=body,
        headers={
            "Content-Type": "application/json",
            "X-Signature": signature,
        },
    )
    
    assert response.status_code == 200
    assert response.json()["status"] == "ok"


def test_webhook_invalid_signature(setup_env):
    """Bad signature should be rejected"""
    body = VALID_MESSAGE.copy()
    
    response = client.post(
        "/webhook",
        json=body,
        headers={
            "Content-Type": "application/json",
            "X-Signature": "invalid",
        },
    )
    
    assert response.status_code == 401
    assert "invalid signature" in response.json()["detail"]


def test_webhook_missing_signature(setup_env):
    """No signature should fail"""
    body = VALID_MESSAGE.copy()
    
    response = client.post(
        "/webhook",
        json=body,
        headers={"Content-Type": "application/json"},
    )
    
    assert response.status_code == 401


def test_webhook_duplicate_idempotency(setup_env):
    """Test that duplicate messages are handled idempotently."""
    body = VALID_MESSAGE.copy()
    signature = get_signature(body, WEBHOOK_SECRET)
    
    # First request
    response1 = client.post(
        "/webhook",
        json=body,
        headers={
            "Content-Type": "application/json",
            "X-Signature": signature,
        },
    )
    assert response1.status_code == 200
    
    # Duplicate request
    response2 = client.post(
        "/webhook",
        json=body,
        headers={
            "Content-Type": "application/json",
            "X-Signature": signature,
        },
    )
    assert response2.status_code == 200
    assert response2.json()["status"] == "ok"


def test_webhook_invalid_phone_format(setup_env):
    """Test webhook with invalid phone number format."""
    body = VALID_MESSAGE.copy()
    body["from"] = "919876543210"  # Missing +
    signature = get_signature(body, WEBHOOK_SECRET)
    
    response = client.post(
        "/webhook",
        json=body,
        headers={
            "Content-Type": "application/json",
            "X-Signature": signature,
        },
    )
    
    assert response.status_code == 422


def test_webhook_invalid_timestamp_format(setup_env):
    """Test webhook with invalid timestamp format."""
    body = VALID_MESSAGE.copy()
    body["ts"] = "2025-01-15T10:00:00"  # Missing Z
    signature = get_signature(body, WEBHOOK_SECRET)
    
    response = client.post(
        "/webhook",
        json=body,
        headers={
            "Content-Type": "application/json",
            "X-Signature": signature,
        },
    )
    
    assert response.status_code == 422


def test_health_live(setup_env):
    """Test liveness probe."""
    response = client.get("/health/live")
    assert response.status_code == 200
    assert response.json()["status"] == "alive"
