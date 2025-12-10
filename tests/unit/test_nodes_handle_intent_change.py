"""Tests for handle_intent_change node.

Design Reference: docs/design/10-dsl-specification/06-patterns.md:169-200
Pattern: "Interruption: New intent/flow → Push to stack, pause current flow"
"""

from unittest.mock import MagicMock

import pytest

from soni.core.state import create_empty_state
from soni.dm.nodes.handle_intent_change import (
    _extract_slots_from_nlu,
    handle_intent_change_node,
)


@pytest.mark.asyncio
async def test_handle_intent_change_rejects_unknown_flow():
    """Test that handle_intent_change rejects unknown flow names."""
    # Arrange
    state = create_empty_state()
    state["nlu_result"] = {
        "command": "unknown_flow",
        "message_type": "interruption",
    }
    state["flow_stack"] = []
    state["flow_slots"] = {}

    mock_flow_manager = MagicMock()
    mock_flow_manager.get_active_context.return_value = None

    mock_config = MagicMock()
    mock_config.flows = {"book_flight": {}, "cancel_booking": {}}

    mock_runtime = MagicMock()
    mock_runtime.context = {
        "flow_manager": mock_flow_manager,
        "config": mock_config,
    }

    # Act
    result = await handle_intent_change_node(state, mock_runtime)

    # Assert
    assert result["conversation_state"] == "idle"
    assert "I don't know how to" in result["last_response"]
    assert "unknown_flow" in result["last_response"]
    # Should not have pushed flow
    mock_flow_manager.push_flow.assert_not_called()


@pytest.mark.asyncio
async def test_handle_intent_change_handles_missing_command():
    """Test that handle_intent_change handles missing command gracefully."""
    # Arrange
    state = create_empty_state()
    state["nlu_result"] = {
        "message_type": "interruption",
        # No command field
    }
    state["flow_stack"] = []
    state["flow_slots"] = {}

    mock_flow_manager = MagicMock()
    mock_config = MagicMock()
    mock_config.flows = {"book_flight": {}}

    mock_runtime = MagicMock()
    mock_runtime.context = {
        "flow_manager": mock_flow_manager,
        "config": mock_config,
    }

    # Act
    result = await handle_intent_change_node(state, mock_runtime)

    # Assert
    assert result["conversation_state"] == "idle"
    assert "I didn't understand" in result["last_response"]
    # Should not have pushed flow
    mock_flow_manager.push_flow.assert_not_called()


@pytest.mark.asyncio
async def test_handle_intent_change_starts_valid_flow():
    """Test that handle_intent_change starts a valid flow."""
    # Arrange
    state = create_empty_state()
    state["nlu_result"] = {
        "command": "book_flight",
        "message_type": "interruption",
    }
    state["flow_stack"] = []
    state["flow_slots"] = {}

    mock_flow_manager = MagicMock()
    # No active flow - should push new flow
    mock_flow_manager.get_active_context.return_value = None
    mock_flow_manager.push_flow.return_value = "flow_1"

    mock_step_manager = MagicMock()
    mock_step_config = MagicMock()
    mock_step_config.type = "collect"
    mock_step_config.slot = "origin"
    mock_step_manager.get_current_step_config.return_value = mock_step_config
    # Mock advance_through_completed_steps to return waiting_for_slot state
    mock_step_manager.advance_through_completed_steps.return_value = {
        "conversation_state": "waiting_for_slot",
        "waiting_for_slot": "origin",
        "current_prompted_slot": "origin",
    }

    mock_config = MagicMock()
    mock_config.flows = {"book_flight": {}}

    # Mock activate_flow_by_intent to return "book_flight"
    from unittest.mock import patch

    # Mock push_flow to modify state in place
    def mock_push_flow(state, flow_name, inputs, reason):
        state["flow_stack"] = [
            {
                "flow_id": "flow_1",
                "flow_name": flow_name,
                "flow_state": "active",
                "current_step": "collect_origin",
                "outputs": {},
                "started_at": 0.0,
                "paused_at": None,
                "completed_at": None,
                "context": None,
            }
        ]
        state["flow_slots"] = {"flow_1": {}}
        return "flow_1"

    mock_flow_manager.push_flow.side_effect = mock_push_flow

    # After push_flow, get_active_context should return the new flow
    def get_active_context_side_effect(state):
        if state.get("flow_stack"):
            return {
                "flow_id": "flow_1",
                "flow_name": "book_flight",
                "current_step": "collect_origin",
            }
        return None

    mock_flow_manager.get_active_context.side_effect = get_active_context_side_effect

    mock_runtime = MagicMock()
    mock_runtime.context = {
        "flow_manager": mock_flow_manager,
        "config": mock_config,
        "step_manager": mock_step_manager,
    }

    # Act
    result = await handle_intent_change_node(state, mock_runtime)

    # Assert
    assert result["conversation_state"] == "waiting_for_slot"
    assert result["waiting_for_slot"] == "origin"
    # Should have pushed flow
    mock_flow_manager.push_flow.assert_called_once_with(
        state, flow_name="book_flight", inputs={}, reason="intent_change"
    )


# === _extract_slots_from_nlu ===


def test_extract_slots_from_nlu_dict_format():
    """Test _extract_slots_from_nlu with dict format."""
    nlu_result = {
        "slots": [
            {"name": "origin", "value": "New York"},
            {"name": "destination", "value": "Los Angeles"},
        ]
    }

    result = _extract_slots_from_nlu(nlu_result)

    assert result["origin"] == "New York"
    assert result["destination"] == "Los Angeles"


def test_extract_slots_from_nlu_slotvalue_format():
    """Test _extract_slots_from_nlu with SlotValue format."""
    from soni.du.models import SlotValue

    nlu_result = {
        "slots": [
            SlotValue(name="origin", value="Madrid", confidence=0.9),
            SlotValue(name="destination", value="Barcelona", confidence=0.9),
        ]
    }

    result = _extract_slots_from_nlu(nlu_result)

    assert result["origin"] == "Madrid"
    assert result["destination"] == "Barcelona"


def test_extract_slots_from_nlu_mixed_format():
    """Test _extract_slots_from_nlu with mixed formats."""
    from soni.du.models import SlotValue

    nlu_result = {
        "slots": [
            {"name": "origin", "value": "New York"},
            SlotValue(name="destination", value="Los Angeles", confidence=0.9),
        ]
    }

    result = _extract_slots_from_nlu(nlu_result)

    assert result["origin"] == "New York"
    assert result["destination"] == "Los Angeles"


def test_extract_slots_from_nlu_empty_list():
    """Test _extract_slots_from_nlu with empty slots list."""
    nlu_result = {"slots": []}

    result = _extract_slots_from_nlu(nlu_result)

    assert result == {}


def test_extract_slots_from_nlu_missing_name():
    """Test _extract_slots_from_nlu skips slots with missing name."""
    nlu_result = {
        "slots": [
            {"name": "origin", "value": "New York"},
            {"value": "Los Angeles"},  # Missing name
        ]
    }

    result = _extract_slots_from_nlu(nlu_result)

    assert "origin" in result
    assert "destination" not in result
    assert len(result) == 1


def test_extract_slots_from_nlu_missing_value():
    """Test _extract_slots_from_nlu skips slots with missing value."""
    nlu_result = {
        "slots": [
            {"name": "origin", "value": "New York"},
            {"name": "destination"},  # Missing value
        ]
    }

    result = _extract_slots_from_nlu(nlu_result)

    assert "origin" in result
    assert "destination" not in result
    assert len(result) == 1


def test_extract_slots_from_nlu_none_value():
    """Test _extract_slots_from_nlu skips slots with None value."""
    nlu_result = {
        "slots": [
            {"name": "origin", "value": "New York"},
            {"name": "destination", "value": None},
        ]
    }

    result = _extract_slots_from_nlu(nlu_result)

    assert "origin" in result
    assert "destination" not in result
    assert len(result) == 1


def test_extract_slots_from_nlu_no_slots_key():
    """Test _extract_slots_from_nlu handles missing slots key."""
    nlu_result = {}

    result = _extract_slots_from_nlu(nlu_result)

    assert result == {}


# === handle_intent_change_node additional cases ===


@pytest.mark.asyncio
async def test_handle_intent_change_no_nlu_result():
    """Test handle_intent_change_node returns error when no NLU result."""
    state = create_empty_state()
    state["nlu_result"] = None

    mock_runtime = MagicMock()
    mock_runtime.context = {
        "flow_manager": MagicMock(),
        "config": MagicMock(),
    }

    result = await handle_intent_change_node(state, mock_runtime)

    assert result["conversation_state"] == "error"


@pytest.mark.asyncio
async def test_handle_intent_change_command_not_flow_but_active_flow():
    """Test handle_intent_change_node when command is not a flow but flow is active."""
    state = create_empty_state()
    state["nlu_result"] = {
        "command": "not_a_flow",
        "message_type": "interruption",
    }
    state["flow_stack"] = [
        {
            "flow_id": "flow_1",
            "flow_name": "book_flight",
            "flow_state": "active",
            "current_step": "collect_origin",
            "outputs": {},
            "started_at": 0.0,
            "paused_at": None,
            "completed_at": None,
            "context": None,
        }
    ]

    mock_flow_manager = MagicMock()
    mock_flow_manager.get_active_context.return_value = {
        "flow_id": "flow_1",
        "flow_name": "book_flight",
    }

    mock_config = MagicMock()
    mock_config.flows = {"book_flight": {}}

    mock_runtime = MagicMock()
    mock_runtime.context = {
        "flow_manager": mock_flow_manager,
        "config": mock_config,
    }

    result = await handle_intent_change_node(state, mock_runtime)

    assert result["conversation_state"] == "idle"
    assert "I didn't understand" in result["last_response"]


@pytest.mark.asyncio
async def test_handle_intent_change_flow_already_active():
    """Test handle_intent_change_node when flow is already active."""
    state = create_empty_state()
    state["nlu_result"] = {
        "command": "book_flight",
        "message_type": "interruption",
    }
    state["flow_stack"] = [
        {
            "flow_id": "flow_1",
            "flow_name": "book_flight",
            "flow_state": "active",
            "current_step": "collect_origin",
            "outputs": {},
            "started_at": 0.0,
            "paused_at": None,
            "completed_at": None,
            "context": None,
        }
    ]
    state["flow_slots"] = {"flow_1": {"origin": "Madrid"}}

    mock_flow_manager = MagicMock()
    mock_flow_manager.get_active_context.return_value = {
        "flow_id": "flow_1",
        "flow_name": "book_flight",
        "current_step": "collect_origin",
    }

    mock_step_manager = MagicMock()
    mock_step_config = MagicMock()
    mock_step_config.type = "collect"
    mock_step_config.slot = "destination"
    mock_step_manager.get_current_step_config.return_value = mock_step_config

    mock_config = MagicMock()
    mock_config.flows = {"book_flight": {}}

    mock_runtime = MagicMock()
    mock_runtime.context = {
        "flow_manager": mock_flow_manager,
        "config": mock_config,
        "step_manager": mock_step_manager,
    }

    result = await handle_intent_change_node(state, mock_runtime)

    assert result["conversation_state"] == "waiting_for_slot"
    assert result["waiting_for_slot"] == "destination"
    # Should preserve existing slots
    assert "flow_slots" in result
    assert result["flow_slots"]["flow_1"]["origin"] == "Madrid"
    # Should not push flow again
    mock_flow_manager.push_flow.assert_not_called()


@pytest.mark.asyncio
async def test_handle_intent_change_extracts_multiple_slots():
    """Test handle_intent_change_node extracts and saves multiple slots."""
    state = create_empty_state()
    state["nlu_result"] = {
        "command": "book_flight",
        "message_type": "interruption",
        "slots": [
            {"name": "origin", "value": "New York"},
            {"name": "destination", "value": "Los Angeles"},
        ],
    }
    state["flow_stack"] = []
    state["flow_slots"] = {}

    mock_flow_manager = MagicMock()
    mock_flow_manager.get_active_context.return_value = None

    def mock_push_flow(state, flow_name, inputs, reason):
        state["flow_stack"] = [
            {
                "flow_id": "flow_1",
                "flow_name": flow_name,
                "flow_state": "active",
                "current_step": "collect_date",
                "outputs": {},
                "started_at": 0.0,
                "paused_at": None,
                "completed_at": None,
                "context": None,
            }
        ]
        state["flow_slots"] = {"flow_1": {}}
        return "flow_1"

    mock_flow_manager.push_flow.side_effect = mock_push_flow

    def get_active_context_side_effect(state):
        if state.get("flow_stack"):
            return {
                "flow_id": "flow_1",
                "flow_name": "book_flight",
                "current_step": "collect_date",
            }
        return None

    mock_flow_manager.get_active_context.side_effect = get_active_context_side_effect

    mock_step_manager = MagicMock()
    mock_step_config = MagicMock()
    mock_step_config.type = "collect"
    mock_step_config.slot = "date"
    mock_step_manager.get_current_step_config.return_value = mock_step_config
    mock_step_manager.advance_through_completed_steps.return_value = {
        "conversation_state": "waiting_for_slot",
        "waiting_for_slot": "date",
    }

    mock_config = MagicMock()
    mock_config.flows = {"book_flight": {}}

    mock_runtime = MagicMock()
    mock_runtime.context = {
        "flow_manager": mock_flow_manager,
        "config": mock_config,
        "step_manager": mock_step_manager,
    }

    result = await handle_intent_change_node(state, mock_runtime)

    # Should have saved slots
    assert "flow_slots" in result
    assert result["flow_slots"]["flow_1"]["origin"] == "New York"
    assert result["flow_slots"]["flow_1"]["destination"] == "Los Angeles"


@pytest.mark.asyncio
async def test_handle_intent_change_clears_user_message():
    """Test handle_intent_change_node clears user_message after processing."""
    state = create_empty_state()
    state["nlu_result"] = {
        "command": "book_flight",
        "message_type": "interruption",
    }
    state["user_message"] = "I want to book a flight"
    state["flow_stack"] = []
    state["flow_slots"] = {}

    mock_flow_manager = MagicMock()
    mock_flow_manager.get_active_context.return_value = None

    def mock_push_flow(state, flow_name, inputs, reason):
        state["flow_stack"] = [
            {
                "flow_id": "flow_1",
                "flow_name": flow_name,
                "flow_state": "active",
                "current_step": "collect_origin",
                "outputs": {},
                "started_at": 0.0,
                "paused_at": None,
                "completed_at": None,
                "context": None,
            }
        ]
        state["flow_slots"] = {"flow_1": {}}
        return "flow_1"

    mock_flow_manager.push_flow.side_effect = mock_push_flow

    def get_active_context_side_effect(state):
        if state.get("flow_stack"):
            return {
                "flow_id": "flow_1",
                "flow_name": "book_flight",
                "current_step": "collect_origin",
            }
        return None

    mock_flow_manager.get_active_context.side_effect = get_active_context_side_effect

    mock_step_manager = MagicMock()
    mock_step_config = MagicMock()
    mock_step_config.type = "collect"
    mock_step_config.slot = "origin"
    mock_step_manager.get_current_step_config.return_value = mock_step_config
    mock_step_manager.advance_through_completed_steps.return_value = {
        "conversation_state": "waiting_for_slot",
        "waiting_for_slot": "origin",
    }

    mock_config = MagicMock()
    mock_config.flows = {"book_flight": {}}

    mock_runtime = MagicMock()
    mock_runtime.context = {
        "flow_manager": mock_flow_manager,
        "config": mock_config,
        "step_manager": mock_step_manager,
    }

    result = await handle_intent_change_node(state, mock_runtime)

    # Should clear user_message
    assert result["user_message"] == ""


@pytest.mark.asyncio
async def test_handle_intent_change_no_updates_from_advance():
    """Test handle_intent_change_node sets defaults when advance returns no updates."""
    state = create_empty_state()
    state["nlu_result"] = {
        "command": "book_flight",
        "message_type": "interruption",
    }
    state["flow_stack"] = []
    state["flow_slots"] = {}

    mock_flow_manager = MagicMock()
    mock_flow_manager.get_active_context.return_value = None

    def mock_push_flow(state, flow_name, inputs, reason):
        state["flow_stack"] = [
            {
                "flow_id": "flow_1",
                "flow_name": flow_name,
                "flow_state": "active",
                "current_step": "collect_origin",
                "outputs": {},
                "started_at": 0.0,
                "paused_at": None,
                "completed_at": None,
                "context": None,
            }
        ]
        state["flow_slots"] = {"flow_1": {}}
        return "flow_1"

    mock_flow_manager.push_flow.side_effect = mock_push_flow

    def get_active_context_side_effect(state):
        if state.get("flow_stack"):
            return {
                "flow_id": "flow_1",
                "flow_name": "book_flight",
                "current_step": "collect_origin",
            }
        return None

    mock_flow_manager.get_active_context.side_effect = get_active_context_side_effect

    mock_step_manager = MagicMock()
    mock_step_config = MagicMock()
    mock_step_config.type = "collect"
    mock_step_config.slot = "origin"
    mock_step_manager.get_current_step_config.return_value = mock_step_config
    # Return empty dict (no conversation_state)
    mock_step_manager.advance_through_completed_steps.return_value = {}

    mock_config = MagicMock()
    mock_config.flows = {"book_flight": {}}

    mock_runtime = MagicMock()
    mock_runtime.context = {
        "flow_manager": mock_flow_manager,
        "config": mock_config,
        "step_manager": mock_step_manager,
    }

    result = await handle_intent_change_node(state, mock_runtime)

    # Should set defaults
    assert result["conversation_state"] == "waiting_for_slot"
    assert result["waiting_for_slot"] == "origin"


@pytest.mark.asyncio
async def test_handle_intent_change_stack_limit():
    """
    Intent change respects flow stack limit.

    When maximum stack depth is reached, system should handle according to strategy.
    """
    from soni.core.errors import FlowStackLimitError

    state = create_empty_state()
    # Create state with stack at max depth
    MAX_STACK_DEPTH = 3
    state["flow_stack"] = [
        {"flow_id": f"flow_{i}", "flow_name": f"flow_{i}", "flow_state": "paused"}
        for i in range(MAX_STACK_DEPTH)
    ]
    state["flow_stack"][-1]["flow_state"] = "active"  # Current flow

    # Try to push new flow
    state["nlu_result"] = {
        "message_type": "interruption",
        "intent": "check_weather",
        "command": "check_weather",
    }

    mock_flow_manager = MagicMock()
    # Mock flow_manager to enforce limit
    mock_flow_manager.get_active_context.return_value = state["flow_stack"][-1]
    mock_flow_manager.push_flow.side_effect = FlowStackLimitError(
        f"Flow stack depth limit ({MAX_STACK_DEPTH}) exceeded",
        current_depth=MAX_STACK_DEPTH,
        flow_name="check_weather",
    )

    mock_config = MagicMock()
    mock_config.flows = {"check_weather": {}}

    mock_runtime = MagicMock()
    mock_runtime.context = {
        "flow_manager": mock_flow_manager,
        "config": mock_config,
    }

    # Act - Should raise exception (current implementation doesn't catch it)
    # Test verifies that exception is raised when limit is exceeded
    with pytest.raises(FlowStackLimitError):
        await handle_intent_change_node(state, mock_runtime)


@pytest.mark.asyncio
async def test_handle_intent_change_stack_limit_strategy_cancel_oldest():
    """
    Stack limit strategy: cancel_oldest removes oldest flow.

    This test verifies that when stack limit is reached, the system
    can handle it by canceling the oldest flow (if strategy implemented).
    """
    from soni.core.config import FlowConfig, StepConfig, TriggerConfig

    MAX_STACK_DEPTH = 3
    state = create_empty_state()
    state["flow_stack"] = [
        {"flow_id": "flow_1", "flow_name": "oldest", "flow_state": "paused"},
        {"flow_id": "flow_2", "flow_name": "middle", "flow_state": "paused"},
        {"flow_id": "flow_3", "flow_name": "current", "flow_state": "active"},
    ]
    state["flow_slots"] = {
        "flow_1": {},
        "flow_2": {},
        "flow_3": {},
    }

    state["nlu_result"] = {
        "message_type": "interruption",
        "intent": "check_weather",
        "command": "check_weather",
    }

    # Mock strategy: cancel_oldest (simulate by popping oldest before pushing)
    def mock_push_flow(state, flow_name, inputs=None, reason=None):
        if len(state["flow_stack"]) >= MAX_STACK_DEPTH:
            # Cancel oldest (simulate strategy)
            state["flow_stack"].pop(0)
            if "flow_1" in state.get("flow_slots", {}):
                state["flow_slots"].pop("flow_1")
        # Push new flow
        new_flow_id = f"{flow_name}_new"
        new_flow = {
            "flow_id": new_flow_id,
            "flow_name": flow_name,
            "flow_state": "active",
            "current_step": "collect_city",  # Set current_step
            "outputs": {},
            "started_at": 0.0,
            "paused_at": None,
            "completed_at": None,
            "context": None,
        }
        state["flow_stack"].append(new_flow)
        state["flow_slots"][new_flow_id] = inputs or {}
        return new_flow_id

    mock_flow_manager = MagicMock()
    mock_flow_manager.get_active_context.side_effect = lambda s: (
        s["flow_stack"][-1] if s.get("flow_stack") else None
    )
    mock_flow_manager.push_flow.side_effect = mock_push_flow

    flow_config = FlowConfig(
        description="Check weather",
        trigger=TriggerConfig(intents=[]),
        steps=[StepConfig(step="collect_city", type="collect", slot="city")],
    )

    mock_config = MagicMock()
    mock_config.flows = {"check_weather": flow_config}

    mock_step_manager = MagicMock()
    mock_step_config = MagicMock()
    mock_step_config.type = "collect"
    mock_step_config.slot = "city"
    mock_step_manager.get_current_step_config.return_value = mock_step_config
    mock_step_manager.advance_through_completed_steps.return_value = {
        "conversation_state": "waiting_for_slot",
        "waiting_for_slot": "city",
        "flow_stack": state["flow_stack"],
    }

    mock_runtime = MagicMock()
    mock_runtime.context = {
        "flow_manager": mock_flow_manager,
        "config": mock_config,
        "step_manager": mock_step_manager,
    }

    # Act
    result = await handle_intent_change_node(state, mock_runtime)

    # Assert
    # Oldest flow removed
    assert len(result.get("flow_stack", state["flow_stack"])) == MAX_STACK_DEPTH
    # New flow added
    assert result.get("flow_stack", state["flow_stack"])[-1]["flow_name"] == "check_weather"
    # Oldest flow NOT in stack
    flow_names = [f["flow_name"] for f in result.get("flow_stack", state["flow_stack"])]
    assert "oldest" not in flow_names
