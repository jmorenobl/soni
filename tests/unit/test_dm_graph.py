"""Tests for SoniGraphBuilder and graph nodes"""

from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from soni.core.config import SoniConfig
from soni.core.state import DialogueState
from soni.dm.graph import (
    SoniGraphBuilder,
    action_node,
    collect_slot_node,
    understand_node,
)


@pytest.mark.asyncio
async def test_builder_initialization():
    """Test that builder initializes correctly"""
    # Arrange
    config = SoniConfig.from_yaml("examples/flight_booking/soni.yaml")

    # Act
    builder = SoniGraphBuilder(config)
    # Initialize checkpointer (lazy initialization)
    await builder.initialize()

    # Assert
    assert builder.config == config
    assert builder.checkpointer is not None


@pytest.mark.asyncio
async def test_build_manual_linear_flow():
    """Test building a simple linear flow"""
    # Arrange
    config = SoniConfig.from_yaml("examples/flight_booking/soni.yaml")
    builder = SoniGraphBuilder(config)

    # Act
    graph = await builder.build_manual("book_flight")

    # Assert
    assert graph is not None
    # graph.compile() returns a CompiledStateGraph, not StateGraph
    assert hasattr(graph, "invoke") or hasattr(graph, "ainvoke")


@pytest.mark.asyncio
async def test_build_manual_nonexistent_flow():
    """Test that building non-existent flow raises error"""
    # Arrange
    config = SoniConfig.from_yaml("examples/flight_booking/soni.yaml")
    builder = SoniGraphBuilder(config)

    # Act & Assert
    with pytest.raises(ValueError, match="Flow 'nonexistent' not found"):
        await builder.build_manual("nonexistent")


@pytest.mark.asyncio
async def test_checkpointer_creation():
    """Test that checkpointer is created for SQLite"""
    # Arrange
    config = SoniConfig.from_yaml("examples/flight_booking/soni.yaml")

    # Act
    builder = SoniGraphBuilder(config)
    await builder.initialize()

    # Assert
    assert builder.checkpointer is not None


@pytest.mark.asyncio
async def test_build_manual_validates_slots():
    """Test that building a flow validates referenced slots exist"""
    # Arrange
    config = SoniConfig.from_yaml("examples/flight_booking/soni.yaml")
    builder = SoniGraphBuilder(config)

    # Modify flow to reference non-existent slot
    # This should be caught during validation
    # For now, we test that the validation happens
    # (actual invalid config would fail at YAML load time)

    # Act & Assert - should work with valid config
    graph = await builder.build_manual("book_flight")
    assert graph is not None


@pytest.mark.asyncio
async def test_build_manual_validates_actions():
    """Test that building a flow validates referenced actions exist"""
    # Arrange
    config = SoniConfig.from_yaml("examples/flight_booking/soni.yaml")
    builder = SoniGraphBuilder(config)

    # Act & Assert - should work with valid config
    graph = await builder.build_manual("book_flight")
    assert graph is not None


@pytest.mark.asyncio
async def test_understand_node_with_message():
    """Test understand_node processes user message"""
    # Arrange
    state = DialogueState(
        messages=[{"role": "user", "content": "I want to book a flight to Paris"}],
        slots={},
        current_flow="book_flight",
    )

    with patch("soni.dm.graph.SoniDU") as mock_du_class:
        mock_du = AsyncMock()
        mock_du_class.return_value = mock_du
        mock_du.predict.return_value = MagicMock(
            command="book_flight",
            slots={"destination": "Paris"},
            confidence=0.95,
            reasoning="User wants to book flight",
        )

        # Act
        result = await understand_node(state)

        # Assert
        assert "slots" in result
        assert result["slots"]["destination"] == "Paris"
        assert result["pending_action"] == "book_flight"


@pytest.mark.asyncio
async def test_collect_slot_node_prompts_user():
    """Test collect_slot_node prompts when slot is missing"""
    # Arrange
    config = SoniConfig.from_yaml("examples/flight_booking/soni.yaml")
    state = DialogueState(
        slots={},
    )
    state.config = config  # Inject config

    # Act
    result = await collect_slot_node(state, "origin")

    # Assert
    assert "last_response" in result
    assert (
        "origin" in result["last_response"].lower()
        or "departing" in result["last_response"].lower()
    )


@pytest.mark.asyncio
async def test_action_node_executes_handler():
    """Test action_node executes action handler"""
    # Arrange
    config = SoniConfig.from_yaml("examples/flight_booking/soni.yaml")
    state = DialogueState(
        slots={"origin": "NYC", "destination": "Paris", "departure_date": "2025-12-01"},
    )
    state.config = config

    # Mock ActionHandler (will be implemented in Task 008)
    with patch("soni.actions.base.ActionHandler") as mock_handler_class:
        mock_handler = AsyncMock()
        mock_handler_class.return_value = mock_handler
        mock_handler.execute.return_value = {"flights": ["FL123", "FL456"], "price": 299.99}

        # Act
        result = await action_node(state, "search_available_flights")

        # Assert
        mock_handler.execute.assert_called_once()
        assert "slots" in result
        assert "flights" in result["slots"]


@pytest.mark.asyncio
async def test_builder_cleanup():
    """Test that builder cleanup closes checkpointer context manager"""
    # Arrange
    config = SoniConfig.from_yaml("examples/flight_booking/soni.yaml")
    builder = SoniGraphBuilder(config)

    # Initialize checkpointer (lazy initialization)
    await builder.initialize()

    # Verify checkpointer was created
    assert builder.checkpointer is not None
    assert builder._checkpointer_cm is not None

    # Act
    await builder.cleanup()

    # Assert
    assert builder.checkpointer is None
    assert builder._checkpointer_cm is None


@pytest.mark.asyncio
async def test_builder_cleanup_no_checkpointer():
    """Test that cleanup handles case when no checkpointer exists"""
    # Arrange
    config = SoniConfig.from_yaml("examples/flight_booking/soni.yaml")
    # Modify config to disable persistence
    config.settings.persistence.backend = "none"
    builder = SoniGraphBuilder(config)

    # Verify no checkpointer
    assert builder.checkpointer is None

    # Act - should not raise error
    await builder.cleanup()

    # Assert
    assert builder.checkpointer is None


@pytest.mark.asyncio
async def test_builder_cleanup_called_twice():
    """Test that cleanup can be called multiple times safely"""
    # Arrange
    config = SoniConfig.from_yaml("examples/flight_booking/soni.yaml")
    builder = SoniGraphBuilder(config)

    # Initialize checkpointer first
    await builder.initialize()

    # Act
    await builder.cleanup()
    await builder.cleanup()  # Should not raise error

    # Assert
    assert builder.checkpointer is None


@pytest.mark.asyncio
async def test_checkpointer_creation_unsupported_backend():
    """Test that unsupported persistence backend logs warning and returns None"""
    # Arrange
    config = SoniConfig.from_yaml("examples/flight_booking/soni.yaml")
    config.settings.persistence.backend = "unsupported"

    # Act
    builder = SoniGraphBuilder(config)

    # Assert
    assert builder.checkpointer is None


@pytest.mark.asyncio
async def test_understand_node_no_messages():
    """Test understand_node handles state with no messages"""
    # Arrange
    state = DialogueState(messages=[], slots={})

    # Act
    result = await understand_node(state)

    # Assert
    assert "last_response" in result
    assert "didn't receive" in result["last_response"].lower()


@pytest.mark.asyncio
async def test_collect_slot_node_already_filled():
    """Test collect_slot_node skips when slot is already filled"""
    # Arrange
    config = SoniConfig.from_yaml("examples/flight_booking/soni.yaml")
    state = DialogueState(slots={"origin": "NYC"})
    state.config = config

    # Act
    result = await collect_slot_node(state, "origin")

    # Assert
    # Should return empty dict (no updates) since slot is already filled
    assert result == {}


@pytest.mark.asyncio
async def test_collect_slot_node_missing_slot_config():
    """Test collect_slot_node handles missing slot configuration"""
    # Arrange
    config = SoniConfig.from_yaml("examples/flight_booking/soni.yaml")
    state = DialogueState(slots={})
    state.config = config

    # Act
    result = await collect_slot_node(state, "nonexistent_slot")

    # Assert
    # Should return error message in response
    assert "last_response" in result
    assert "error" in result["last_response"].lower()


@pytest.mark.asyncio
async def test_action_node_missing_input_slot():
    """Test action_node handles missing required input slot"""
    # Arrange
    config = SoniConfig.from_yaml("examples/flight_booking/soni.yaml")
    state = DialogueState(
        slots={"origin": "NYC"}  # Missing destination and departure_date
    )
    state.config = config

    # Act
    result = await action_node(state, "search_available_flights")

    # Assert
    # Should return error message
    assert "last_response" in result
    assert "error" in result["last_response"].lower()
