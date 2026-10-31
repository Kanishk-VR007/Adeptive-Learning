import os
import pytest
from fastapi.testclient import TestClient
from sqlalchemy import text
from app.main import app
from app.core.config import Settings, settings
from app.db.session import engine, SessionLocal


def test_app_starts_and_metadata():
    """Test that FastAPI app initialized with proper metadata and docs paths."""
    assert app.title == settings.PROJECT_NAME
    assert app.version == "1.0.0"
    assert app.openapi_url == f"{settings.API_V1_STR}/openapi.json"
    assert app.docs_url == f"{settings.API_V1_STR}/docs"


def test_health_check_endpoint(client: TestClient):
    """Test Stage A: API health check endpoint returns 200 healthy."""
    response = client.get("/health")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "healthy"
    assert data["service"] == settings.PROJECT_NAME
    assert data["environment"] == settings.ENVIRONMENT


def test_root_endpoint(client: TestClient):
    """Test Stage A: Root service endpoint returns API metadata."""
    response = client.get("/")
    assert response.status_code == 200
    data = response.json()
    assert "Welcome to" in data["message"]
    assert data["docs_url"] == f"{settings.API_V1_STR}/docs"
    assert data["health_url"] == "/health"
    assert data["api_v1"] == settings.API_V1_STR


def test_database_connection():
    """Test Stage A: Database connection succeeds and executes basic query."""
    with engine.connect() as connection:
        result = connection.execute(text("SELECT 1")).scalar()
        assert result == 1


def test_database_session_transaction():
    """Test Stage A: SessionLocal creates and closes cleanly."""
    db = SessionLocal()
    try:
        val = db.execute(text("SELECT 42")).scalar()
        assert val == 42
    finally:
        db.close()


def test_configuration_loading():
    """Test Stage A: Configuration loads environment defaults properly."""
    custom_settings = Settings(
        PROJECT_NAME="Custom Tutor Test",
        API_V1_STR="/api/test_v1",
        ENVIRONMENT="testing",
        SECRET_KEY="test-secret-key-12345",
        BACKEND_CORS_ORIGINS=["http://localhost:3000", "http://127.0.0.1:3000"]
    )
    assert custom_settings.PROJECT_NAME == "Custom Tutor Test"
    assert custom_settings.API_V1_STR == "/api/test_v1"
    assert custom_settings.ENVIRONMENT == "testing"
    assert len(custom_settings.BACKEND_CORS_ORIGINS) == 2


def test_cors_assembly_from_string():
    """Test Stage A: CORS string splitting validation."""
    custom = Settings(
        BACKEND_CORS_ORIGINS="http://localhost:3000, https://app.example.com"
    )
    assert custom.BACKEND_CORS_ORIGINS == ["http://localhost:3000", "https://app.example.com"]


def test_error_handling_not_found(client: TestClient):
    """Test Stage A: Unregistered routes return proper 404 response."""
    response = client.get("/api/v1/non_existent_route_test")
    assert response.status_code == 404
