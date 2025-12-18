"""Tests for FastAPI dependency injection."""

from unittest.mock import AsyncMock, Mock

import pytest
from fastapi import HTTPException, Request

from soni.server.dependencies import get_config, get_runtime


class TestGetRuntime:
    """Test runtime dependency."""

    def test_returns_runtime_when_initialized(self):
        """Should return runtime from app.state."""
        mock_runtime = Mock()
        mock_request = Mock(spec=Request)
        mock_request.app.state.runtime = mock_runtime

        result = get_runtime(mock_request)

        assert result is mock_runtime

    def test_raises_503_when_not_initialized(self):
        """Should raise 503 when runtime is None."""
        mock_request = Mock(spec=Request)
        mock_request.app.state.runtime = None

        with pytest.raises(HTTPException) as exc_info:
            get_runtime(mock_request)

        assert exc_info.value.status_code == 503

    def test_raises_503_when_state_missing_attribute(self):
        """Should raise 503 when state attribute missing."""
        mock_request = Mock(spec=Request)
        # getattr will return None for missing attribute
        mock_request.app.state = Mock(spec=[])

        with pytest.raises(HTTPException) as exc_info:
            get_runtime(mock_request)

        assert exc_info.value.status_code == 503


class TestGetConfig:
    """Test config dependency."""

    def test_returns_config_when_loaded(self):
        """Should return config from app.state."""
        mock_config = Mock()
        mock_request = Mock(spec=Request)
        mock_request.app.state.config = mock_config

        result = get_config(mock_request)

        assert result is mock_config

    def test_raises_503_when_not_loaded(self):
        """Should raise 503 when config is None."""
        mock_request = Mock(spec=Request)
        mock_request.app.state.config = None

        with pytest.raises(HTTPException) as exc_info:
            get_config(mock_request)

        assert exc_info.value.status_code == 503


class TestDependencyIntegration:
    """Integration tests for dependency injection in endpoints."""

    @pytest.fixture
    def app_with_runtime(self):
        """Create app with mocked runtime in state."""
        from soni.server.api import create_app

        app = create_app()

        # Mock runtime in state
        mock_runtime = AsyncMock()
        mock_runtime.process_message = AsyncMock(return_value="Hello!")
        mock_runtime.get_state = AsyncMock(return_value=None)

        app.state.runtime = mock_runtime
        app.state.config = Mock()

        return app, mock_runtime

    def test_message_endpoint_uses_injected_runtime(self, app_with_runtime):
        """POST /message should use runtime from dependency."""
        from fastapi.testclient import TestClient

        app, mock_runtime = app_with_runtime
        client = TestClient(app, raise_server_exceptions=False)

        _response = client.post(
            "/message",
            json={"user_id": "test", "message": "hello"},
        )

        # Verify runtime was called
        mock_runtime.process_message.assert_called_once()

    def test_state_endpoint_uses_injected_runtime(self, app_with_runtime):
        """GET /state should use runtime from dependency."""
        from fastapi.testclient import TestClient

        app, mock_runtime = app_with_runtime
        client = TestClient(app, raise_server_exceptions=False)

        _response = client.get("/state/test-user")

        # Verify runtime.get_state was called
        mock_runtime.get_state.assert_called_once_with("test-user")

    def test_health_returns_starting_when_no_runtime(self):
        """Health should show starting when runtime not initialized."""
        from fastapi.testclient import TestClient

        from soni.server.api import create_app

        app = create_app()
        # Explicitly clear any runtime from previous tests
        if hasattr(app.state, "runtime"):
            app.state.runtime = None
        if hasattr(app.state, "config"):
            app.state.config = None

        client = TestClient(app, raise_server_exceptions=False)

        response = client.get("/health")

        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "starting"
        assert data["initialized"] is False

    def test_health_returns_healthy_when_runtime_initialized(self, app_with_runtime):
        """Health should show healthy when runtime is initialized."""
        from fastapi.testclient import TestClient

        app, _ = app_with_runtime
        client = TestClient(app, raise_server_exceptions=False)

        response = client.get("/health")

        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "healthy"
        assert data["initialized"] is True
