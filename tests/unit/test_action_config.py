"""Tests for ActionConfig"""

import pytest

from soni.core.config import ActionConfig


def test_action_config_basic():
    """Test ActionConfig with basic fields"""
    # Arrange & Act
    config = ActionConfig(
        inputs=["origin", "destination"],
        outputs=["flights"],
    )

    # Assert
    assert config.inputs == ["origin", "destination"]
    assert config.outputs == ["flights"]


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
    assert config.inputs == ["origin", "destination"]
    assert config.outputs == ["flights"]


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
