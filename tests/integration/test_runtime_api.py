"""Integration tests for RuntimeLoop and FastAPI"""

from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from soni.runtime import RuntimeLoop
from soni.server.api import app


@pytest.fixture
async def test_runtime():
    """Create test runtime instance with automatic cleanup"""
    config_path = Path("examples/flight_booking/soni.yaml")
    runtime_instance = RuntimeLoop(config_path)
    yield runtime_instance
    # Cleanup connections after test
    await runtime_instance.cleanup()


@pytest.fixture
def client_with_runtime(test_runtime, monkeypatch):
    """Create test client with real runtime"""
    monkeypatch.setattr("soni.server.api.runtime", test_runtime)
    return TestClient(app)


@pytest.mark.integration
@pytest.mark.asyncio
@pytest.mark.skip(
    reason="Requires AsyncSqliteSaver for full async support. "
    "SqliteSaver doesn't support async methods. "
    "This will be fixed in Hito 10."
)
async def test_end_to_end_conversation(client_with_runtime):
    """Test complete conversation flow through API"""
    # Arrange
    user_id = "integration-test-user"

    # Act - Start conversation
    response_1 = client_with_runtime.post(
        f"/chat/{user_id}",
        json={"message": "I want to book a flight"},
    )

    # Assert
    assert response_1.status_code == 200
    data_1 = response_1.json()
    assert "response" in data_1
    assert len(data_1["response"]) > 0

    # Act - Continue conversation
    response_2 = client_with_runtime.post(
        f"/chat/{user_id}",
        json={"message": "From New York to Paris"},
    )

    # Assert
    assert response_2.status_code == 200
    data_2 = response_2.json()
    assert "response" in data_2


@pytest.mark.integration
def test_health_endpoint_always_works(client_with_runtime):
    """Test that health endpoint works even if runtime fails"""
    # Arrange
    # Health endpoint should work independently

    # Act
    response = client_with_runtime.get("/health")

    # Assert
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "ok"
    assert "version" in data
