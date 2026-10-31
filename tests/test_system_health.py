import pytest
from fastapi.testclient import TestClient
from app.main import app

client = TestClient(app)


def test_health_live_endpoint():
    """Verify that /health/live returns HTTP 200 with alive status."""
    res = client.get("/health/live")
    assert res.status_code == 200
    data = res.json()
    assert data["status"] == "alive"
    assert "service" in data


def test_health_ready_endpoint():
    """Verify that /health/ready connects to database and returns ready."""
    res = client.get("/health/ready")
    assert res.status_code == 200
    data = res.json()
    assert data["status"] == "ready"
    assert data["database"] == "connected"


def test_system_status_endpoint():
    """Verify that /api/v1/system/status returns diagnostic breakdown."""
    res = client.get("/api/v1/system/status")
    assert res.status_code == 200
    data = res.json()
    assert "components" in data
    assert data["components"]["api"]["status"] == "online"
    assert data["components"]["database"]["status"] == "connected"
    assert "operational_capabilities" in data
    assert data["operational_capabilities"]["deterministic_bkt_active"] is True
    assert data["operational_capabilities"]["fsrs_revisions_active"] is True
