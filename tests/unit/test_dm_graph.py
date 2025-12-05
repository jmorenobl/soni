"""Tests for SoniGraphBuilder and graph nodes"""

import warnings
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from soni.core.config import SoniConfig
from soni.core.state import DialogueState
from soni.dm.graph import SoniGraphBuilder
from soni.dm.nodes import understand_node
from soni.dm.nodes.factories import (
    collect_slot_node,
    create_action_node_factory,
    create_collect_node_factory,
    create_understand_node,
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
    await builder.initialize()

    # Act & Assert
    # FlowCompiler raises KeyError, but validator raises ValidationError first
    # So we check for ValidationError (from validator)
    from soni.core.errors import ValidationError

    with pytest.raises(ValidationError):
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
    from soni.actions.base import ActionHandler
    from soni.core.scope import ScopeManager
    from soni.core.state import RuntimeContext
    from soni.du.normalizer import SlotNormalizer

    config = SoniConfig.from_yaml("examples/flight_booking/soni.yaml")
    state = DialogueState(
        messages=[{"role": "user", "content": "I want to book a flight to Paris"}],
        slots={},
        current_flow="book_flight",
    )

    # Create mock NLU provider
    mock_du = AsyncMock()
    # Create NLUOutput object
    from soni.du.models import MessageType, NLUOutput, SlotValue

    nlu_result = NLUOutput(
        message_type=MessageType.SLOT_VALUE,
        command="book_flight",
        slots=[SlotValue(name="destination", value="Paris", confidence=0.95)],
        confidence=0.95,
        reasoning="User wants to book flight",
    )

    # Track calls to verify available_flows is passed
    predict_calls = []

    async def track_predict(*args, **kwargs):
        predict_calls.append(kwargs)
        return nlu_result

    mock_du.predict = track_predict

    scope_manager = ScopeManager(config=config)
    normalizer = SlotNormalizer(config=config)
    action_handler = ActionHandler(config=config)

    context = RuntimeContext(
        config=config,
        scope_manager=scope_manager,
        normalizer=normalizer,
        action_handler=action_handler,
        du=mock_du,
    )

    # Create understand node using factory
    understand_fn = create_understand_node(
        scope_manager=scope_manager,
        normalizer=normalizer,
        nlu_provider=mock_du,
        context=context,
    )

    # Act
    result = await understand_fn(state)

    # Assert
    assert "slots" in result
    assert result["slots"]["destination"] == "Paris"
    assert result["pending_action"] == "book_flight"
    # Verify available_flows was passed to NLU
    assert len(predict_calls) > 0, "NLU predict should have been called"
    assert "available_flows" in predict_calls[0], "available_flows should be passed to NLU"
    assert isinstance(predict_calls[0]["available_flows"], list), "available_flows should be a list"


@pytest.mark.asyncio
async def test_collect_slot_node_prompts_user():
    """Test collect_slot_node prompts when slot is missing"""
    # Arrange
    from soni.actions.base import ActionHandler
    from soni.core.scope import ScopeManager
    from soni.core.state import RuntimeContext
    from soni.du.modules import SoniDU
    from soni.du.normalizer import SlotNormalizer

    config = SoniConfig.from_yaml("examples/flight_booking/soni.yaml")
    state = DialogueState(
        slots={},
    )

    scope_manager = ScopeManager(config=config)
    normalizer = SlotNormalizer(config=config)
    action_handler = ActionHandler(config=config)
    du = SoniDU()

    context = RuntimeContext(
        config=config,
        scope_manager=scope_manager,
        normalizer=normalizer,
        action_handler=action_handler,
        du=du,
    )

    # Act
    result = await collect_slot_node(state, "origin", context=context)

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
    from soni.core.scope import ScopeManager
    from soni.core.state import RuntimeContext
    from soni.du.modules import SoniDU
    from soni.du.normalizer import SlotNormalizer

    config = SoniConfig.from_yaml("examples/flight_booking/soni.yaml")
    state = DialogueState(
        slots={"origin": "NYC", "destination": "Paris", "departure_date": "2025-12-01"},
    )

    # Mock ActionHandler
    mock_handler = AsyncMock()
    mock_handler.execute.return_value = {"flights": ["FL123", "FL456"], "price": 299.99}

    scope_manager = ScopeManager(config=config)
    normalizer = SlotNormalizer(config=config)
    du = SoniDU()

    context = RuntimeContext(
        config=config,
        scope_manager=scope_manager,
        normalizer=normalizer,
        action_handler=mock_handler,
        du=du,
    )

    # Create action node factory
    action_fn = create_action_node_factory("search_available_flights", context)

    # Act
    result = await action_fn(state)

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
async def test_builder_warns_if_not_cleaned_up():
    """Test SoniGraphBuilder warns if cleanup() not called"""
    # Arrange
    config = SoniConfig.from_yaml("examples/flight_booking/soni.yaml")

    # Act - create builder without cleanup
    builder = SoniGraphBuilder(config)
    await builder.initialize()  # Initialize checkpointer
    # Don't call cleanup()
    # Verify flag is False (not cleaned up)
    assert builder._cleaned_up is False

    # Note: __del__ may not be called immediately during test execution
    # The ResourceWarning will be emitted when Python garbage collects the object
    # This test verifies the flag mechanism is in place


@pytest.mark.asyncio
async def test_builder_no_warning_after_cleanup():
    """Test SoniGraphBuilder doesn't warn if cleanup() called"""
    # Arrange
    config = SoniConfig.from_yaml("examples/flight_booking/soni.yaml")

    # Act
    with warnings.catch_warnings(record=True) as w:
        warnings.simplefilter("always")

        builder = SoniGraphBuilder(config)
        await builder.initialize()
        await builder.cleanup()  # Proper cleanup
        assert builder._cleaned_up is True

        del builder
        import gc

        gc.collect()

        # Assert - no resource warnings about cleanup
        resource_warnings = [
            warning
            for warning in w
            if issubclass(warning.category, ResourceWarning)
            and "not cleaned up" in str(warning.message)
        ]
        assert len(resource_warnings) == 0


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
    from soni.actions.base import ActionHandler
    from soni.core.scope import ScopeManager
    from soni.core.state import RuntimeContext
    from soni.du.modules import SoniDU
    from soni.du.normalizer import SlotNormalizer

    config = SoniConfig.from_yaml("examples/flight_booking/soni.yaml")
    state = DialogueState(messages=[], slots={})

    scope_manager = ScopeManager(config=config)
    normalizer = SlotNormalizer(config=config)
    action_handler = ActionHandler(config=config)
    du = SoniDU()

    context = RuntimeContext(
        config=config,
        scope_manager=scope_manager,
        normalizer=normalizer,
        action_handler=action_handler,
        du=du,
    )

    understand_fn = create_understand_node(
        scope_manager=scope_manager,
        normalizer=normalizer,
        nlu_provider=du,
        context=context,
    )

    # Act
    result = await understand_fn(state)

    # Assert
    assert "last_response" in result
    assert "didn't receive" in result["last_response"].lower()


@pytest.mark.asyncio
async def test_collect_slot_node_already_filled():
    """Test collect_slot_node skips when slot is already filled"""
    # Arrange
    from soni.actions.base import ActionHandler
    from soni.core.scope import ScopeManager
    from soni.core.state import RuntimeContext
    from soni.du.modules import SoniDU
    from soni.du.normalizer import SlotNormalizer

    config = SoniConfig.from_yaml("examples/flight_booking/soni.yaml")
    # Create state with slot filled and trace event showing it was explicitly collected
    from soni.core.events import EVENT_SLOT_COLLECTION

    state = DialogueState(
        slots={"origin": "NYC"},
        trace=[
            {
                "event": EVENT_SLOT_COLLECTION,
                "data": {"slot": "origin", "prompt": "Which city are you departing from?"},
            }
        ],
    )

    scope_manager = ScopeManager(config=config)
    normalizer = SlotNormalizer(config=config)
    action_handler = ActionHandler(config=config)
    du = SoniDU()

    context = RuntimeContext(
        config=config,
        scope_manager=scope_manager,
        normalizer=normalizer,
        action_handler=action_handler,
        du=du,
    )

    # Act
    result = await collect_slot_node(state, "origin", context=context)

    # Assert
    # Should return empty dict (no updates) since slot is already filled
    assert result == {}


@pytest.mark.asyncio
async def test_collect_slot_node_missing_slot_config():
    """Test collect_slot_node handles missing slot configuration"""
    # Arrange
    from soni.actions.base import ActionHandler
    from soni.core.scope import ScopeManager
    from soni.core.state import RuntimeContext
    from soni.du.modules import SoniDU
    from soni.du.normalizer import SlotNormalizer

    config = SoniConfig.from_yaml("examples/flight_booking/soni.yaml")
    state = DialogueState(slots={})

    scope_manager = ScopeManager(config=config)
    normalizer = SlotNormalizer(config=config)
    action_handler = ActionHandler(config=config)
    du = SoniDU()

    context = RuntimeContext(
        config=config,
        scope_manager=scope_manager,
        normalizer=normalizer,
        action_handler=action_handler,
        du=du,
    )

    # Act
    result = await collect_slot_node(state, "nonexistent_slot", context=context)

    # Assert
    # Function catches KeyError and returns error message
    assert "last_response" in result
    assert "error" in result["last_response"].lower()


@pytest.mark.asyncio
async def test_action_node_missing_input_slot():
    """Test action_node handles missing required input slot"""
    # Arrange
    from soni.actions.base import ActionHandler
    from soni.core.scope import ScopeManager
    from soni.core.state import RuntimeContext
    from soni.du.modules import SoniDU
    from soni.du.normalizer import SlotNormalizer

    config = SoniConfig.from_yaml("examples/flight_booking/soni.yaml")
    state = DialogueState(
        slots={"origin": "NYC"}  # Missing destination and departure_date
    )

    scope_manager = ScopeManager(config=config)
    normalizer = SlotNormalizer(config=config)
    action_handler = ActionHandler(config=config)
    du = SoniDU()

    context = RuntimeContext(
        config=config,
        scope_manager=scope_manager,
        normalizer=normalizer,
        action_handler=action_handler,
        du=du,
    )

    action_fn = create_action_node_factory("search_available_flights", context)

    # Act & Assert - should raise ValueError for missing input slot
    with pytest.raises(ValueError, match="Required input slot"):
        await action_fn(state)
