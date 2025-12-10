"""Tests for handle_intent_change node."""

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
