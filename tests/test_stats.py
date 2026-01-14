"""
Tests for analytics/stats endpoint.
"""
from fastapi.testclient import TestClient
from app.main import app


client = TestClient(app)


def test_stats_endpoint():
    """Test stats endpoint returns correct structure."""
    response = client.get("/stats")
    assert response.status_code == 200
    data = response.json()
    
    assert "total_messages" in data
    assert "senders_count" in data
    assert "messages_per_sender" in data
    assert "first_message_ts" in data
    assert "last_message_ts" in data
    
    assert isinstance(data["total_messages"], int)
    assert isinstance(data["senders_count"], int)
    assert isinstance(data["messages_per_sender"], list)


def test_stats_empty_database():
    """Test stats when database is empty."""
    response = client.get("/stats")
    assert response.status_code == 200
    data = response.json()
    
    assert data["total_messages"] == 0
    assert data["senders_count"] == 0
    assert data["messages_per_sender"] == []
    assert data["first_message_ts"] is None
    assert data["last_message_ts"] is None
