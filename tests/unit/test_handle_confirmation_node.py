"""Unit tests for handle_confirmation_node.

Design Reference: docs/design/10-dsl-specification/06-patterns.md:119-167
Pattern: "Confirmation: User confirms/denies → Proceed to action or allow modification"
"""

from unittest.mock import AsyncMock, MagicMock

import pytest

from soni.dm.nodes.handle_confirmation import (
    _get_response_template,
    _handle_correction_during_confirmation,
    handle_confirmation_node,
)


class MockRuntime:
    """Mock runtime for testing."""

    def __init__(self):
        self.context = {}
        # Create mock step_manager
        mock_step_manager = MagicMock()
        mock_step_manager.advance_to_next_step.return_value = {
            "flow_stack": [],
            "conversation_state": "ready_for_action",
        }
        mock_step_manager.get_current_step_config.return_value = MagicMock(
            message="Is this correct?"
        )
        self.context["step_manager"] = mock_step_manager

        # Mock normalizer
        self.context["normalizer"] = AsyncMock()
        self.context["normalizer"].normalize_slot.return_value = "normalized_value"

        # Mock flow_manager
        self.context["flow_manager"] = MagicMock()
        self.context["flow_manager"].get_active_context.return_value = {
            "flow_id": "flow_1",
            "flow_name": "test_flow",
        }

        # Mock config
        self.context["config"] = MagicMock()
        self.context["config"].responses = {}


@pytest.fixture
def mock_runtime():
    """Create mock runtime for testing."""
    return MockRuntime()


# === HAPPY PATH ===
@pytest.mark.asyncio
async def test_handle_confirmation_confirmed(mock_runtime):
    """Test handling user confirmation (yes)."""
    state = {
        "nlu_result": {
            "message_type": "confirmation",
            "confirmation_value": True,
        },
        "metadata": {},
    }

    result = await handle_confirmation_node(state, mock_runtime)

    assert result["conversation_state"] == "ready_for_action"
    assert "_confirmation_attempts" not in result.get("metadata", {})


@pytest.mark.asyncio
async def test_handle_confirmation_denied(mock_runtime):
    """Test handling user denial (no)."""
    state = {
        "nlu_result": {
            "message_type": "confirmation",
            "confirmation_value": False,
        },
        "metadata": {},
    }

    result = await handle_confirmation_node(state, mock_runtime)

    assert result["conversation_state"] == "understanding"
    assert "change" in result["last_response"].lower()
    assert "_confirmation_attempts" not in result.get("metadata", {})


# === UNCLEAR RESPONSE ===
@pytest.mark.asyncio
async def test_handle_confirmation_unclear_first_attempt(mock_runtime):
    """Test handling unclear response (first attempt)."""
    state = {
        "nlu_result": {
            "message_type": "confirmation",
            "confirmation_value": None,
        },
        "metadata": {},
    }

    result = await handle_confirmation_node(state, mock_runtime)

    assert result["conversation_state"] == "confirming"
    assert result["metadata"]["_confirmation_attempts"] == 1
    assert "didn't understand" in result["last_response"].lower()


# === RETRY COUNTER ===
@pytest.mark.asyncio
async def test_handle_confirmation_max_retries_exceeded(mock_runtime):
    """Test that exceeding max retries triggers error state."""
    state = {
        "nlu_result": {
            "message_type": "confirmation",
            "confirmation_value": None,
        },
        "metadata": {"_confirmation_attempts": 3},  # Already at max
    }

    result = await handle_confirmation_node(state, mock_runtime)

    assert result["conversation_state"] == "error"
    assert "_confirmation_attempts" not in result["metadata"]
    assert "trouble understanding" in result["last_response"].lower()


@pytest.mark.asyncio
async def test_handle_confirmation_retry_counter_cleared_on_success(mock_runtime):
    """Test that retry counter is cleared on successful confirmation."""
    state = {
        "nlu_result": {
            "message_type": "confirmation",
            "confirmation_value": True,
        },
        "metadata": {"_confirmation_attempts": 2},
    }

    result = await handle_confirmation_node(state, mock_runtime)

    assert result["conversation_state"] == "ready_for_action"
    assert "_confirmation_attempts" not in result["metadata"]


@pytest.mark.asyncio
async def test_handle_confirmation_retry_counter_increments(mock_runtime):
    """Test that retry counter increments on unclear responses."""
    state = {
        "nlu_result": {
            "message_type": "confirmation",
            "confirmation_value": None,
        },
        "metadata": {"_confirmation_attempts": 1},
    }

    result = await handle_confirmation_node(state, mock_runtime)

    assert result["conversation_state"] == "confirming"
    assert result["metadata"]["_confirmation_attempts"] == 2


# === EDGE CASES ===
@pytest.mark.asyncio
async def test_handle_confirmation_missing_nlu_result(mock_runtime):
    """Test handling when NLU result is missing."""
    state = {
        "nlu_result": None,
        "metadata": {},
    }

    result = await handle_confirmation_node(state, mock_runtime)

    # When nlu_result is None, message_type becomes None, which != "confirmation"
    # So it returns "understanding" (treats as digression)
    assert result["conversation_state"] == "understanding"


@pytest.mark.asyncio
async def test_handle_confirmation_wrong_message_type(mock_runtime):
    """Test handling when message_type is not confirmation."""
    state = {
        "nlu_result": {
            "message_type": "slot_value",  # Wrong type
            "confirmation_value": None,
        },
        "metadata": {},
    }

    result = await handle_confirmation_node(state, mock_runtime)

    # When message_type is not "confirmation", it treats as digression
    # and returns "understanding"
    assert result["conversation_state"] == "understanding"


# === CORRECTION DURING CONFIRMATION ===


@pytest.mark.asyncio
async def test_handle_confirmation_correction_during_confirmation(mock_runtime):
    """Test handling correction during confirmation."""
    from soni.core.state import create_empty_state

    state = create_empty_state()
    state["flow_stack"] = [
        {
            "flow_id": "flow_1",
            "flow_name": "test_flow",
            "flow_state": "active",
            "current_step": "confirm_booking",
            "outputs": {},
            "started_at": 0.0,
            "paused_at": None,
            "completed_at": None,
            "context": None,
        }
    ]
    state["flow_slots"] = {"flow_1": {"destination": "Madrid"}}
    state["conversation_state"] = "confirming"
    state["nlu_result"] = {
        "message_type": "correction",
        "slots": [{"name": "destination", "value": "Barcelona"}],
    }

    mock_runtime.context["normalizer"].normalize_slot.return_value = "BCN"

    result = await handle_confirmation_node(state, mock_runtime)

    assert result["conversation_state"] == "confirming"
    assert result["flow_slots"]["flow_1"]["destination"] == "BCN"
    assert "last_response" in result
    assert "destination" in result["last_response"].lower()


@pytest.mark.asyncio
async def test_handle_correction_during_confirmation_slotvalue_format(mock_runtime):
    """Test _handle_correction_during_confirmation with SlotValue format."""
    from soni.core.state import create_empty_state
    from soni.du.models import SlotValue

    state = create_empty_state()
    state["flow_stack"] = [
        {
            "flow_id": "flow_1",
            "flow_name": "test_flow",
            "flow_state": "active",
            "current_step": "confirm_booking",
            "outputs": {},
            "started_at": 0.0,
            "paused_at": None,
            "completed_at": None,
            "context": None,
        }
    ]
    state["flow_slots"] = {"flow_1": {"origin": "Madrid"}}
    nlu_result = {"slots": [SlotValue(name="origin", value="Barcelona", confidence=0.9)]}

    mock_runtime.context["normalizer"].normalize_slot.return_value = "BCN"

    result = await _handle_correction_during_confirmation(
        state, mock_runtime, nlu_result, "correction"
    )

    assert result["conversation_state"] == "confirming"
    assert result["flow_slots"]["flow_1"]["origin"] == "BCN"


@pytest.mark.asyncio
async def test_handle_correction_during_confirmation_dict_format(mock_runtime):
    """Test _handle_correction_during_confirmation with dict format."""
    from soni.core.state import create_empty_state

    state = create_empty_state()
    state["flow_stack"] = [
        {
            "flow_id": "flow_1",
            "flow_name": "test_flow",
            "flow_state": "active",
            "current_step": "confirm_booking",
            "outputs": {},
            "started_at": 0.0,
            "paused_at": None,
            "completed_at": None,
            "context": None,
        }
    ]
    state["flow_slots"] = {"flow_1": {"date": "2025-12-25"}}
    nlu_result = {"slots": [{"name": "date", "value": "2025-12-26"}]}

    mock_runtime.context["normalizer"].normalize_slot.return_value = "2025-12-26"

    result = await _handle_correction_during_confirmation(
        state, mock_runtime, nlu_result, "modification"
    )

    assert result["conversation_state"] == "confirming"
    assert result["flow_slots"]["flow_1"]["date"] == "2025-12-26"


@pytest.mark.asyncio
async def test_handle_correction_during_confirmation_no_slots(mock_runtime):
    """Test _handle_correction_during_confirmation with no slots."""
    from soni.core.state import create_empty_state

    state = create_empty_state()
    nlu_result = {"slots": []}

    result = await _handle_correction_during_confirmation(
        state, mock_runtime, nlu_result, "correction"
    )

    assert result["conversation_state"] == "confirming"


@pytest.mark.asyncio
async def test_handle_correction_during_confirmation_no_active_ctx(mock_runtime):
    """Test _handle_correction_during_confirmation with no active context."""
    from soni.core.state import create_empty_state

    state = create_empty_state()
    state["flow_stack"] = []
    nlu_result = {"slots": [{"name": "destination", "value": "Barcelona"}]}

    mock_runtime.context["flow_manager"].get_active_context.return_value = None

    result = await _handle_correction_during_confirmation(
        state, mock_runtime, nlu_result, "correction"
    )

    assert result["conversation_state"] == "error"


@pytest.mark.asyncio
async def test_handle_correction_during_confirmation_normalization_failure(mock_runtime):
    """Test _handle_correction_during_confirmation handles normalization failure."""
    from soni.core.state import create_empty_state

    state = create_empty_state()
    state["flow_stack"] = [
        {
            "flow_id": "flow_1",
            "flow_name": "test_flow",
            "flow_state": "active",
            "current_step": "confirm_booking",
            "outputs": {},
            "started_at": 0.0,
            "paused_at": None,
            "completed_at": None,
            "context": None,
        }
    ]
    nlu_result = {"slots": [{"name": "destination", "value": "Invalid"}]}

    mock_runtime.context["normalizer"].normalize_slot.side_effect = Exception("Normalization error")

    result = await _handle_correction_during_confirmation(
        state, mock_runtime, nlu_result, "correction"
    )

    assert result["conversation_state"] == "confirming"


@pytest.mark.asyncio
async def test_handle_confirmation_modification_during_confirmation(mock_runtime):
    """Test handling modification during confirmation."""
    from soni.core.state import create_empty_state

    state = create_empty_state()
    state["flow_stack"] = [
        {
            "flow_id": "flow_1",
            "flow_name": "test_flow",
            "flow_state": "active",
            "current_step": "confirm_booking",
            "outputs": {},
            "started_at": 0.0,
            "paused_at": None,
            "completed_at": None,
            "context": None,
        }
    ]
    state["flow_slots"] = {"flow_1": {"destination": "Madrid"}}
    state["conversation_state"] = "confirming"
    state["nlu_result"] = {
        "message_type": "modification",
        "slots": [{"name": "destination", "value": "Valencia"}],
    }

    mock_runtime.context["normalizer"].normalize_slot.return_value = "VLC"

    result = await handle_confirmation_node(state, mock_runtime)

    assert result["conversation_state"] == "confirming"
    assert result["flow_slots"]["flow_1"]["destination"] == "VLC"


@pytest.mark.asyncio
async def test_handle_confirmation_correction_regenerates_message(mock_runtime):
    """
    Correction during confirmation regenerates confirmation with new value.

    Design Reference: docs/design/10-dsl-specification/06-patterns.md:168-171
    Pattern: "Re-display confirmation with updated value"
    """
    from soni.core.state import create_empty_state

    # Arrange - State ready for confirmation with slots
    state = create_empty_state()
    state["flow_stack"] = [
        {
            "flow_id": "flow_1",
            "flow_name": "book_flight",
            "flow_state": "active",
            "current_step": "confirm_booking",
            "outputs": {},
            "started_at": 0.0,
            "paused_at": None,
            "completed_at": None,
            "context": None,
        }
    ]
    state["flow_slots"] = {
        "flow_1": {
            "origin": "Madrid",
            "destination": "Barcelona",
            "date": "2024-12-15",
        }
    }
    state["conversation_state"] = "confirming"

    # User corrects date during confirmation
    state["nlu_result"] = {
        "message_type": "correction",
        "slots": [{"name": "date", "value": "2024-12-20"}],
    }

    # Mock normalizer
    mock_runtime.context["normalizer"].normalize_slot.return_value = "2024-12-20"

    # Mock step_manager to return step config
    mock_step_config = MagicMock()
    mock_step_config.type = "confirm"
    mock_step_config.message = None  # Will use default confirmation message
    mock_runtime.context["step_manager"].get_current_step_config.return_value = mock_step_config

    # Act
    result = await handle_confirmation_node(state, mock_runtime)

    # Assert
    # Slot updated
    assert result["flow_slots"]["flow_1"]["date"] == "2024-12-20"
    # New confirmation message generated with updated value
    assert "2024-12-20" in result["last_response"]
    # OLD value NOT in message
    assert "2024-12-15" not in result["last_response"]
    # Still in confirming state
    assert result["conversation_state"] == "confirming"
    # Should include acknowledgment
    assert (
        "updated" in result["last_response"].lower() or "got it" in result["last_response"].lower()
    )


# === MAX RETRIES EDGE CASES ===


@pytest.mark.asyncio
async def test_handle_confirmation_denied_at_threshold(mock_runtime):
    """Test that denial at threshold (MAX-1 attempts) is treated as error."""
    # MAX_CONFIRMATION_ATTEMPTS = 3
    # When attempts >= MAX - 1 (i.e., >= 2), denial triggers error
    state = {
        "nlu_result": {
            "message_type": "confirmation",
            "confirmation_value": False,
        },
        "metadata": {"_confirmation_attempts": 2},  # At threshold (MAX - 1)
    }

    result = await handle_confirmation_node(state, mock_runtime)

    assert result["conversation_state"] == "error"
    assert "_confirmation_attempts" not in result["metadata"]


@pytest.mark.asyncio
async def test_handle_confirmation_unclear_before_max_attempts(mock_runtime):
    """Test unclear response before max attempts."""
    state = {
        "nlu_result": {
            "message_type": "confirmation",
            "confirmation_value": None,
        },
        "metadata": {"_confirmation_attempts": 1},
    }

    result = await handle_confirmation_node(state, mock_runtime)

    assert result["conversation_state"] == "confirming"
    assert result["metadata"]["_confirmation_attempts"] == 2


@pytest.mark.asyncio
async def test_handle_confirmation_unclear_at_max_attempts(mock_runtime):
    """Test unclear response at max attempts triggers error."""
    state = {
        "nlu_result": {
            "message_type": "confirmation",
            "confirmation_value": None,
        },
        "metadata": {"_confirmation_attempts": 2},  # One less than max
    }

    result = await handle_confirmation_node(state, mock_runtime)

    assert result["conversation_state"] == "error"
    assert "_confirmation_attempts" not in result["metadata"]


# === _get_response_template ===


def test_get_response_template_from_config_dict():
    """Test _get_response_template retrieves from config dict."""
    config = MagicMock()
    config.responses = {
        "correction_acknowledged": {"default": "Updated {slot_name} to {new_value}."}
    }

    result = _get_response_template(
        config, "correction_acknowledged", "Default message", slot_name="origin", new_value="NYC"
    )

    assert "origin" in result
    assert "NYC" in result
    assert "Updated" in result


def test_get_response_template_from_config_string():
    """Test _get_response_template retrieves from config string."""
    config = MagicMock()
    config.responses = {"modification_acknowledged": "Changed {slot_name} to {new_value}."}

    result = _get_response_template(
        config, "modification_acknowledged", "Default", slot_name="date", new_value="2025-12-25"
    )

    assert "date" in result
    assert "2025-12-25" in result
    assert "Changed" in result


def test_get_response_template_default_fallback():
    """Test _get_response_template uses default when not in config."""
    config = MagicMock()
    config.responses = {}

    result = _get_response_template(
        config,
        "unknown_template",
        "Default: {slot_name}={new_value}",
        slot_name="test",
        new_value="value",
    )

    assert result == "Default: test=value"


def test_get_response_template_interpolation():
    """Test _get_response_template interpolates multiple variables."""
    config = MagicMock()
    config.responses = {}

    result = _get_response_template(
        config,
        "test",
        "Slot {slot_name} is now {new_value} with {extra}",
        slot_name="origin",
        new_value="NYC",
        extra="details",
    )

    assert "origin" in result
    assert "NYC" in result
    assert "details" in result


def test_get_response_template_no_config_responses():
    """Test _get_response_template when config has no responses attribute."""
    config = MagicMock()
    del config.responses

    result = _get_response_template(config, "test", "Default {slot_name}", slot_name="test")

    assert result == "Default test"
