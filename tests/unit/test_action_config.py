"""Tests for ActionConfig deprecation"""

import warnings
from warnings import catch_warnings

import pytest

from soni.core.config import ActionConfig


def test_action_config_without_handler_is_valid():
    """Test ActionConfig without handler field is valid"""
    # Arrange & Act
    config = ActionConfig(
        inputs=["origin", "destination"],
        outputs=["flights"],
    )

    # Assert
    assert config.handler is None
    assert config.inputs == ["origin", "destination"]
    assert config.outputs == ["flights"]


def test_action_config_with_handler_emits_deprecation_warning():
    """Test ActionConfig with handler emits DeprecationWarning"""
    # Arrange & Act & Assert
    with catch_warnings(record=True) as warnings_list:
        warnings.simplefilter("always")

        config = ActionConfig(
            handler="flights.search_flights",  # Deprecated
            inputs=["origin"],
            outputs=["flights"],
        )

        # Verify warning emitted
        assert len(warnings_list) == 1
        assert issubclass(warnings_list[0].category, DeprecationWarning)
        assert "deprecated" in str(warnings_list[0].message).lower()
        assert "ActionRegistry" in str(warnings_list[0].message)
        assert config.handler == "flights.search_flights"


def test_action_config_handler_defaults_to_none():
    """Test ActionConfig handler defaults to None"""
    # Arrange & Act
    config = ActionConfig(
        inputs=["origin"],
        outputs=["flights"],
    )

    # Assert
    assert config.handler is None


def test_action_config_with_description():
    """Test ActionConfig with description field"""
    # Arrange & Act
    config = ActionConfig(
        description="Search for flights",
        inputs=["origin", "destination"],
        outputs=["flights"],
    )

    # Assert
    assert config.description == "Search for flights"
    assert config.handler is None


@pytest.mark.asyncio
async def test_action_handler_requires_registry():
    """Test ActionHandler requires actions in registry"""
    from soni.actions.base import ActionHandler
    from soni.actions.registry import ActionRegistry
    from soni.core.errors import ActionNotFoundError
    from tests.conftest import load_test_config

    # Arrange
    ActionRegistry.clear()

    config = load_test_config("examples/flight_booking/soni.yaml")
    handler = ActionHandler(config)

    # Act & Assert
    with pytest.raises(ActionNotFoundError) as exc_info:
        await handler.execute("unregistered_action", {})

    error_str = str(exc_info.value)
    assert "not found in registry" in error_str or "not found" in error_str
    assert "ActionRegistry.register" in error_str or "register" in error_str
