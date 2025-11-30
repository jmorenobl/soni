"""Tests for ActionHandler"""

from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from soni.actions.base import ActionHandler
from soni.actions.registry import ActionRegistry
from soni.core.config import SoniConfig
from soni.core.errors import ActionNotFoundError


@pytest.mark.asyncio
async def test_execute_sync_handler():
    """Test executing a synchronous handler"""
    # Arrange
    ActionRegistry.clear()
    config = SoniConfig.from_yaml("examples/flight_booking/soni.yaml")
    handler = ActionHandler(config)

    # Register handler in ActionRegistry
    def mock_search(origin: str, destination: str, departure_date: str) -> dict:
        return {"flights": [f"{origin}-{destination}"], "price": 299.99}

    ActionRegistry.register("search_available_flights")(mock_search)

    # Act
    result = await handler.execute(
        "search_available_flights",
        {"origin": "NYC", "destination": "Paris", "departure_date": "2025-12-01"},
    )

    # Assert
    assert "flights" in result
    assert len(result["flights"]) > 0


@pytest.mark.asyncio
async def test_execute_async_handler():
    """Test executing an asynchronous handler"""
    # Arrange
    ActionRegistry.clear()
    config = SoniConfig.from_yaml("examples/flight_booking/soni.yaml")
    handler = ActionHandler(config)

    # Register async handler in ActionRegistry
    async def mock_async_search(origin: str, destination: str, departure_date: str) -> dict:
        return {"flights": [f"{origin}-{destination}"], "price": 299.99}

    ActionRegistry.register("search_available_flights")(mock_async_search)

    # Act
    result = await handler.execute(
        "search_available_flights",
        {"origin": "NYC", "destination": "Paris", "departure_date": "2025-12-01"},
    )

    # Assert
    assert "flights" in result


@pytest.mark.asyncio
async def test_execute_nonexistent_action():
    """Test that executing non-existent action raises error"""
    # Arrange
    config = SoniConfig.from_yaml("examples/flight_booking/soni.yaml")
    handler = ActionHandler(config)

    # Act & Assert
    with pytest.raises(ActionNotFoundError, match="Action 'nonexistent' not found"):
        await handler.execute("nonexistent", {})


@pytest.mark.asyncio
async def test_execute_missing_input():
    """Test that missing required input raises error"""
    # Arrange
    ActionRegistry.clear()
    config = SoniConfig.from_yaml("examples/flight_booking/soni.yaml")
    handler = ActionHandler(config)

    # Register handler in ActionRegistry
    ActionRegistry.register("search_available_flights")(
        lambda origin, destination, departure_date: {}
    )

    # Act & Assert
    with pytest.raises(ValueError, match="Required input slot 'origin' not provided"):
        await handler.execute("search_available_flights", {"destination": "Paris"})


@pytest.mark.asyncio
async def test_load_handler_caching():
    """Test that handlers are retrieved from registry (no caching needed)"""
    # Arrange
    ActionRegistry.clear()
    config = SoniConfig.from_yaml("examples/flight_booking/soni.yaml")
    handler = ActionHandler(config)

    def mock_search(origin: str, destination: str, departure_date: str) -> dict:
        return {"flights": [], "price": 0.0}

    # Register handler in ActionRegistry
    ActionRegistry.register("search_available_flights")(mock_search)

    # Act - execute twice
    await handler.execute(
        "search_available_flights",
        {"origin": "NYC", "destination": "Paris", "departure_date": "2025-12-01"},
    )
    result = await handler.execute(
        "search_available_flights",
        {"origin": "NYC", "destination": "Paris", "departure_date": "2025-12-01"},
    )

    # Assert - handler should work correctly
    assert "flights" in result


@pytest.mark.asyncio
async def test_execute_handler_exception():
    """Test that handler execution exceptions are caught and re-raised as RuntimeError"""
    # Arrange
    ActionRegistry.clear()
    config = SoniConfig.from_yaml("examples/flight_booking/soni.yaml")
    handler = ActionHandler(config)

    # Register handler that raises exception
    def mock_search_failing(origin: str, destination: str, departure_date: str) -> dict:
        raise ValueError("Handler execution failed")

    ActionRegistry.register("search_available_flights")(mock_search_failing)

    # Act & Assert
    with pytest.raises(RuntimeError, match="Action 'search_available_flights' execution failed"):
        await handler.execute(
            "search_available_flights",
            {"origin": "NYC", "destination": "Paris", "departure_date": "2025-12-01"},
        )


@pytest.mark.asyncio
async def test_execute_handler_non_dict_result():
    """Test that non-dict results are converted to dict"""
    # Arrange
    ActionRegistry.clear()
    config = SoniConfig.from_yaml("examples/flight_booking/soni.yaml")
    handler = ActionHandler(config)

    # Register handler that returns non-dict
    def mock_search_string(origin: str, destination: str, departure_date: str) -> str:
        return "string result"

    ActionRegistry.register("search_available_flights")(mock_search_string)

    # Act
    result = await handler.execute(
        "search_available_flights",
        {"origin": "NYC", "destination": "Paris", "departure_date": "2025-12-01"},
    )

    # Assert - should be converted to dict
    assert isinstance(result, dict)
    assert "result" in result
    assert result["result"] == "string result"


@pytest.mark.asyncio
async def test_execute_handler_object_result():
    """Test that object results with __dict__ are converted to dict"""
    # Arrange
    ActionRegistry.clear()
    config = SoniConfig.from_yaml("examples/flight_booking/soni.yaml")
    handler = ActionHandler(config)

    # Create a simple object with __dict__
    class ResultObject:
        def __init__(self):
            self.flights = ["FL123"]
            self.price = 299.99

    def mock_search_object(origin: str, destination: str, departure_date: str) -> ResultObject:
        return ResultObject()

    ActionRegistry.register("search_available_flights")(mock_search_object)

    # Act
    result = await handler.execute(
        "search_available_flights",
        {"origin": "NYC", "destination": "Paris", "departure_date": "2025-12-01"},
    )

    # Assert - should be converted to dict using __dict__
    assert isinstance(result, dict)
    assert "flights" in result
    assert result["flights"] == ["FL123"]


@pytest.mark.asyncio
async def test_execute_missing_outputs():
    """Test that missing expected outputs log warning but don't fail"""
    # Arrange
    ActionRegistry.clear()
    config = SoniConfig.from_yaml("examples/flight_booking/soni.yaml")
    handler = ActionHandler(config)

    # Register handler that returns incomplete outputs
    def mock_search_incomplete(origin: str, destination: str, departure_date: str) -> dict:
        return {"flights": ["FL123"]}  # Missing "price"

    ActionRegistry.register("search_available_flights")(mock_search_incomplete)

    # Act
    result = await handler.execute(
        "search_available_flights",
        {"origin": "NYC", "destination": "Paris", "departure_date": "2025-12-01"},
    )

    # Assert - should still return result even with missing outputs
    assert isinstance(result, dict)
    assert "flights" in result


@pytest.mark.asyncio
async def test_action_handler_requires_registry_no_fallback():
    """Test that ActionHandler requires ActionRegistry and doesn't fallback to handler path"""
    # Arrange
    ActionRegistry.clear()
    config = SoniConfig.from_yaml("examples/flight_booking/soni.yaml")
    handler = ActionHandler(config)

    # Create a config with handler path (deprecated, should be ignored)
    from soni.core.config import ActionConfig

    action_with_handler = ActionConfig(
        handler="examples.flight_booking.handlers.search_available_flights",
        inputs=["origin", "destination", "departure_date"],
        outputs=["flights", "price"],
    )
    config.actions["test_action"] = action_with_handler

    # Act & Assert - should fail because action is not in registry
    with pytest.raises(ActionNotFoundError) as exc_info:
        await handler.execute(
            "test_action", {"origin": "NYC", "destination": "LAX", "departure_date": "2025-12-01"}
        )

    # Verify error message mentions ActionRegistry
    error_str = str(exc_info.value)
    assert "not found in registry" in error_str or "not found" in error_str
    assert "ActionRegistry.register" in error_str or "register" in error_str
