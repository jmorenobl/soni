from unittest.mock import AsyncMock, MagicMock

import pytest
from fastapi.testclient import TestClient


class TestResetEndpoint:
    """Tests for POST /reset/{user_id} endpoint."""

    @pytest.fixture
    def client_with_runtime(self):
        """Create test client with mocked runtime."""
        from soni.server.api import app

        mock_runtime = MagicMock()
        # Mocking the new method
        mock_runtime.reset_state = AsyncMock(return_value=True)
        # Use dependency overrides for reliability
        from soni.server.dependencies import get_runtime

        app.dependency_overrides[get_runtime] = lambda: mock_runtime

        # Also set on app.state just in case specific logic accesses it directly,
        # though get_runtime is preferred.
        app.state.runtime = mock_runtime

        client = TestClient(app)
        yield client, mock_runtime

        # Cleanup
        app.dependency_overrides.clear()

    def test_reset_returns_success_when_state_cleared(self, client_with_runtime):
        """Test that reset returns success=True when state was cleared."""
        client, mock_runtime = client_with_runtime
        mock_runtime.reset_state = AsyncMock(return_value=True)

        response = client.post("/reset/test_user")

        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True
        # We expect detailed message
        assert "has been reset" in data["message"]

    def test_reset_returns_success_when_no_state(self, client_with_runtime):
        """Test that reset returns success with appropriate message when no state."""
        client, mock_runtime = client_with_runtime
        mock_runtime.reset_state = AsyncMock(return_value=False)

        response = client.post("/reset/unknown_user")

        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True
        assert "No existing state" in data["message"]

    def test_reset_returns_error_on_failure(self, client_with_runtime):
        """Test that reset returns error when operation fails."""
        from soni.core.errors import StateError

        client, mock_runtime = client_with_runtime
        mock_runtime.reset_state = AsyncMock(side_effect=StateError("Database unavailable"))

        response = client.post("/reset/test_user")

        # Expecting generic error handler -> 500
        assert response.status_code == 500
        data = response.json()
        assert "error" in data["detail"]
