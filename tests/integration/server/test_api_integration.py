"""Integration tests for API flows."""

from unittest.mock import AsyncMock, patch

import pytest
from fastapi.testclient import TestClient


class TestChatFlowIntegration:
    """Integration tests for complete chat flow."""

    def test_complete_chat_session(self, test_client: TestClient, mock_runtime):
        """Test complete chat session from start to finish."""
        with patch("soni.server.dependencies.get_runtime", return_value=mock_runtime):
            mock_runtime.process_message = AsyncMock(return_value="Hello!")

            # First message
            response1 = test_client.post(
                "/chat", json={"message": "Hello", "user_id": "session-123"}
            )
            assert response1.status_code == 200

            # Second message
            response2 = test_client.post(
                "/chat", json={"message": "How are you?", "user_id": "session-123"}
            )
            assert response2.status_code == 200

    def test_concurrent_sessions(self, test_client: TestClient, mock_runtime):
        """Test handling multiple concurrent sessions."""
        with patch("soni.server.dependencies.get_runtime", return_value=mock_runtime):
            mock_runtime.process_message = AsyncMock(return_value="Hi!")

            sessions = ["session-1", "session-2", "session-3"]

            for session_id in sessions:
                response = test_client.post(
                    "/chat", json={"message": "Hello", "user_id": session_id}
                )
                assert response.status_code == 200


class TestStateEndpoints:
    """Integration tests for state management endpoints."""

    def test_get_state_endpoint(self, test_client: TestClient, mock_runtime):
        """Test GET /state/{user_id} endpoint."""
        with patch("soni.server.dependencies.get_runtime", return_value=mock_runtime):
            response = test_client.get("/state/test-user")
            assert response.status_code == 200
            data = response.json()
            assert "user_id" in data
            assert data["user_id"] == "test-user"

    def test_reset_state_endpoint(self, test_client: TestClient, mock_runtime):
        """Test DELETE /state/{user_id} endpoint."""
        with patch("soni.server.dependencies.get_runtime", return_value=mock_runtime):
            response = test_client.delete("/state/test-user")
            assert response.status_code == 200
            data = response.json()
            assert "success" in data
            assert "message" in data
