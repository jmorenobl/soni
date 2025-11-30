"""Tests for RuntimeContext"""

from unittest.mock import MagicMock

import pytest

from soni.core.config import SoniConfig
from soni.core.state import DialogueState, RuntimeContext


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
    context = RuntimeContext(
        config=config,
        scope_manager=mock_scope,
        normalizer=mock_normalizer,
        action_handler=mock_handler,
        du=mock_du,
    )

    # Assert
    assert context.config is config
    assert context.scope_manager is mock_scope
    assert context.normalizer is mock_normalizer
    assert context.action_handler is mock_handler
    assert context.du is mock_du


def test_runtime_context_get_slot_config():
    """Test RuntimeContext can retrieve slot config"""
    # Arrange
    from pathlib import Path

    config_path = Path("examples/flight_booking/soni.yaml")
    config = SoniConfig.from_yaml(config_path)
    context = RuntimeContext(
        config=config,
        scope_manager=MagicMock(),
        normalizer=MagicMock(),
        action_handler=MagicMock(),
        du=MagicMock(),
    )

    # Act
    slot_config = context.get_slot_config("destination")

    # Assert
    assert hasattr(slot_config, "type")
    assert hasattr(slot_config, "prompt")


def test_runtime_context_get_action_config():
    """Test RuntimeContext can retrieve action config"""
    # Arrange
    from pathlib import Path

    config_path = Path("examples/flight_booking/soni.yaml")
    config = SoniConfig.from_yaml(config_path)
    context = RuntimeContext(
        config=config,
        scope_manager=MagicMock(),
        normalizer=MagicMock(),
        action_handler=MagicMock(),
        du=MagicMock(),
    )

    # Act
    action_config = context.get_action_config("search_available_flights")

    # Assert
    assert hasattr(action_config, "inputs")
    assert hasattr(action_config, "outputs")
    assert "origin" in action_config.inputs


def test_runtime_context_get_flow_config():
    """Test RuntimeContext can retrieve flow config"""
    # Arrange
    from pathlib import Path

    config_path = Path("examples/flight_booking/soni.yaml")
    config = SoniConfig.from_yaml(config_path)
    context = RuntimeContext(
        config=config,
        scope_manager=MagicMock(),
        normalizer=MagicMock(),
        action_handler=MagicMock(),
        du=MagicMock(),
    )

    # Act
    flow_config = context.get_flow_config("book_flight")

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
    context = RuntimeContext(
        config=config,
        scope_manager=MagicMock(),
        normalizer=MagicMock(),
        action_handler=MagicMock(),
        du=MagicMock(),
    )

    # Act & Assert
    with pytest.raises(KeyError):
        context.get_slot_config("nonexistent_slot")


def test_dialogue_state_has_no_config_attribute():
    """Test that DialogueState does not have config attribute"""
    # Arrange & Act
    state = DialogueState()

    # Assert
    assert not hasattr(state, "config")


def test_dialogue_state_is_serializable():
    """Test that DialogueState can be serialized without runtime dependencies"""
    # Arrange
    state = DialogueState(
        messages=[{"role": "user", "content": "Hello"}],
        slots={"destination": "Paris"},
        current_flow="book_flight",
    )

    # Act
    serialized = state.to_dict()
    deserialized = DialogueState.from_dict(serialized)

    # Assert
    assert deserialized.messages == state.messages
    assert deserialized.slots == state.slots
    assert deserialized.current_flow == state.current_flow
    assert not hasattr(deserialized, "config")
