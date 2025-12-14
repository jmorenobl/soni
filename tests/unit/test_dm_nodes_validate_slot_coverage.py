"""Targeted coverage tests for validate_slot node."""

from unittest.mock import AsyncMock, MagicMock

import pytest

from soni.core.state import create_empty_state
from soni.dm.nodes.validate_slot import (
    _handle_correction_flow,
    validate_slot_node,
)
from soni.du.models import MessageType, NLUOutput, SlotAction, SlotValue


@pytest.mark.asyncio
async def test_fallback_logic_enum_conversion_failure(caplog):
    """Test fallback logic handles invalid SlotAction enum string gracefully."""
    import logging

    # Arrange
    state = create_empty_state()
    state["waiting_for_slot"] = "origin"
    state["user_message"] = "Madrid"
    state["nlu_result"] = {"message_type": "slot_value", "slots": []}

    # Setup flow stack
    state["flow_stack"] = [
        {
            "flow_id": "flow_1",
            "flow_name": "book_flight",
            "current_step": "collect_origin",  # Must have current step for fallback
            "context": {},
        }
    ]

    # Mock fallback result utilizing MagicMock with spec to prevent model_dump existence
    # We use spec to ensure hasattr(fallback_slot, "model_dump") returns False
    fallback_slot = MagicMock(spec=["name", "value", "action", "confidence"])
    fallback_slot.name = "origin"
    fallback_slot.value = "Madrid"
    fallback_slot.action = "INVALID_ACTION"  # This will cause ValueError in logic
    fallback_slot.confidence = 0.8

    # Mock the NLU result object
    fallback_result = MagicMock()
    fallback_result.message_type = "slot_value"  # Use string directly to be safe
    fallback_result.slots = [fallback_slot]

    mock_nlu_provider = AsyncMock()
    mock_nlu_provider.predict.return_value = fallback_result

    mock_scope_manager = MagicMock()
    mock_scope_manager.get_available_actions.return_value = []
    mock_scope_manager.get_available_flows.return_value = {}

    mock_runtime = MagicMock()
    mock_runtime.context = {
        "normalizer": AsyncMock(),
        "nlu_provider": mock_nlu_provider,
        "scope_manager": mock_scope_manager,
        "flow_manager": MagicMock(),
        "step_manager": MagicMock(),
    }
    mock_runtime.context["normalizer"].normalize_slot.return_value = "MAD"
    mock_runtime.context["flow_manager"].get_active_context.return_value = state["flow_stack"][0]

    # Mock step manager to prevent errors in later stages
    mock_runtime.context["step_manager"].is_step_complete.return_value = False
    mock_runtime.context["step_manager"].advance_through_completed_steps.return_value = {
        "conversation_state": "waiting_for_slot",
        "flow_stack": state["flow_stack"],
    }

    # Act
    import sys
    from unittest.mock import patch

    mock_dspy = MagicMock()
    mock_history = MagicMock()
    mock_dspy.History.return_value = mock_history

    with patch.dict(sys.modules, {"dspy": mock_dspy}):
        result = await validate_slot_node(state, mock_runtime)

    # Assert
    # Should default to SlotAction.PROVIDE and process successfully
    assert "flow_slots" in result
    assert result["flow_slots"]["flow_1"]["origin"] == "MAD"


@pytest.mark.asyncio
async def test_correction_navigation_confirmation_state_matching():
    """Test correction navigation matches previous confirmation state."""
    # Arrange
    state = create_empty_state()
    state["conversation_state"] = "confirming"  # Previous state

    from soni.core.config import FlowConfig, StepConfig, TriggerConfig

    flow_config = FlowConfig(
        description="Book flight",
        trigger=TriggerConfig(intents=[]),
        steps=[
            StepConfig(step="collect_origin", type="collect", slot="origin"),
            StepConfig(step="confirm_booking", type="confirm", message="Confirm?"),
        ],
    )

    flow_slots = {"flow_1": {"origin": "Madrid"}}
    previous_step = "collect_origin"  # Hypothetically converting from here but was in confirming?

    mock_runtime = MagicMock()
    mock_runtime.context = {
        "step_manager": MagicMock(),
        "flow_manager": MagicMock(),
    }

    # Setup step config
    mock_runtime.context["step_manager"].config.flows = {"book_flight": flow_config}
    active_ctx = {
        "flow_id": "flow_1",
        "flow_name": "book_flight",
        "current_step": "confirm_booking",
    }
    mock_runtime.context["flow_manager"].get_active_context.return_value = active_ctx

    # Mock get_current_step_config to return confirm config when asked for confirm_booking
    mock_target_config = MagicMock()
    mock_target_config.type = "confirm"
    mock_runtime.context["step_manager"].get_current_step_config.return_value = mock_target_config

    # Act
    result = _handle_correction_flow(state, mock_runtime, flow_slots, previous_step)

    # Assert
    # Should navigate to confirm_booking because we were confirming
    assert result["conversation_state"] == "ready_for_confirmation"
    assert result["current_step"] == "confirm_booking"


@pytest.mark.asyncio
async def test_correction_navigation_action_state_matching():
    """Test correction navigation matches previous action state."""
    # Arrange
    state = create_empty_state()
    state["conversation_state"] = "executing_action"

    from soni.core.config import FlowConfig, StepConfig, TriggerConfig

    flow_config = FlowConfig(
        description="Book flight",
        trigger=TriggerConfig(intents=[]),
        steps=[
            StepConfig(step="collect_origin", type="collect", slot="origin"),
            StepConfig(step="execute_booking", type="action", call="book"),
        ],
    )

    flow_slots = {"flow_1": {"origin": "Madrid"}}
    previous_step = "collect_origin"

    mock_runtime = MagicMock()
    mock_runtime.context = {
        "step_manager": MagicMock(),
        "flow_manager": MagicMock(),
    }

    mock_runtime.context["step_manager"].config.flows = {"book_flight": flow_config}
    active_ctx = {"flow_id": "flow_1", "flow_name": "book_flight"}
    mock_runtime.context["flow_manager"].get_active_context.return_value = active_ctx

    # Mock action config
    mock_target_config = MagicMock()
    mock_target_config.type = "action"
    mock_runtime.context["step_manager"].get_current_step_config.return_value = mock_target_config

    # Act
    result = _handle_correction_flow(state, mock_runtime, flow_slots, previous_step)

    # Assert
    # Should navigate to execute_booking
    assert result["conversation_state"] == "ready_for_action"
    assert result["current_step"] == "execute_booking"


@pytest.mark.asyncio
async def test_fallback_logic_classifies_as_non_slot():
    """Test fallback logic handles NLU re-classification as non-slot_value."""
    # Arrange
    state = create_empty_state()
    state["waiting_for_slot"] = "origin"
    state["user_message"] = "What time is it?"  # Digression
    state["nlu_result"] = {"message_type": "slot_value", "slots": []}

    # Setup flow stack
    state["flow_stack"] = [
        {
            "flow_id": "flow_1",
            "flow_name": "book_flight",
            "current_step": "collect_origin",
            "context": {},
        }
    ]

    # Mock fallback result as DIGRESSION
    fallback_result = MagicMock()
    fallback_result.message_type = "digression"
    fallback_result.slots = []

    mock_nlu_provider = AsyncMock()
    mock_nlu_provider.predict.return_value = fallback_result

    mock_scope_manager = MagicMock()
    mock_scope_manager.get_available_actions.return_value = []
    mock_scope_manager.get_available_flows.return_value = {}

    mock_runtime = MagicMock()
    mock_runtime.context = {
        "normalizer": AsyncMock(),
        "nlu_provider": mock_nlu_provider,
        "scope_manager": mock_scope_manager,
        "flow_manager": MagicMock(),
        "step_manager": MagicMock(),
    }
    mock_runtime.context["flow_manager"].get_active_context.return_value = state["flow_stack"][0]

    # Mock step manager to indicate step is NOT complete (since no slot extracted)
    mock_runtime.context["step_manager"].is_step_complete.return_value = False

    # Act
    import sys
    from unittest.mock import patch

    mock_dspy = MagicMock()
    mock_dspy.History.return_value = MagicMock()

    with patch.dict(sys.modules, {"dspy": mock_dspy}):
        result = await validate_slot_node(state, mock_runtime)

    # Assert
    # Should NOT have extracted slots
    assert "flow_slots" not in result
    # Should be in idle state passing through to generate response (since not handled)
    # The code proceeds to "if not slots: ... if waiting_for_slot: ..."
    # It generates a prompt asking for the slot again
    assert result["conversation_state"] == "idle"
    # Ensure it's asking for the slot
    assert (
        "origin" in result.get("last_response", "").lower()
        or "value" in result.get("last_response", "").lower()
    )


@pytest.mark.asyncio
async def test_fallback_logic_fails_to_extract():
    """Test fallback logic where NLU classifies as slot_value but extracts nothing."""
    # Arrange
    state = create_empty_state()
    state["waiting_for_slot"] = "origin"
    state["user_message"] = "I don't know"
    state["nlu_result"] = {"message_type": "slot_value", "slots": []}

    state["flow_stack"] = [
        {
            "flow_id": "flow_1",
            "flow_name": "book_flight",
            "current_step": "collect_origin",
            "context": {},
        }
    ]

    # Mock fallback result as SLOT_VALUE but empty slots
    fallback_result = MagicMock()
    fallback_result.message_type = "slot_value"
    fallback_result.slots = []  # Empty

    mock_nlu_provider = AsyncMock()
    mock_nlu_provider.predict.return_value = fallback_result

    mock_scope_manager = MagicMock()
    mock_scope_manager.get_available_actions.return_value = []
    mock_scope_manager.get_available_flows.return_value = {}

    mock_runtime = MagicMock()
    mock_runtime.context = {
        "normalizer": AsyncMock(),
        "nlu_provider": mock_nlu_provider,
        "scope_manager": mock_scope_manager,
        "flow_manager": MagicMock(),
        "step_manager": MagicMock(),
    }
    mock_runtime.context["flow_manager"].get_active_context.return_value = state["flow_stack"][0]
    mock_runtime.context["step_manager"].is_step_complete.return_value = False

    # Act
    import sys
    from unittest.mock import patch

    mock_dspy = MagicMock()
    mock_dspy.History.return_value = MagicMock()

    with patch.dict(sys.modules, {"dspy": mock_dspy}):
        result = await validate_slot_node(state, mock_runtime)

    # Assert
    assert "flow_slots" not in result
    assert result["conversation_state"] == "idle"
