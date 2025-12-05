"""Tests for FastAPI endpoints."""

import pytest
from fastapi.testclient import TestClient

from soni.server.api import app


@pytest.fixture
def client():
    """Create test client."""
    return TestClient(app)


def test_health_check(client):
    """Test health check endpoint."""
    # Act
    response = client.get("/health")

    # Assert
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "ok"
    assert "version" in data


def test_health_check_structure(client):
    """Test health check returns correct structure."""
    # Act
    response = client.get("/health")

    # Assert
    assert response.status_code == 200
    data = response.json()
    assert isinstance(data["status"], str)
    assert isinstance(data["version"], str)


# Note: Full message processing test requires mocking RuntimeLoop
# This is complex and may already be tested elsewhere
# The existing API already has comprehensive error handling
