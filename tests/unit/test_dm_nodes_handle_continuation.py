"""Unit tests for continuation pattern handling.

Continuation is handled through routing to collect_next_slot or other nodes,
not through a dedicated handle_continuation_node.

Design Reference: docs/design/10-dsl-specification/06-patterns.md
Pattern: "Continuation: General continuation of flow"
"""

from unittest.mock import MagicMock

import pytest

from soni.dm.routing import route_after_understand
from soni.du.models import MessageType


@pytest.mark.asyncio
async def test_handle_continuation_advances_flow(create_state_with_flow, mock_runtime):
    """
    Continuation advances to next unfilled slot or action.

    When user provides continuation message and there's an active flow,
    system should advance to next step.
    """
    # Arrange
    state = create_state_with_flow("book_flight")
    state["conversation_state"] = "waiting_for_slot"
    state["waiting_for_slot"] = "origin"
    state["nlu_result"] = {
        "message_type": MessageType.CONTINUATION.value,
        "command": "continue",
    }

    # Mock step_manager to advance to next slot
    from soni.core.config import FlowConfig, StepConfig, TriggerConfig

    flow_config = FlowConfig(
        description="Book flight",
        trigger=TriggerConfig(intents=[]),
        steps=[
            StepConfig(step="collect_origin", type="collect", slot="origin"),
            StepConfig(step="collect_destination", type="collect", slot="destination"),
        ],
    )

    mock_runtime.context["step_manager"].config = MagicMock()
    mock_runtime.context["step_manager"].config.flows = {"book_flight": flow_config}
    mock_runtime.context["step_manager"].get_current_step_config.return_value = StepConfig(
        step="collect_origin", type="collect", slot="origin"
    )
    mock_runtime.context["step_manager"].get_next_required_slot.return_value = "destination"
    mock_runtime.context["step_manager"].advance_to_next_step.return_value = {
        "waiting_for_slot": "destination",
        "conversation_state": "waiting_for_slot",
        "flow_stack": state["flow_stack"],
    }

    # Act - Continuation routes to collect_next_slot
    route_result = route_after_understand(state)

    # Assert
    # Should route to collect_next_slot when there's an active flow
    assert route_result == "collect_next_slot"


@pytest.mark.asyncio
async def test_handle_continuation_with_no_active_flow(mock_runtime):
    """
    Continuation when no active flow triggers intent detection.

    When user provides continuation but no active flow exists,
    system should treat it as new intent.
    """
    from soni.core.state import create_empty_state

    # Arrange
    state = create_empty_state()
    state["conversation_state"] = "idle"
    state["flow_stack"] = []
    state["nlu_result"] = {
        "message_type": MessageType.CONTINUATION.value,
        "command": "book_flight",  # NLU detects intent
    }

    # Act - Continuation with no flow but command routes to intent_change
    route_result = route_after_understand(state)

    # Assert
    # Should trigger new flow or intent detection
    assert route_result == "handle_intent_change"


@pytest.mark.asyncio
async def test_handle_continuation_no_flow_no_command():
    """Continuation with no flow and no command routes to generate_response."""
    from soni.core.state import create_empty_state

    # Arrange
    state = create_empty_state()
    state["flow_stack"] = []
    state["nlu_result"] = {
        "message_type": MessageType.CONTINUATION.value,
        "command": None,  # No command
    }

    # Act
    route_result = route_after_understand(state)

    # Assert
    assert route_result == "generate_response"


@pytest.mark.asyncio
async def test_handle_continuation_all_slots_filled(create_state_with_flow, mock_runtime):
    """Continuation when all slots are filled should advance to action/confirm."""
    from soni.core.config import FlowConfig, StepConfig, TriggerConfig

    # Arrange
    state = create_state_with_flow("book_flight")
    state["flow_slots"] = {
        "flow_1": {
            "origin": "Madrid",
            "destination": "Barcelona",
            "date": "2024-12-25",
        }
    }
    state["conversation_state"] = "waiting_for_slot"
    state["nlu_result"] = {
        "message_type": MessageType.CONTINUATION.value,
        "command": "continue",
    }

    flow_config = FlowConfig(
        description="Book flight",
        trigger=TriggerConfig(intents=[]),
        steps=[
            StepConfig(step="collect_origin", type="collect", slot="origin"),
            StepConfig(step="collect_destination", type="collect", slot="destination"),
            StepConfig(step="collect_date", type="collect", slot="date"),
            StepConfig(step="confirm_booking", type="confirm", message="Confirm?"),
        ],
    )

    mock_runtime.context["step_manager"].config = MagicMock()
    mock_runtime.context["step_manager"].config.flows = {"book_flight": flow_config}
    mock_runtime.context["step_manager"].get_current_step_config.return_value = StepConfig(
        step="collect_date", type="collect", slot="date"
    )
    # All slots filled - no next slot
    mock_runtime.context["step_manager"].get_next_required_slot.return_value = None
    mock_runtime.context["step_manager"].advance_to_next_step.return_value = {
        "conversation_state": "ready_for_confirmation",
        "current_step": "confirm_booking",
        "flow_stack": state["flow_stack"],
    }

    # Act
    route_result = route_after_understand(state)

    # Assert
    # Should route to collect_next_slot, which will then advance to confirmation
    assert route_result == "collect_next_slot"
