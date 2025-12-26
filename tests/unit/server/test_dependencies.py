"""Tests for server dependency injection functions."""

from unittest.mock import MagicMock

import pytest
from fastapi import HTTPException
from fastapi.testclient import TestClient

from soni.server.dependencies import get_config, get_runtime


class TestGetRuntime:
    """Tests for get_runtime dependency."""

    def test_raises_503_when_no_runtime(self, test_client: TestClient):
        """Should raise 503 when runtime not initialized."""
        # Create a mock request with no runtime in app state
        mock_request = MagicMock()
        mock_request.app.state = MagicMock(spec=[])  # No 'runtime' attribute

        with pytest.raises(HTTPException) as exc_info:
            get_runtime(mock_request)

        assert exc_info.value.status_code == 503
        assert "temporarily unavailable" in exc_info.value.detail["error"]

    def test_returns_runtime_when_available(self, test_client: TestClient):
        """Should return runtime when available."""
        mock_request = MagicMock()
        mock_runtime = MagicMock()
        mock_request.app.state.runtime = mock_runtime

        result = get_runtime(mock_request)
        assert result is mock_runtime


class TestGetConfig:
    """Tests for get_config dependency."""

    def test_raises_503_when_no_config(self):
        """Should raise 503 when config not loaded."""
        mock_request = MagicMock()
        mock_request.app.state = MagicMock(spec=[])  # No 'config' attribute

        with pytest.raises(HTTPException) as exc_info:
            get_config(mock_request)

        assert exc_info.value.status_code == 503
        assert "not configured" in exc_info.value.detail["error"]

    def test_returns_config_when_available(self):
        """Should return config when available."""
        mock_request = MagicMock()
        mock_config = MagicMock()
        mock_request.app.state.config = mock_config

        result = get_config(mock_request)
        assert result is mock_config
