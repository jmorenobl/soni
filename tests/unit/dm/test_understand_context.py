from unittest.mock import Mock

import pytest

from soni.core.constants import FlowState, SlotWaitType
from soni.core.types import DialogueState, RuntimeContext
from soni.dm.nodes.understand import build_du_context


@pytest.fixture
def mock_context():
    # Mock RuntimeContext and its components
    ctx = Mock(spec=RuntimeContext)
    ctx.config = Mock()
    ctx.config.flows = {}
    ctx.flow_manager = Mock()
    # Mock active context return
    ctx.flow_manager.get_active_context.return_value = {
        "flow_name": "test_flow",
        "flow_id": "test_flow_id",
    }
    return ctx


def test_build_du_context_detects_confirming_state(mock_context):
    """Test that conversation state is 'confirming' when waiting_for_slot_type is 'confirmation'."""
    state: DialogueState = {
        "messages": [],
        "user_message": "",
        "last_response": "",
        "waiting_for_slot": "transfer_confirmed",
        "waiting_for_slot_type": SlotWaitType.CONFIRMATION,
        "flow_state": FlowState.ACTIVE,
        "flow_stack": [],
        "flow_slots": {},
        "commands": [],
        "response": None,
        "action_result": None,
        "_branch_target": None,
        "turn_count": 0,
        "metadata": {},
    }

    du_ctx = build_du_context(state, mock_context)

    assert du_ctx.conversation_state == "confirming"
    assert du_ctx.expected_slot == "transfer_confirmed"


def test_build_du_context_detects_collecting_state(mock_context):
    """Test fallback to 'collecting' for normal slots."""
    state: DialogueState = {
        "messages": [],
        "user_message": "",
        "last_response": "",
        "waiting_for_slot": "amount",
        "waiting_for_slot_type": SlotWaitType.COLLECTION,
        "flow_state": FlowState.ACTIVE,
        "flow_stack": [],
        "flow_slots": {},
        "commands": [],
        "response": None,
        "action_result": None,
        "_branch_target": None,
        "turn_count": 0,
        "metadata": {},
    }

    du_ctx = build_du_context(state, mock_context)

    assert du_ctx.conversation_state == "collecting"


def test_build_du_context_detects_idle_state(mock_context):
    """Test 'idle' when no active flow."""
    mock_context.flow_manager.get_active_context.return_value = None
    state: DialogueState = {
        "messages": [],
        "user_message": "",
        "last_response": "",
        "waiting_for_slot": None,
        "waiting_for_slot_type": None,
        "flow_state": FlowState.IDLE,
        "flow_stack": [],
        "flow_slots": {},
        "commands": [],
        "response": None,
        "action_result": None,
        "_branch_target": None,
        "turn_count": 0,
        "metadata": {},
    }

    du_ctx = build_du_context(state, mock_context)

    assert du_ctx.conversation_state == "idle"
