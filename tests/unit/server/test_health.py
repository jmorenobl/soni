import pytest
from fastapi.testclient import TestClient


class TestHealthEndpoint:
    """Tests for /health endpoint."""

    def test_health_returns_200(self, test_client: TestClient):
        """Health endpoint should return 200 OK."""
        response = test_client.get("/health")
        assert response.status_code == 200
        assert response.json()["status"] == "healthy"

    def test_health_includes_version(self, test_client: TestClient):
        """Health response should include version."""
        response = test_client.get("/health")
        assert "version" in response.json()
