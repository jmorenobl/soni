from unittest.mock import patch

import pytest
from fastapi.testclient import TestClient


class TestChatEndpoint:
    """Tests for /chat endpoint."""

    def test_chat_validates_empty_message(self, test_client: TestClient):
        """Chat endpoint should reject empty messages."""
        response = test_client.post("/chat", json={"message": "", "user_id": "test-123"})
        assert response.status_code == 422

    @pytest.mark.asyncio
    async def test_chat_processes_valid_message(self, test_client: TestClient, mock_runtime):
        """Chat endpoint should process valid messages."""
        # Patch the dependency from the correct module
        with patch("soni.server.dependencies.get_runtime", return_value=mock_runtime):
            mock_runtime.process_message.return_value = {
                "response": "Hello!",
                "session_id": "test-123",
            }

            response = test_client.post("/chat", json={"message": "Hello", "user_id": "test-123"})
            assert response.status_code == 200
            assert "response" in response.json()
            assert response.json()["response"] == "Hello!"
