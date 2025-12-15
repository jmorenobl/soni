"""Unit tests for CommandExecutor."""

from unittest.mock import AsyncMock, MagicMock

import pytest

from soni.core.commands import AffirmConfirmation, SetSlot, StartFlow
from soni.core.constants import ConversationState
from soni.core.types import DialogueState, RuntimeContext
from soni.dm.executor import execute_commands_node


@pytest.fixture
def mock_context():
    """Create a mock runtime context."""
    return RuntimeContext(
        config=MagicMock(),
        scope_manager=MagicMock(),
        normalizer=MagicMock(),
        action_handler=MagicMock(),
        du=MagicMock(),
        step_manager=MagicMock(),
        flow_manager=MagicMock(),
    )


@pytest.fixture
def base_state():
    """Create a basic dialogue state."""
    return DialogueState(
        user_message="hello",
        last_response="",
        messages=[],
        flow_stack=[],
        flow_slots={},
        conversation_state=ConversationState.IDLE,
        current_step=None,
        waiting_for_slot=None,
        current_prompted_slot=None,
        all_slots_filled=False,
        nlu_result=None,
        command_log=[],
        last_nlu_call=None,
        action_result=None,
        digression_depth=0,
        last_digression_type=None,
        turn_count=0,
        trace=[],
        metadata={},
    )


@pytest.mark.asyncio
async def test_execute_no_commands(base_state, mock_context):
    """Test executing empty command list."""
    base_state["command_log"] = []
    updates = await execute_commands_node(base_state, mock_context)
    assert updates == {}


@pytest.mark.asyncio
async def test_execute_start_flow(base_state, mock_context):
    """Test executing StartFlow command."""
    cmd = StartFlow(flow_name="test_flow")
    base_state["command_log"] = [cmd]

    updates = await execute_commands_node(base_state, mock_context)

    assert updates["conversation_state"] == ConversationState.UNDERSTANDING


@pytest.mark.asyncio
async def test_execute_affirm_confirmation(base_state, mock_context):
    """Test executing AffirmConfirmation command."""
    cmd = AffirmConfirmation()
    base_state["command_log"] = [cmd]

    updates = await execute_commands_node(base_state, mock_context)

    assert updates["conversation_state"] == ConversationState.READY_FOR_ACTION


@pytest.mark.asyncio
async def test_execute_multiple_commands(base_state, mock_context):
    """Test executing multiple commands in sequence."""
    cmd1 = SetSlot(slot_name="slot1", value="val1")
    cmd2 = AffirmConfirmation()

    base_state["command_log"] = [cmd1, cmd2]

    updates = await execute_commands_node(base_state, mock_context)

    # State should reflect the final command's impact
    assert updates["conversation_state"] == ConversationState.READY_FOR_ACTION
