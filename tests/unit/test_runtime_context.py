"""Tests for RuntimeContext"""

from unittest.mock import MagicMock

import pytest

from soni.core.config import SoniConfig
from soni.core.state import (
    DialogueState,
    RuntimeContext,
    create_empty_state,
    create_initial_state,
    create_runtime_context,
    get_action_config,
    get_all_slots,
    get_current_flow,
    get_flow_config,
    get_slot_config,
    push_flow,
    set_slot,
    state_from_dict,
    state_to_dict,
)


def test_runtime_context_creation():
    """Test RuntimeContext can be created with all dependencies"""
    # Arrange
    config = SoniConfig(
        version="1.0",
        settings={"models": {"nlu": {"provider": "openai", "model": "gpt-4o-mini"}}},
        flows={},
        slots={},
        actions={},
    )
    mock_scope = MagicMock()
    mock_normalizer = MagicMock()
    mock_handler = MagicMock()
    mock_du = MagicMock()

    # Act
    context = create_runtime_context(
        config=config,
        scope_manager=mock_scope,
        normalizer=mock_normalizer,
        action_handler=mock_handler,
        du=mock_du,
    )

    # Assert
    # RuntimeContext is now TypedDict (dict), use dict access
    assert context["config"] is config
    assert context["scope_manager"] is mock_scope
    assert context["normalizer"] is mock_normalizer
    assert context["action_handler"] is mock_handler
    assert context["du"] is mock_du


def test_runtime_context_get_slot_config():
    """Test RuntimeContext can retrieve slot config"""
    # Arrange
    from pathlib import Path

    from tests.conftest import load_test_config

    config_path = Path("examples/flight_booking/soni.yaml")
    config = load_test_config(config_path)
    context = create_runtime_context(
        config=config,
        scope_manager=MagicMock(),
        normalizer=MagicMock(),
        action_handler=MagicMock(),
        du=MagicMock(),
    )

    # Act
    # Use helper function instead of method
    slot_config = get_slot_config(context, "destination")

    # Assert
    assert hasattr(slot_config, "type")
    assert hasattr(slot_config, "prompt")


def test_runtime_context_get_action_config():
    """Test RuntimeContext can retrieve action config"""
    # Arrange
    from pathlib import Path

    from tests.conftest import load_test_config

    config_path = Path("examples/flight_booking/soni.yaml")
    config = load_test_config(config_path)
    context = create_runtime_context(
        config=config,
        scope_manager=MagicMock(),
        normalizer=MagicMock(),
        action_handler=MagicMock(),
        du=MagicMock(),
    )

    # Act
    # Use helper function instead of method
    action_config = get_action_config(context, "search_available_flights")

    # Assert
    assert hasattr(action_config, "inputs")
    assert hasattr(action_config, "outputs")
    assert "origin" in action_config.inputs


def test_runtime_context_get_flow_config():
    """Test RuntimeContext can retrieve flow config"""
    # Arrange
    from pathlib import Path

    from tests.conftest import load_test_config

    config_path = Path("examples/flight_booking/soni.yaml")
    config = load_test_config(config_path)
    context = create_runtime_context(
        config=config,
        scope_manager=MagicMock(),
        normalizer=MagicMock(),
        action_handler=MagicMock(),
        du=MagicMock(),
    )

    # Act
    # Use helper function instead of method
    flow_config = get_flow_config(context, "book_flight")

    # Assert
    assert hasattr(flow_config, "steps")
    assert isinstance(flow_config.steps, list)


def test_runtime_context_get_slot_config_not_found():
    """Test RuntimeContext raises KeyError for non-existent slot"""
    # Arrange
    config = SoniConfig(
        version="1.0",
        settings={"models": {"nlu": {"provider": "openai", "model": "gpt-4o-mini"}}},
        flows={},
        slots={},
        actions={},
    )
    context = create_runtime_context(
        config=config,
        scope_manager=MagicMock(),
        normalizer=MagicMock(),
        action_handler=MagicMock(),
        du=MagicMock(),
    )

    # Act & Assert
    # Use helper function instead of method
    with pytest.raises(KeyError):
        get_slot_config(context, "nonexistent_slot")


def test_dialogue_state_has_no_config_attribute():
    """Test that DialogueState does not have config attribute"""
    # Arrange & Act
    state = create_empty_state()

    # Assert
    assert not hasattr(state, "config")


def test_dialogue_state_is_serializable():
    """Test that DialogueState can be serialized without runtime dependencies"""
    # Arrange
    state = create_empty_state()
    state["messages"] = [{"role": "user", "content": "Hello"}]
    push_flow(state, "book_flight")
    set_slot(state, "destination", "Paris")

    # Act
    serialized = state_to_dict(state)
    deserialized = state_from_dict(serialized)

    # Assert
    assert deserialized["messages"] == state["messages"]
    assert get_all_slots(deserialized) == get_all_slots(state)
    assert get_current_flow(deserialized) == get_current_flow(state)
    assert "config" not in deserialized  # No runtime dependencies in state


def test_node_factories_require_runtime_context():
    """Test that node factories require RuntimeContext"""
    from soni.dm.nodes.factories import (
        create_action_node_factory,
        create_collect_node_factory,
        create_understand_node,
    )

    # Arrange
    config = SoniConfig(
        version="1.0",
        settings={"models": {"nlu": {"provider": "openai", "model": "gpt-4o-mini"}}},
        flows={},
        slots={"test_slot": {"type": "string", "prompt": "Enter value"}},
        actions={"test_action": {"inputs": [], "outputs": []}},
    )
    mock_scope = MagicMock()
    mock_normalizer = MagicMock()
    mock_handler = MagicMock()
    mock_du = MagicMock()
    context = create_runtime_context(
        config=config,
        scope_manager=mock_scope,
        normalizer=mock_normalizer,
        action_handler=mock_handler,
        du=mock_du,
    )

    # Act & Assert - Should work with context
    node_fn = create_understand_node(
        scope_manager=mock_scope,
        normalizer=mock_normalizer,
        nlu_provider=mock_du,
        context=context,
    )
    assert callable(node_fn)

    collect_fn = create_collect_node_factory("test_slot", context)
    assert callable(collect_fn)

    action_fn = create_action_node_factory("test_action", context)
    assert callable(action_fn)

    # Act & Assert - Should fail without context (TypeError for missing required arg)
    with pytest.raises(TypeError):
        create_understand_node(
            scope_manager=mock_scope,
            normalizer=mock_normalizer,
            nlu_provider=mock_du,
            # context missing - should raise TypeError
        )

    with pytest.raises(TypeError):
        create_collect_node_factory("test_slot")  # context missing

    with pytest.raises(TypeError):
        create_action_node_factory("test_action")  # context missing
