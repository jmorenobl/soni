"""Tests for ActionRegistry"""

import pytest

from soni.actions.registry import ActionRegistry


def test_register_and_get_action():
    """Test registering and retrieving action"""

    # Arrange
    @ActionRegistry.register("test_action")
    async def test_func(param: str) -> dict[str, str]:
        return {"result": param}

    # Act
    action = ActionRegistry.get("test_action")

    # Assert
    assert action is test_func


@pytest.mark.asyncio
async def test_registered_action_executes():
    """Test registered action can be executed"""

    # Arrange
    @ActionRegistry.register("greet")
    async def greet(name: str) -> dict[str, str]:
        return {"message": f"Hello {name}"}

    # Act
    action = ActionRegistry.get("greet")
    result = await action(name="World")

    # Assert
    assert result["message"] == "Hello World"


@pytest.mark.asyncio
async def test_sync_action_executes():
    """Test registered sync action can be executed"""

    # Arrange
    @ActionRegistry.register("add")
    def add(a: int, b: int) -> dict[str, int]:
        return {"sum": a + b}

    # Act
    action = ActionRegistry.get("add")
    result = action(a=5, b=3)

    # Assert
    assert result["sum"] == 8


def test_get_nonexistent_action():
    """Test getting non-existent action raises error"""
    # Act & Assert
    with pytest.raises(ValueError, match="not registered"):
        ActionRegistry.get("nonexistent_action")


def test_list_actions():
    """Test listing all actions"""

    # Arrange
    @ActionRegistry.register("test_list_action")
    def test_action() -> dict:
        return {}

    # Act
    actions = ActionRegistry.list_actions()

    # Assert
    assert isinstance(actions, list)
    assert "test_list_action" in actions


def test_is_registered():
    """Test checking if action is registered"""

    # Arrange
    @ActionRegistry.register("check_action")
    def check() -> dict:
        return {}

    # Act & Assert
    assert ActionRegistry.is_registered("check_action")
    assert not ActionRegistry.is_registered("not_registered")
