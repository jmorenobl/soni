"""Integration tests for digression flow.

Tests the complete flow: digression → slot collection → next slot prompt.
"""

from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from soni.core.config import FlowConfig, StepConfig, TriggerConfig
from soni.core.state import create_empty_state
from soni.dm.nodes.collect_next_slot import collect_next_slot_node
from soni.dm.nodes.generate_response import generate_response_node
from soni.dm.nodes.handle_digression import handle_digression_node
from soni.dm.nodes.validate_slot import validate_slot_node
from soni.du.models import MessageType, NLUOutput, SlotValue


@pytest.fixture
def mock_runtime_with_flow():
    """Create mock runtime with flow configuration."""
    runtime = MagicMock()

    # Mock flow_manager
    mock_flow_manager = MagicMock()
    mock_flow_manager.get_active_context.return_value = {
        "flow_id": "book_flight_123",
        "flow_name": "book_flight",
        "current_step": "collect_destination",
        "flow_state": "active",
    }

    # Mock step_manager with flow config
    mock_step_manager = MagicMock()
    flow_config = FlowConfig(
        description="Book flight",
        trigger=TriggerConfig(intents=[]),
        steps=[
            StepConfig(step="collect_origin", type="collect", slot="origin"),
            StepConfig(step="collect_destination", type="collect", slot="destination"),
            StepConfig(step="collect_date", type="collect", slot="departure_date"),
        ],
    )
    mock_step_manager.config = MagicMock()
    mock_step_manager.config.flows = {"book_flight": flow_config}

    # Mock get_current_step_config
    destination_step_config = StepConfig(
        step="collect_destination", type="collect", slot="destination"
    )
    date_step_config = StepConfig(step="collect_date", type="collect", slot="departure_date")
    mock_step_manager.get_current_step_config.return_value = destination_step_config
    mock_step_manager.get_next_step_config.return_value = date_step_config
    mock_step_manager.get_next_required_slot.return_value = "departure_date"
    mock_step_manager.advance_to_next_step.return_value = {
        "flow_stack": [],
        "conversation_state": "waiting_for_slot",
        "current_step": "collect_date",
    }

    # Mock normalizer
    mock_normalizer = AsyncMock()
    mock_normalizer.normalize_slot.return_value = "Miami"

    # Mock config with slot prompts
    mock_config = MagicMock()
    mock_config.flows = {"book_flight": flow_config}
    mock_config.slots = {
        "destination": MagicMock(prompt="Where would you like to go?"),
        "departure_date": MagicMock(prompt="When would you like to depart?"),
    }

    runtime.context = {
        "flow_manager": mock_flow_manager,
        "step_manager": mock_step_manager,
        "normalizer": mock_normalizer,
        "config": mock_config,
    }

    return runtime


@pytest.mark.asyncio
async def test_digression_then_slot_collection_shows_next_prompt(mock_runtime_with_flow):
    """
    Test complete flow: digression → slot collection → next slot prompt.

    Scenario:
    1. User is waiting for destination
    2. User asks a question (digression)
    3. System responds and re-prompts for destination
    4. User provides destination
    5. System should show prompt for departure_date (not digression message)
    """
    # Step 1: User is waiting for destination
    state = create_empty_state()
    state["flow_stack"] = [
        {
            "flow_id": "book_flight_123",
            "flow_name": "book_flight",
            "current_step": "collect_destination",
            "flow_state": "active",
            "outputs": {},
            "started_at": 0.0,
            "paused_at": None,
            "completed_at": None,
            "context": None,
        }
    ]
    state["flow_slots"] = {"book_flight_123": {"origin": "San Francisco"}}
    state["waiting_for_slot"] = "destination"
    state["current_step"] = "collect_destination"
    state["conversation_state"] = "waiting_for_slot"

    # Step 2: User asks a question (digression)
    state["nlu_result"] = NLUOutput(
        message_type=MessageType.DIGRESSION,
        command="airports",
        confidence=0.9,
    ).model_dump()
    state["user_message"] = "What airports do you support?"

    # Step 3: Handle digression
    digression_result = await handle_digression_node(state, mock_runtime_with_flow)
    state.update(digression_result)

    # Verify digression preserved waiting_for_slot and re-prompts
    assert state["waiting_for_slot"] == "destination"
    assert state["conversation_state"] == "waiting_for_slot"
    assert "Where would you like to go?" in state["last_response"]
    assert (
        "airports" in state["last_response"].lower() or "question" in state["last_response"].lower()
    )

    # Step 4: Generate response (simulates going through generate_response node)
    response_result = await generate_response_node(state, mock_runtime_with_flow)
    state.update(response_result)

    # Verify response preserves waiting_for_slot
    assert state["waiting_for_slot"] == "destination"
    assert state["conversation_state"] == "waiting_for_slot"
    assert "Where would you like to go?" in state["last_response"]

    # Step 5: User provides destination
    state["user_message"] = "Miami"
    state["nlu_result"] = NLUOutput(
        message_type=MessageType.SLOT_VALUE,
        command=None,
        slots=[SlotValue(name="destination", value="Miami", confidence=0.95)],
        confidence=0.95,
    ).model_dump()

    # Step 6: Validate slot
    validate_result = await validate_slot_node(state, mock_runtime_with_flow)
    state.update(validate_result)

    # Verify destination was saved
    assert state["flow_slots"]["book_flight_123"]["destination"] == "Miami"
    assert state["conversation_state"] == "waiting_for_slot"

    # Step 7: Collect next slot (should show prompt for departure_date)
    # Mock get_slot_config for departure_date
    def get_slot_config(context, slot_name):
        if slot_name == "departure_date":
            return MagicMock(prompt="When would you like to depart?")
        elif slot_name == "destination":
            return MagicMock(prompt="Where would you like to go?")
        raise KeyError(f"Slot {slot_name} not found")

    with patch("soni.core.state.get_slot_config", side_effect=get_slot_config):
        with patch("langgraph.types.interrupt", return_value=""):
            collect_result = await collect_next_slot_node(state, mock_runtime_with_flow)
            state.update(collect_result)

    # CRITICAL: Should show prompt for departure_date, NOT the digression message
    assert "departure_date" in state.get("waiting_for_slot", "")
    assert "When would you like to depart?" in state["last_response"]
    # Should NOT contain the digression message
    assert "airports" not in state["last_response"].lower()
    assert (
        "question" not in state["last_response"].lower()
        or "When would you like to depart?" in state["last_response"]
    )


@pytest.mark.asyncio
async def test_collect_next_slot_sets_last_response_before_interrupt(mock_runtime_with_flow):
    """
    Test that collect_next_slot sets last_response before interrupt().

    This ensures that if the flow goes to generate_response, it has the correct prompt.
    """
    # Arrange: State after validating a slot, ready to collect next slot
    state = create_empty_state()
    state["flow_stack"] = [
        {
            "flow_id": "book_flight_123",
            "flow_name": "book_flight",
            "current_step": "collect_destination",
            "flow_state": "active",
            "outputs": {},
            "started_at": 0.0,
            "paused_at": None,
            "completed_at": None,
            "context": None,
        }
    ]
    state["flow_slots"] = {"book_flight_123": {"origin": "San Francisco", "destination": "Miami"}}
    state["conversation_state"] = "waiting_for_slot"
    state["current_step"] = "collect_destination"

    # Mock step_manager to return date step config
    date_step_config = StepConfig(step="collect_date", type="collect", slot="departure_date")
    mock_runtime_with_flow.context[
        "step_manager"
    ].get_current_step_config.return_value = date_step_config
    mock_runtime_with_flow.context[
        "step_manager"
    ].get_next_required_slot.return_value = "departure_date"

    # Mock get_slot_config
    def get_slot_config(context, slot_name):
        if slot_name == "departure_date":
            return MagicMock(prompt="When would you like to depart?")
        raise KeyError(f"Slot {slot_name} not found")

    interrupt_calls = []

    def mock_interrupt(prompt):
        interrupt_calls.append(prompt)
        return ""  # Simulate no user response yet

    with patch("soni.core.state.get_slot_config", side_effect=get_slot_config):
        with patch("langgraph.types.interrupt", mock_interrupt):
            # Act
            result = await collect_next_slot_node(state, mock_runtime_with_flow)

            # Assert
            # CRITICAL: last_response should be set BEFORE interrupt() is called
            assert "last_response" in result
            assert result["last_response"] == "When would you like to depart?"
            assert result["waiting_for_slot"] == "departure_date"
            assert result["conversation_state"] == "waiting_for_slot"
            # Verify interrupt was called with the prompt
            assert len(interrupt_calls) > 0
            assert interrupt_calls[0] == "When would you like to depart?"
