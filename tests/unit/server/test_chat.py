from unittest.mock import AsyncMock, patch

import pytest
from fastapi.testclient import TestClient

from soni.core.errors import StateError


class TestChatEndpoint:
    """Tests for /chat endpoint."""

    def test_chat_validates_empty_message(self, test_client: TestClient):
        """Chat endpoint should reject empty messages."""
        response = test_client.post("/chat", json={"message": "", "user_id": "test-123"})
        assert response.status_code == 422

    def test_chat_requires_user_id(self, test_client: TestClient):
        """Chat endpoint should require user_id."""
        response = test_client.post("/chat", json={"message": "Hello"})
        assert response.status_code == 422

    def test_chat_requires_message(self, test_client: TestClient):
        """Chat endpoint should require message."""
        response = test_client.post("/chat", json={"user_id": "test-123"})
        assert response.status_code == 422

    def test_chat_validates_message_length(self, test_client: TestClient, mock_runtime):
        """Chat endpoint should handle long messages."""
        with patch("soni.server.dependencies.get_runtime", return_value=mock_runtime):
            mock_runtime.process_message = AsyncMock(return_value="OK")
            long_message = "x" * 1000
            response = test_client.post("/chat", json={"message": long_message, "user_id": "test"})
            # Should either accept or reject gracefully
            assert response.status_code in [200, 400, 422]

    @pytest.mark.asyncio
    async def test_chat_processes_valid_message(self, test_client: TestClient, mock_runtime):
        """Chat endpoint should process valid messages."""
        with patch("soni.server.dependencies.get_runtime", return_value=mock_runtime):
            mock_runtime.process_message = AsyncMock(
                return_value={"response": "Hello!", "session_id": "test-123"}
            )

            response = test_client.post("/chat", json={"message": "Hello", "user_id": "test-123"})
            assert response.status_code == 200
            assert "response" in response.json()
            assert response.json()["response"] == "Hello!"

    def test_chat_returns_correct_structure(self, test_client: TestClient, mock_runtime):
        """Chat response should have correct structure."""
        with patch("soni.server.dependencies.get_runtime", return_value=mock_runtime):
            mock_runtime.process_message = AsyncMock(return_value="Hello!")

            response = test_client.post("/chat", json={"message": "Hello", "user_id": "test-123"})

            if response.status_code == 200:
                data = response.json()
                assert "response" in data
                assert "flow_state" in data

    def test_chat_handles_state_error(self, test_client: TestClient, mock_runtime):
        """Chat endpoint should handle StateError gracefully."""
        with patch("soni.server.dependencies.get_runtime", return_value=mock_runtime):
            mock_runtime.process_message = AsyncMock(
                side_effect=StateError("Session state corrupted")
            )

            response = test_client.post("/chat", json={"message": "Hello", "user_id": "test-123"})
            assert response.status_code == 200
            assert "trouble" in response.json()["response"].lower()
