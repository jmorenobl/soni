from unittest.mock import Mock

import pytest

from soni.compiler.nodes.confirm import ConfirmNodeFactory
from soni.config import ConfirmStepConfig
from soni.core.constants import FlowState, SlotWaitType
from soni.core.types import DialogueState


@pytest.fixture
def customized_runtime(mock_runtime):
    """Customize mock runtime with confirmation settings."""
    ctx = mock_runtime.context

    # Mock config settings hierarchy
    ctx.config.settings = Mock()
    ctx.config.settings.patterns = Mock()
    ctx.config.settings.patterns.confirmation = Mock()
    # Set default behaviors
    ctx.config.settings.patterns.confirmation.modification_handling = "update_and_reprompt"
    ctx.config.settings.patterns.confirmation.update_acknowledgment = "Updated."
    ctx.config.settings.patterns.confirmation.retry_message = (
        "I need a clear yes or no answer. {prompt}"
    )
    ctx.config.settings.patterns.confirmation.max_retries = 3

    # Ensure flow_manager returns None for set_slot (synchronous mock behavior)
    ctx.flow_manager.set_slot = Mock(return_value=None)

    return mock_runtime


@pytest.mark.asyncio
async def test_confirm_node_reprompts_on_deny_with_setslot(customized_runtime):
    """Test re-prompt when NLU generates DenyConfirmation + SetSlot.

    This is the ELEGANT solution: NLU detects slot modification during confirmation
    and generates both commands. confirm_node sees DenyConfirmation with SetSlot
    and re-prompts with updated values (without asking for the value again).
    """
    factory = ConfirmNodeFactory()
    step = ConfirmStepConfig(
        step="confirm_transfer",
        type="confirm",
        slot="transfer_confirmed",
        message="Transfer {amount} to {beneficiary}?",
    )
    confirm_node = factory.create(step)

    # State with BOTH DenyConfirmation and SetSlot commands
    state: DialogueState = {
        "flow_state": FlowState.WAITING_INPUT,
        "waiting_for_slot": "transfer_confirmed",
        "waiting_for_slot_type": SlotWaitType.CONFIRMATION,
        "commands": [
            {"type": "deny"},
            {"type": "set_slot", "slot": "amount", "value": "200"},
        ],
        "flow_slots": {"test_flow": {"amount": "200", "beneficiary": "mom"}},
        "flow_stack": [],
        "messages": [],
        "user_message": "",
        "last_response": "",
        "response": None,
        "action_result": None,
        "_branch_target": None,
        "turn_count": 0,
        "metadata": {},
    }

    ctx = customized_runtime.context
    ctx.flow_manager.get_slot.return_value = None
    ctx.flow_manager.get_all_slots.return_value = {
        "amount": "200",
        "beneficiary": "mom",
    }

    result = await confirm_node(state, customized_runtime)

    assert isinstance(result, dict)
    assert result["waiting_for_slot"] == "transfer_confirmed"
    assert result["waiting_for_slot_type"] == SlotWaitType.CONFIRMATION
    assert "200" in result["last_response"]
    assert "mom" in result["last_response"]
    assert "change" not in result["last_response"].lower()


@pytest.mark.asyncio
async def test_confirm_node_retry_formats_templates(customized_runtime):
    """Test retry prompt correctly formats template placeholders."""
    factory = ConfirmNodeFactory()
    step = ConfirmStepConfig(
        step="confirm_transfer",
        type="confirm",
        slot="transfer_confirmed",
        message="Confirm amount {amount}?",
    )
    confirm_node = factory.create(step)

    state: DialogueState = {
        "flow_state": FlowState.WAITING_INPUT,
        "waiting_for_slot": "transfer_confirmed",
        "waiting_for_slot_type": SlotWaitType.CONFIRMATION,
        "commands": [],
        "flow_slots": {"test_flow": {"amount": "100"}},
        "flow_stack": [],
        "messages": [],
        "user_message": "",
        "last_response": "",
        "response": None,
        "action_result": None,
        "_branch_target": None,
        "turn_count": 0,
        "metadata": {},
    }

    ctx = customized_runtime.context
    ctx.flow_manager.get_slot.return_value = None
    ctx.flow_manager.get_all_slots.return_value = {"amount": "100"}

    result = await confirm_node(state, customized_runtime)

    assert isinstance(result, dict)
    msg = result["messages"][0].content
    assert "I need a clear yes or no answer" in msg
    assert "Confirm amount 100?" in msg
    assert "{amount}" not in msg


@pytest.mark.asyncio
async def test_confirm_node_modification_updates_and_reprompts(customized_runtime):
    """Test standard slot modification behavior (update_and_reprompt)."""
    factory = ConfirmNodeFactory()
    step = ConfirmStepConfig(
        step="confirm_transfer",
        type="confirm",
        slot="transfer_confirmed",
        message="Transfer {amount} to {beneficiary}?",
    )
    confirm_node = factory.create(step)

    # State with ONLY SetSlot (no Deny) - this was the user's issue
    state: DialogueState = {
        "flow_state": FlowState.WAITING_INPUT,
        "waiting_for_slot": "transfer_confirmed",
        "waiting_for_slot_type": SlotWaitType.CONFIRMATION,
        "commands": [
            {"type": "set_slot", "slot": "amount", "value": "200"},
        ],
        "flow_slots": {"test_flow": {"amount": "200", "beneficiary": "mom"}},
        "flow_stack": [],
        "messages": [],
        "user_message": "Let's make it 200",
        "last_response": "",
        "turn_count": 1,
        "metadata": {},
        "response": None,
        "action_result": None,
        "_branch_target": None,
    }

    ctx = customized_runtime.context
    ctx.flow_manager.get_slot.return_value = None
    ctx.flow_manager.get_all_slots.return_value = {
        "amount": "200",
        "beneficiary": "mom",
    }

    result = await confirm_node(state, customized_runtime)

    # Should update retry counter to 0 (reset)
    ctx.flow_manager.set_slot.assert_any_call(state, "__confirm_retries_transfer_confirmed", 0)

    # Should stay in confirmation with natural prompt
    assert isinstance(result, dict)
    assert result["waiting_for_slot"] == "transfer_confirmed"
    msg = result["messages"][0].content
    assert "Updated." in msg
    assert "Transfer 200 to mom?" in msg
    assert "clear yes or no" not in msg  # Should NOT scold user
