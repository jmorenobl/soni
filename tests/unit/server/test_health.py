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

    def test_health_response_structure(self, test_client: TestClient):
        """Health response should have correct structure."""
        response = test_client.get("/health")
        data = response.json()

        assert "status" in data
        assert "version" in data
        assert "timestamp" in data
        assert isinstance(data["status"], str)
        assert data["status"] in ["healthy", "starting", "degraded", "unhealthy"]

    def test_health_always_available(self, test_client: TestClient):
        """Health endpoint should always be available."""
        # Multiple calls should all succeed
        for _ in range(3):
            response = test_client.get("/health")
            assert response.status_code == 200


class TestReadyEndpoint:
    """Tests for /ready endpoint."""

    def test_ready_returns_response(self, test_client: TestClient):
        """Ready endpoint should return a response."""
        response = test_client.get("/ready")
        # May be 200 (ready) or other status (not ready)
        assert response.status_code in [200, 503]

    def test_ready_response_structure(self, test_client: TestClient):
        """Ready response should have correct structure."""
        response = test_client.get("/ready")
        data = response.json()

        assert "ready" in data
        assert "message" in data
        assert isinstance(data["ready"], bool)


class TestStartupEndpoint:
    """Tests for /startup endpoint."""

    def test_startup_returns_response(self, test_client: TestClient):
        """Startup endpoint should return a response."""
        response = test_client.get("/startup")
        # May be 200 (started) or 503 (starting)
        assert response.status_code in [200, 503]
        assert "status" in response.json()


class TestVersionEndpoint:
    """Tests for /version endpoint."""

    def test_version_returns_200(self, test_client: TestClient):
        """Version endpoint should return 200 OK."""
        response = test_client.get("/version")
        assert response.status_code == 200

    def test_version_response_structure(self, test_client: TestClient):
        """Version response should have correct structure."""
        response = test_client.get("/version")
        data = response.json()

        assert "version" in data
        assert "major" in data
        assert "minor" in data
        assert "patch" in data
        assert isinstance(data["major"], int)
        assert isinstance(data["minor"], int)
