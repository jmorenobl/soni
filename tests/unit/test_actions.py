"""Tests for ActionHandler"""

from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from soni.actions.base import ActionHandler
from soni.core.config import SoniConfig
from soni.core.errors import ActionNotFoundError


@pytest.mark.asyncio
async def test_execute_sync_handler():
    """Test executing a synchronous handler"""
    # Arrange
    config = SoniConfig.from_yaml("examples/flight_booking/soni.yaml")
    handler = ActionHandler(config)

    # Mock handler function
    def mock_search(origin: str, destination: str, departure_date: str) -> dict:
        return {"flights": [f"{origin}-{destination}"], "price": 299.99}

    with patch("importlib.import_module") as mock_import:
        mock_module = MagicMock()
        mock_module.search_available_flights = mock_search
        mock_import.return_value = mock_module

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
    config = SoniConfig.from_yaml("examples/flight_booking/soni.yaml")
    handler = ActionHandler(config)

    # Mock async handler
    async def mock_async_search(origin: str, destination: str, departure_date: str) -> dict:
        return {"flights": [f"{origin}-{destination}"], "price": 299.99}

    with patch("importlib.import_module") as mock_import:
        mock_module = MagicMock()
        mock_module.search_available_flights = mock_async_search
        mock_import.return_value = mock_module

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
    config = SoniConfig.from_yaml("examples/flight_booking/soni.yaml")
    handler = ActionHandler(config)

    # Mock handler import to avoid actual import error
    with patch("importlib.import_module") as mock_import:
        mock_module = MagicMock()
        mock_module.search_available_flights = lambda origin, destination, departure_date: {}
        mock_import.return_value = mock_module

        # Act & Assert
        with pytest.raises(ValueError, match="Required input slot 'origin' not provided"):
            await handler.execute("search_available_flights", {"destination": "Paris"})


@pytest.mark.asyncio
async def test_load_handler_caching():
    """Test that handlers are cached after first load"""
    # Arrange
    config = SoniConfig.from_yaml("examples/flight_booking/soni.yaml")
    handler = ActionHandler(config)

    def mock_search(origin: str, destination: str, departure_date: str) -> dict:
        return {"flights": [], "price": 0.0}

    with patch("importlib.import_module") as mock_import:
        mock_module = MagicMock()
        mock_module.search_available_flights = mock_search
        mock_import.return_value = mock_module

        # Act - execute twice
        await handler.execute(
            "search_available_flights",
            {"origin": "NYC", "destination": "Paris", "departure_date": "2025-12-01"},
        )
        await handler.execute(
            "search_available_flights",
            {"origin": "NYC", "destination": "Paris", "departure_date": "2025-12-01"},
        )

        # Assert - import should be called only once
        assert mock_import.call_count == 1


@pytest.mark.asyncio
async def test_execute_handler_exception():
    """Test that handler execution exceptions are caught and re-raised as RuntimeError"""
    # Arrange
    config = SoniConfig.from_yaml("examples/flight_booking/soni.yaml")
    handler = ActionHandler(config)

    # Mock handler that raises exception
    def mock_search_failing(origin: str, destination: str, departure_date: str) -> dict:
        raise ValueError("Handler execution failed")

    with patch("importlib.import_module") as mock_import:
        mock_module = MagicMock()
        mock_module.search_available_flights = mock_search_failing
        mock_import.return_value = mock_module

        # Act & Assert
        with pytest.raises(
            RuntimeError, match="Action 'search_available_flights' execution failed"
        ):
            await handler.execute(
                "search_available_flights",
                {"origin": "NYC", "destination": "Paris", "departure_date": "2025-12-01"},
            )


@pytest.mark.asyncio
async def test_execute_handler_non_dict_result():
    """Test that non-dict results are converted to dict"""
    # Arrange
    config = SoniConfig.from_yaml("examples/flight_booking/soni.yaml")
    handler = ActionHandler(config)

    # Mock handler that returns non-dict
    def mock_search_string(origin: str, destination: str, departure_date: str) -> str:
        return "string result"

    with patch("importlib.import_module") as mock_import:
        mock_module = MagicMock()
        mock_module.search_available_flights = mock_search_string
        mock_import.return_value = mock_module

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
    config = SoniConfig.from_yaml("examples/flight_booking/soni.yaml")
    handler = ActionHandler(config)

    # Create a simple object with __dict__
    class ResultObject:
        def __init__(self):
            self.flights = ["FL123"]
            self.price = 299.99

    def mock_search_object(origin: str, destination: str, departure_date: str) -> ResultObject:
        return ResultObject()

    with patch("importlib.import_module") as mock_import:
        mock_module = MagicMock()
        mock_module.search_available_flights = mock_search_object
        mock_import.return_value = mock_module

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
    config = SoniConfig.from_yaml("examples/flight_booking/soni.yaml")
    handler = ActionHandler(config)

    # Mock handler that returns incomplete outputs
    def mock_search_incomplete(origin: str, destination: str, departure_date: str) -> dict:
        return {"flights": ["FL123"]}  # Missing "price"

    with patch("importlib.import_module") as mock_import:
        mock_module = MagicMock()
        mock_module.search_available_flights = mock_search_incomplete
        mock_import.return_value = mock_module

        # Act
        result = await handler.execute(
            "search_available_flights",
            {"origin": "NYC", "destination": "Paris", "departure_date": "2025-12-01"},
        )

        # Assert - should still return result even with missing outputs
        assert isinstance(result, dict)
        assert "flights" in result


@pytest.mark.asyncio
async def test_load_handler_invalid_path():
    """Test loading handler with invalid path format"""
    # Arrange
    config = SoniConfig.from_yaml("examples/flight_booking/soni.yaml")
    handler = ActionHandler(config)

    # Create a config with invalid handler path
    from soni.core.config import ActionConfig

    invalid_action = ActionConfig(
        handler="invalid",  # Too short, needs module.function format
        inputs=[],
        outputs=[],
    )
    config.actions["test_action"] = invalid_action

    # Act & Assert
    with pytest.raises(ActionNotFoundError, match="Invalid handler path"):
        await handler.execute("test_action", {})


@pytest.mark.asyncio
async def test_load_handler_missing_attribute():
    """Test loading handler when module doesn't have the attribute"""
    # Arrange
    config = SoniConfig.from_yaml("examples/flight_booking/soni.yaml")
    handler = ActionHandler(config)

    # Create a config with handler path pointing to non-existent attribute
    from soni.core.config import ActionConfig

    invalid_action = ActionConfig(
        handler="examples.flight_booking.handlers.nonexistent_function",
        inputs=[],
        outputs=[],
    )
    config.actions["test_action"] = invalid_action

    # Act & Assert
    with pytest.raises(ActionNotFoundError):
        await handler.execute("test_action", {})


@pytest.mark.asyncio
async def test_load_handler_non_callable():
    """Test loading handler when attribute is not callable"""
    # Arrange
    config = SoniConfig.from_yaml("examples/flight_booking/soni.yaml")
    handler = ActionHandler(config)

    # Create a config with handler path pointing to non-callable attribute
    from soni.core.config import ActionConfig

    invalid_action = ActionConfig(
        handler="examples.flight_booking.handlers.logger",  # logger is not callable
        inputs=[],
        outputs=[],
    )
    config.actions["test_action"] = invalid_action

    # Act & Assert
    with pytest.raises(ActionNotFoundError, match="is not callable"):
        await handler.execute("test_action", {})


@pytest.mark.asyncio
async def test_load_handler_import_error():
    """Test loading handler when module import fails"""
    # Arrange
    config = SoniConfig.from_yaml("examples/flight_booking/soni.yaml")
    handler = ActionHandler(config)

    # Create a config with non-existent module
    from soni.core.config import ActionConfig

    invalid_action = ActionConfig(
        handler="nonexistent.module.function",
        inputs=[],
        outputs=[],
    )
    config.actions["test_action"] = invalid_action

    # Act & Assert
    with pytest.raises(ActionNotFoundError):
        await handler.execute("test_action", {})
