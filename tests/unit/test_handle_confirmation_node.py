"""Unit tests for handle_confirmation_node."""

from unittest.mock import MagicMock

import pytest

from soni.dm.nodes.handle_confirmation import handle_confirmation_node


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
        self.context["step_manager"] = mock_step_manager


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

    # Should treat as unclear and increment retries or handle gracefully
    assert result["conversation_state"] in ("confirming", "error", "understanding")


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

    # Should handle gracefully (treat as digression or re-prompt)
    assert result["conversation_state"] in ("confirming", "understanding")
