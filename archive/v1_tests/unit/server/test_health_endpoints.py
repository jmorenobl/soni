"""Tests for health and readiness endpoints.

Verifies /health and /ready endpoints work correctly for Kubernetes integration.
"""

from datetime import datetime
from unittest.mock import MagicMock

import pytest
from fastapi.testclient import TestClient

from soni.server.api import app


@pytest.fixture
def client() -> TestClient:
    """Create test client."""
    return TestClient(app, raise_server_exceptions=False)


@pytest.fixture
def mock_runtime() -> MagicMock:
    """Create fully initialized mock runtime."""
    runtime = MagicMock()
    runtime._components = MagicMock()
    runtime._components.graph = MagicMock()
    runtime._components.du = MagicMock()
    runtime._components.flow_manager = MagicMock()
    runtime._components.checkpointer = MagicMock()
    return runtime


@pytest.fixture(autouse=True)
def reset_app_state() -> None:
    """Reset app state before each test."""
    app.state.runtime = None
    app.state.config = None


class TestHealthEndpoint:
    """Tests for /health liveness endpoint."""

    def test_health_returns_healthy_when_initialized(
        self, client: TestClient, mock_runtime: MagicMock
    ) -> None:
        """Test /health returns healthy when runtime is fully initialized."""
        app.state.runtime = mock_runtime

        response = client.get("/health")

        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "healthy"
        assert "version" in data
        assert "timestamp" in data

    def test_health_returns_starting_when_no_runtime(self, client: TestClient) -> None:
        """Test /health returns starting when runtime not yet created."""
        response = client.get("/health")

        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "starting"

    def test_health_returns_starting_when_no_components(self, client: TestClient) -> None:
        """Test /health returns starting when runtime has no components."""
        runtime = MagicMock()
        runtime._components = None
        app.state.runtime = runtime

        response = client.get("/health")

        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "starting"

    def test_health_returns_degraded_when_graph_missing(self, client: TestClient) -> None:
        """Test /health returns degraded when graph is not compiled."""
        runtime = MagicMock()
        runtime._components = MagicMock()
        runtime._components.graph = None
        app.state.runtime = runtime

        response = client.get("/health")

        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "degraded"

    def test_health_includes_component_details(
        self, client: TestClient, mock_runtime: MagicMock
    ) -> None:
        """Test /health includes component status details."""
        app.state.runtime = mock_runtime

        response = client.get("/health")

        data = response.json()
        assert "components" in data
        assert "runtime" in data["components"]
        assert "graph" in data["components"]

    def test_health_timestamp_is_valid_iso(
        self, client: TestClient, mock_runtime: MagicMock
    ) -> None:
        """Test timestamp is valid ISO format."""
        app.state.runtime = mock_runtime

        response = client.get("/health")

        data = response.json()
        # Should not raise
        datetime.fromisoformat(data["timestamp"].replace("Z", "+00:00"))


class TestReadinessEndpoint:
    """Tests for /ready readiness endpoint."""

    def test_ready_returns_200_when_fully_initialized(
        self, client: TestClient, mock_runtime: MagicMock
    ) -> None:
        """Test /ready returns 200 when service is ready."""
        app.state.runtime = mock_runtime

        response = client.get("/ready")

        assert response.status_code == 200
        data = response.json()
        assert data["ready"] is True
        assert "checks" in data

    def test_ready_returns_503_when_no_runtime(self, client: TestClient) -> None:
        """Test /ready returns 503 when runtime not created."""
        response = client.get("/ready")

        assert response.status_code == 503
        data = response.json()["detail"]
        assert data["ready"] is False
        assert "runtime_exists" in data["checks"]

    def test_ready_returns_503_when_graph_missing(self, client: TestClient) -> None:
        """Test /ready returns 503 when graph not compiled."""
        runtime = MagicMock()
        runtime._components = MagicMock()
        runtime._components.graph = None
        runtime._components.du = MagicMock()
        runtime._components.flow_manager = MagicMock()
        app.state.runtime = runtime

        response = client.get("/ready")

        assert response.status_code == 503

    def test_ready_checks_all_components(self, client: TestClient, mock_runtime: MagicMock) -> None:
        """Test /ready checks all required components."""
        app.state.runtime = mock_runtime

        response = client.get("/ready")

        data = response.json()
        checks = data["checks"]
        assert "runtime_exists" in checks
        assert "components_initialized" in checks
        assert "graph_ready" in checks

    def test_ready_fails_if_du_missing(self, client: TestClient) -> None:
        """Test /ready fails if DU module is missing."""
        runtime = MagicMock()
        runtime._components = MagicMock()
        runtime._components.graph = MagicMock()
        runtime._components.du = None  # Missing!
        runtime._components.flow_manager = MagicMock()
        app.state.runtime = runtime

        response = client.get("/ready")

        assert response.status_code == 503


class TestStartupEndpoint:
    """Tests for /startup startup probe endpoint."""

    def test_startup_returns_200_when_initialized(
        self, client: TestClient, mock_runtime: MagicMock
    ) -> None:
        """Test /startup returns 200 after initialization."""
        app.state.runtime = mock_runtime

        response = client.get("/startup")

        assert response.status_code == 200
        assert response.json()["started"] is True

    def test_startup_returns_503_during_init(self, client: TestClient) -> None:
        """Test /startup returns 503 during initialization."""
        response = client.get("/startup")

        assert response.status_code == 503


class TestKubernetesIntegration:
    """Tests simulating Kubernetes probe behavior."""

    def test_probe_sequence_during_startup(
        self, client: TestClient, mock_runtime: MagicMock
    ) -> None:
        """Test typical Kubernetes probe sequence during app startup."""
        # Phase 1: App starting, no runtime yet
        # Startup probe should fail (503)
        assert client.get("/startup").status_code == 503
        # Readiness should fail (503)
        assert client.get("/ready").status_code == 503
        # Health should return starting (200)
        assert client.get("/health").status_code == 200
        assert client.get("/health").json()["status"] == "starting"

        # Phase 2: Runtime initialized
        app.state.runtime = mock_runtime

        # All probes should succeed
        assert client.get("/startup").status_code == 200
        assert client.get("/ready").status_code == 200
        assert client.get("/health").status_code == 200
        assert client.get("/health").json()["status"] == "healthy"

    def test_probe_during_graceful_shutdown(
        self, client: TestClient, mock_runtime: MagicMock
    ) -> None:
        """Test probe behavior during graceful shutdown."""
        app.state.runtime = mock_runtime

        # Initially ready
        assert client.get("/ready").status_code == 200

        # Simulate shutdown: components being cleaned up
        mock_runtime._components = None

        # Readiness should fail (remove from load balancer)
        assert client.get("/ready").status_code == 503
        # Health should show starting/degraded
        assert client.get("/health").json()["status"] in ["starting", "degraded"]
