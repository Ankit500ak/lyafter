"""
Tests for messages listing and filtering.
"""
import json
import hashlib
import hmac
from fastapi.testclient import TestClient
from app.main import app


client = TestClient(app)

WEBHOOK_SECRET = "testsecret"


def get_signature(body: dict, secret: str) -> str:
    """Compute HMAC-SHA256 signature."""
    body_bytes = json.dumps(body).encode()
    return hmac.new(
        secret.encode(),
        body_bytes,
        hashlib.sha256,
    ).hexdigest()


def insert_message(message_id: str, from_number: str = "+919876543210", text: str = "Hello"):
    """Helper to insert a test message."""
    body = {
        "message_id": message_id,
        "from": from_number,
        "to": "+14155550100",
        "ts": "2025-01-15T10:00:00Z",
        "text": text,
    }
    signature = get_signature(body, WEBHOOK_SECRET)
    
    client.post(
        "/webhook",
        json=body,
        headers={
            "Content-Type": "application/json",
            "X-Signature": signature,
        },
    )


def test_messages_list():
    """Test basic messages listing."""
    response = client.get("/messages")
    assert response.status_code == 200
    data = response.json()
    assert "data" in data
    assert "total" in data
    assert "limit" in data
    assert "offset" in data


def test_messages_pagination():
    """Test pagination with limit and offset."""
    response = client.get("/messages?limit=10&offset=0")
    assert response.status_code == 200
    data = response.json()
    assert data["limit"] == 10
    assert data["offset"] == 0


def test_messages_limit_validation():
    """Test limit validation."""
    # Test max limit
    response = client.get("/messages?limit=200")
    assert response.status_code == 422
    
    # Test min limit
    response = client.get("/messages?limit=0")
    assert response.status_code == 422


def test_messages_filter_by_from():
    """Test filtering by from parameter."""
    response = client.get("/messages?from=%2B919876543210")  # URL-encoded +919876543210
    assert response.status_code == 200
    data = response.json()
    assert "data" in data


def test_messages_filter_by_since():
    """Test filtering by since parameter."""
    response = client.get("/messages?since=2025-01-15T09:30:00Z")
    assert response.status_code == 200
    data = response.json()
    assert "data" in data


def test_messages_search_by_text():
    """Test free-text search."""
    response = client.get("/messages?q=Hello")
    assert response.status_code == 200
    data = response.json()
    assert "data" in data
