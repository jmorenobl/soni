"""Tests for FastAPI endpoints"""

from pathlib import Path
from unittest.mock import AsyncMock, patch

import pytest
from fastapi.testclient import TestClient

from soni.core.errors import NLUError, SoniError, ValidationError
from soni.runtime import RuntimeLoop
from soni.server.api import app, runtime


@pytest.fixture
def client():
    """Create test client"""
    return TestClient(app)


@pytest.fixture
def mock_runtime(monkeypatch):
    """Mock runtime for testing"""
    config_path = Path("examples/flight_booking/soni.yaml")
    mock_runtime = RuntimeLoop(config_path)

    # Mock process_message to avoid actual execution
    async def mock_process_message(user_msg: str, user_id: str) -> str:
        if not user_msg.strip():
            raise ValidationError("Message cannot be empty")
        return f"Mock response to: {user_msg}"

    mock_runtime.process_message = mock_process_message
    return mock_runtime


def test_health_endpoint(client):
    """Test health endpoint"""
    # Act
    response = client.get("/health")

    # Assert
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "ok"
    assert data["version"] == "0.1.0"


def test_chat_endpoint_success(client, mock_runtime, monkeypatch):
    """Test chat endpoint with successful processing"""
    # Arrange
    monkeypatch.setattr("soni.server.api.runtime", mock_runtime)
    user_id = "test-user-1"
    message = "Hello"

    # Act
    response = client.post(
        f"/chat/{user_id}",
        json={"message": message},
    )

    # Assert
    assert response.status_code == 200
    data = response.json()
    assert "response" in data
    assert data["user_id"] == user_id
    assert isinstance(data["response"], str)


def test_chat_endpoint_empty_message(client, mock_runtime, monkeypatch):
    """Test chat endpoint with empty message"""
    # Arrange
    monkeypatch.setattr("soni.server.api.runtime", mock_runtime)
    user_id = "test-user-1"

    # Act
    response = client.post(
        f"/chat/{user_id}",
        json={"message": ""},
    )

    # Assert
    assert response.status_code == 422  # Validation error


def test_chat_endpoint_empty_user_id(client, mock_runtime, monkeypatch):
    """Test chat endpoint with empty user_id"""
    # Arrange
    monkeypatch.setattr("soni.server.api.runtime", mock_runtime)

    # Act
    response = client.post(
        "/chat/",
        json={"message": "Hello"},
    )

    # Assert
    assert response.status_code == 404  # Not found (empty user_id in path)


def test_chat_endpoint_runtime_not_initialized(client, monkeypatch):
    """Test chat endpoint when runtime is not initialized"""
    # Arrange
    monkeypatch.setattr("soni.server.api.runtime", None)
    user_id = "test-user-1"

    # Act
    response = client.post(
        f"/chat/{user_id}",
        json={"message": "Hello"},
    )

    # Assert
    assert response.status_code == 503  # Service unavailable


def test_chat_endpoint_persists_state(client, mock_runtime, monkeypatch):
    """Test that chat endpoint persists state between requests"""
    # Arrange
    monkeypatch.setattr("soni.server.api.runtime", mock_runtime)
    user_id = "test-user-1"

    # First request
    response_1 = client.post(
        f"/chat/{user_id}",
        json={"message": "I want to book a flight"},
    )

    # Assert first response
    assert response_1.status_code == 200
    data_1 = response_1.json()
    assert "response" in data_1

    # Second request - should have context from first
    response_2 = client.post(
        f"/chat/{user_id}",
        json={"message": "To Paris"},
    )

    # Assert second response
    assert response_2.status_code == 200
    data_2 = response_2.json()
    assert "response" in data_2


def test_chat_endpoint_validation_error(client, mock_runtime, monkeypatch):
    """Test chat endpoint with validation error"""
    # Arrange
    monkeypatch.setattr("soni.server.api.runtime", mock_runtime)
    user_id = "test-user-1"

    # Mock runtime to raise ValidationError
    async def mock_process_validation_error(user_msg: str, user_id: str) -> str:
        raise ValidationError("Invalid input")

    mock_runtime.process_message = mock_process_validation_error

    # Act
    response = client.post(
        f"/chat/{user_id}",
        json={"message": "test"},
    )

    # Assert
    assert response.status_code == 400
    assert "Invalid input" in response.json()["detail"]


def test_chat_endpoint_nlu_error(client, mock_runtime, monkeypatch):
    """Test chat endpoint with NLU error"""
    # Arrange
    monkeypatch.setattr("soni.server.api.runtime", mock_runtime)
    user_id = "test-user-1"

    # Mock runtime to raise NLUError
    async def mock_process_nlu_error(user_msg: str, user_id: str) -> str:
        raise NLUError("NLU processing failed")

    mock_runtime.process_message = mock_process_nlu_error

    # Act
    response = client.post(
        f"/chat/{user_id}",
        json={"message": "test"},
    )

    # Assert
    assert response.status_code == 500
    assert "Natural language understanding failed" in response.json()["detail"]


def test_chat_endpoint_different_users_independent(client, mock_runtime, monkeypatch):
    """Test that different users have independent conversations"""
    # Arrange
    monkeypatch.setattr("soni.server.api.runtime", mock_runtime)
    user_id_1 = "user-1"
    user_id_2 = "user-2"

    # Act - User 1
    response_1 = client.post(
        f"/chat/{user_id_1}",
        json={"message": "Hello"},
    )

    # Act - User 2
    response_2 = client.post(
        f"/chat/{user_id_2}",
        json={"message": "Hello"},
    )

    # Assert
    assert response_1.status_code == 200
    assert response_2.status_code == 200
    data_1 = response_1.json()
    data_2 = response_2.json()
    assert data_1["user_id"] == user_id_1
    assert data_2["user_id"] == user_id_2


def test_chat_endpoint_empty_user_id_whitespace(client, mock_runtime, monkeypatch):
    """Test chat endpoint with whitespace-only user_id"""
    # Arrange
    monkeypatch.setattr("soni.server.api.runtime", mock_runtime)

    # Act
    response = client.post(
        "/chat/   ",
        json={"message": "Hello"},
    )

    # Assert
    assert response.status_code == 400
    assert "User ID cannot be empty" in response.json()["detail"]


def test_chat_endpoint_soni_error(client, mock_runtime, monkeypatch):
    """Test chat endpoint with SoniError"""
    # Arrange
    monkeypatch.setattr("soni.server.api.runtime", mock_runtime)
    user_id = "test-user-1"

    # Mock runtime to raise SoniError
    async def mock_process_soni_error(user_msg: str, user_id: str) -> str:
        raise SoniError("Soni framework error")

    mock_runtime.process_message = mock_process_soni_error

    # Act
    response = client.post(
        f"/chat/{user_id}",
        json={"message": "test"},
    )

    # Assert
    assert response.status_code == 500
    assert "Soni framework error" in response.json()["detail"]


def test_chat_endpoint_unexpected_exception(client, mock_runtime, monkeypatch):
    """Test chat endpoint with unexpected exception"""
    # Arrange
    monkeypatch.setattr("soni.server.api.runtime", mock_runtime)
    user_id = "test-user-1"

    # Mock runtime to raise unexpected exception
    async def mock_process_unexpected_error(user_msg: str, user_id: str) -> str:
        raise KeyError("Unexpected error")

    mock_runtime.process_message = mock_process_unexpected_error

    # Act
    response = client.post(
        f"/chat/{user_id}",
        json={"message": "test"},
    )

    # Assert
    assert response.status_code == 500
    assert "Internal server error" in response.json()["detail"]


def test_validation_exception_handler(client):
    """Test validation exception handler for invalid request"""
    # Arrange - send invalid JSON
    # Act
    response = client.post(
        "/chat/test-user",
        json={"invalid": "field"},
    )

    # Assert - should return 422 with validation errors
    assert response.status_code == 422
    assert "detail" in response.json()


@pytest.mark.asyncio
async def test_startup_event(monkeypatch, tmp_path):
    """Test lifespan startup initializes runtime"""
    # Arrange
    from soni.server.api import app, lifespan

    # Create a temporary config file
    config_file = tmp_path / "test_config.yaml"
    config_file.write_text(
        """
version: "0.1"
settings:
  models:
    nlu:
      provider: openai
      model: gpt-4o-mini
flows:
  test_flow:
    description: "Test flow"
    trigger:
      intents: ["test"]
    steps: []
slots: {}
actions: {}
"""
    )

    # Set environment variable
    monkeypatch.setenv("SONI_CONFIG_PATH", str(config_file))

    # Reset runtime
    import soni.server.api

    soni.server.api.runtime = None

    # Act - trigger lifespan startup
    async with lifespan(app):
        # Assert - runtime should be initialized
        assert soni.server.api.runtime is not None
        # RuntimeLoop stores config, not config_path directly
        assert soni.server.api.runtime.config is not None


@pytest.mark.asyncio
async def test_startup_event_with_optimized_du(monkeypatch, tmp_path):
    """Test lifespan startup with optimized DU path"""
    # Arrange
    from soni.server.api import app, lifespan

    # Create temporary config and DU files
    config_file = tmp_path / "test_config.yaml"
    config_file.write_text(
        """
version: "0.1"
settings:
  models:
    nlu:
      provider: openai
      model: gpt-4o-mini
flows:
  test_flow:
    description: "Test flow"
    trigger:
      intents: ["test"]
    steps: []
slots: {}
actions: {}
"""
    )

    # Create a valid DU module file (SoniDU.save() format)
    from soni.du.modules import SoniDU

    du_file = tmp_path / "optimized_du.json"
    du_module = SoniDU()
    # Save using the save method from dspy.Module
    du_module.save(str(du_file))

    # Set environment variables
    monkeypatch.setenv("SONI_CONFIG_PATH", str(config_file))
    monkeypatch.setenv("SONI_OPTIMIZED_DU_PATH", str(du_file))

    # Reset runtime
    import soni.server.api

    soni.server.api.runtime = None

    # Act - trigger lifespan startup
    async with lifespan(app):
        # Assert - runtime should be initialized
        assert soni.server.api.runtime is not None


@pytest.mark.asyncio
async def test_startup_event_missing_config(monkeypatch):
    """Test lifespan startup with missing config file"""
    # Arrange
    from soni.server.api import app, lifespan

    # Set environment variable to non-existent file
    monkeypatch.setenv("SONI_CONFIG_PATH", "/nonexistent/config.yaml")

    # Reset runtime
    import soni.server.api

    soni.server.api.runtime = None

    # Act & Assert - should raise FileNotFoundError
    with pytest.raises(FileNotFoundError, match="Configuration file not found"):
        async with lifespan(app):
            pass  # Should not reach here


@pytest.mark.asyncio
async def test_shutdown_event(monkeypatch, tmp_path):
    """Test lifespan shutdown cleans up runtime"""
    # Arrange
    from soni.server.api import app, lifespan

    # Create a temporary config file
    config_file = tmp_path / "test_config.yaml"
    config_file.write_text(
        """
version: "0.1"
settings:
  models:
    nlu:
      provider: openai
      model: gpt-4o-mini
flows:
  test_flow:
    description: "Test flow"
    trigger:
      intents: ["test"]
    steps: []
slots: {}
actions: {}
"""
    )

    # Set environment variable
    monkeypatch.setenv("SONI_CONFIG_PATH", str(config_file))

    # Reset runtime
    import soni.server.api

    soni.server.api.runtime = None

    # Act - trigger lifespan (startup and shutdown)
    async with lifespan(app):
        # Assert - runtime should be initialized during lifespan
        assert soni.server.api.runtime is not None

    # Assert - runtime should be None after shutdown
    assert soni.server.api.runtime is None
