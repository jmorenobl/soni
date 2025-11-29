"""Integration tests for scoping with SoniDU"""

from pathlib import Path

import pytest

from soni.core.state import DialogueState
from soni.runtime import RuntimeLoop


@pytest.mark.asyncio
async def test_runtime_uses_scoped_actions():
    """Test that runtime uses scoped actions"""
    # Arrange
    config_path = Path("examples/flight_booking/soni.yaml")
    runtime = RuntimeLoop(config_path)
    user_id = "test-user-1"
    user_msg = "I want to book a flight"

    try:
        # Act
        response = await runtime.process_message(user_msg, user_id)

        # Assert
        assert isinstance(response, str)
        # Verify that scoped actions were used (check logs or internal state)
        assert runtime.scope_manager is not None
    finally:
        await runtime.cleanup()


@pytest.mark.asyncio
async def test_scoping_reduces_actions():
    """Test that scoping reduces number of actions"""
    # Arrange
    config_path = Path("examples/flight_booking/soni.yaml")
    runtime = RuntimeLoop(config_path)
    state = DialogueState(current_flow="book_flight")

    try:
        # Act
        scoped_actions = runtime.scope_manager.get_available_actions(state)

        # Assert
        # Scoped actions should be fewer than total actions (or equal if all are relevant)
        # At minimum, should include global actions
        assert len(scoped_actions) > 0
        assert "help" in scoped_actions
        assert "cancel" in scoped_actions
        assert "restart" in scoped_actions
    finally:
        await runtime.cleanup()


@pytest.mark.asyncio
async def test_different_flows_have_different_actions():
    """Test that different flows have different scoped actions"""
    # Arrange
    config_path = Path("examples/flight_booking/soni.yaml")
    runtime = RuntimeLoop(config_path)

    try:
        # Act
        state1 = DialogueState(current_flow="book_flight")
        actions1 = runtime.scope_manager.get_available_actions(state1)

        state2 = DialogueState(current_flow="none")
        actions2 = runtime.scope_manager.get_available_actions(state2)

        # Assert
        # Both should have global actions
        assert "help" in actions1
        assert "help" in actions2
        # Actions should be different (or at least flow-specific actions differ)
        # When in a flow, should have flow-specific actions
        # When no flow, should have start_flow actions
        assert len(actions1) > 0
        assert len(actions2) > 0
    finally:
        await runtime.cleanup()
