"""Tests for core interfaces (Protocols)"""

import inspect
from typing import Any, get_args, get_origin

import pytest

from soni.core.config import SoniConfig
from soni.core.interfaces import IActionHandler, INLUProvider, IScopeManager


def test_action_handler_implements_protocol():
    """Test that ActionHandler implements IActionHandler Protocol"""
    # Arrange
    from soni.actions.base import ActionHandler

    config_dict = {
        "version": "0.1",
        "settings": {
            "models": {
                "nlu": {
                    "provider": "openai",
                    "model": "gpt-4o-mini",
                    "temperature": 0.1,
                },
            },
        },
        "flows": {},
        "slots": {},
        "actions": {},
    }
    config = SoniConfig(**config_dict)
    handler = ActionHandler(config)

    # Act & Assert
    assert isinstance(handler, IActionHandler)


@pytest.mark.asyncio
async def test_iactionhandler_protocol_signature():
    """Test that IActionHandler Protocol has correct method signature"""
    # Arrange
    from soni.core.interfaces import IActionHandler

    # Act
    execute_method = IActionHandler.execute

    # Assert
    # Protocol methods have special handling, check signature
    sig = inspect.signature(execute_method)
    assert "action_name" in sig.parameters
    assert "slots" in sig.parameters
    # Check return annotation (can be string or actual type)
    return_ann = sig.return_annotation
    if isinstance(return_ann, str):
        assert "dict" in return_ann and "Any" in return_ann
    else:
        assert get_origin(return_ann) is dict


class MockActionHandler:
    """Mock implementation for testing Protocol"""

    async def execute(self, action_name: str, slots: dict[str, Any]) -> dict[str, Any]:
        """Mock execute method"""
        return {"mock_output": "test"}


def test_mock_handler_satisfies_protocol():
    """Test that a mock implementation satisfies IActionHandler"""
    # Arrange
    mock = MockActionHandler()

    # Act & Assert
    assert isinstance(mock, IActionHandler)


@pytest.mark.asyncio
async def test_mock_handler_execute():
    """Test that mock handler can be used as IActionHandler"""
    # Arrange
    mock = MockActionHandler()

    # Act
    result = await mock.execute("test_action", {"slot1": "value1"})

    # Assert
    assert result == {"mock_output": "test"}


def test_inluprovider_protocol():
    """Test that INLUProvider Protocol is properly defined"""
    # Act
    predict_method = INLUProvider.predict

    # Assert
    sig = inspect.signature(predict_method)
    assert "user_message" in sig.parameters
    assert "dialogue_history" in sig.parameters
    assert "current_slots" in sig.parameters
    assert "available_actions" in sig.parameters
    assert "current_flow" in sig.parameters


def test_iscopemanager_protocol():
    """Test that IScopeManager Protocol is properly defined"""
    # Act
    get_actions_method = IScopeManager.get_available_actions

    # Assert
    sig = inspect.signature(get_actions_method)
    assert "state" in sig.parameters
    # Check return annotation (can be string or actual type)
    return_ann = sig.return_annotation
    if isinstance(return_ann, str):
        assert "list" in return_ann and "str" in return_ann
    else:
        assert get_origin(return_ann) is list
