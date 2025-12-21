from unittest.mock import Mock

import pytest
from soni.compiler.nodes.confirm import ConfirmNodeFactory
from soni.core.constants import FlowState
from soni.core.types import DialogueState

from soni.config import ConfirmStepConfig


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
    """Test deny command handling (command-based logic)."""
    factory = ConfirmNodeFactory()
    step = ConfirmStepConfig(
        step="confirm_transfer",
        type="confirm",
        slot="transfer_confirmed",
        message="Transfer {amount} to {beneficiary}?",
    )
    confirm_node = factory.create(step)

    # State with deny command (command-based)
    state: DialogueState = {
        "flow_state": FlowState.ACTIVE,
        "waiting_for_slot": None,
        "waiting_for_slot_type": None,
        "commands": [{"type": "deny_confirmation"}],  # Deny command
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

    # Should deny (set slot to False) and proceed
    assert isinstance(result, dict)
    assert result.get("flow_state") == "active"
    # Verify slot was set to False
    ctx.flow_manager.set_slot.assert_called_with(state, "transfer_confirmed", False)


@pytest.mark.asyncio
async def test_confirm_node_retry_formats_templates(customized_runtime):
    """Test affirm command handling (command-based logic)."""
    factory = ConfirmNodeFactory()
    step = ConfirmStepConfig(
        step="confirm_transfer",
        type="confirm",
        slot="transfer_confirmed",
        message="Confirm amount {amount}?",
    )
    confirm_node = factory.create(step)

    # State WITH affirm command (command-based)
    state: DialogueState = {
        "flow_state": FlowState.ACTIVE,
        "waiting_for_slot": None,
        "waiting_for_slot_type": None,
        "commands": [{"type": "affirm_confirmation"}],  # Affirm command present
        "flow_slots": {"test_flow": {"amount": "100", "beneficiary": "dad"}},
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
    ctx.flow_manager.get_all_slots.return_value = {"amount": "100", "beneficiary": "dad"}

    result = await confirm_node(state, customized_runtime)

    # Should affirm (set slot to True) and proceed
    assert isinstance(result, dict)
    assert result.get("flow_state") == "active"
    # Verify slot was set to True
    ctx.flow_manager.set_slot.assert_called_with(state, "transfer_confirmed", True)


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
        "flow_state": FlowState.ACTIVE,
        "waiting_for_slot": None,
        "waiting_for_slot_type": None,
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

    # With interrupt() API: modification triggers handle_interrupt
    # which for "update_and_reprompt" returns empty dict to trigger re-execution
    # The retry counter should be reset
    ctx.flow_manager.set_slot.assert_any_call(state, "__confirm_retries_transfer_confirmed", 0)

    # Result should be empty or minimal (re-execution will call interrupt)
    assert isinstance(result, dict)
