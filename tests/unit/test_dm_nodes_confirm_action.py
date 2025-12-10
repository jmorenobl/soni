"""Unit tests for confirm_action node.

All tests use mocked state and runtime for determinism.
"""

from unittest.mock import MagicMock, patch

import pytest

from soni.core.state import create_empty_state
from soni.dm.nodes.confirm_action import confirm_action_node


@pytest.fixture
def mock_runtime():
    """Create mock runtime for testing."""
    runtime = MagicMock()
    runtime.context = {
        "flow_manager": MagicMock(),
        "step_manager": MagicMock(),
        "config": MagicMock(),
    }
    return runtime


@pytest.fixture
def create_state_with_flow():
    """Factory fixture to create state with active flow."""

    def _create(flow_name: str, current_step: str | None = None, **kwargs):
        state = create_empty_state()
        state["flow_stack"] = [
            {
                "flow_id": f"{flow_name}_123",
                "flow_name": flow_name,
                "flow_state": "active",
                "current_step": current_step,
                "outputs": {},
                "started_at": 0.0,
                "paused_at": None,
                "completed_at": None,
                "context": None,
            }
        ]
        state["flow_slots"] = {f"{flow_name}_123": kwargs.get("slots", {})}
        if "conversation_state" in kwargs:
            state["conversation_state"] = kwargs["conversation_state"]
        if "metadata" in kwargs:
            state["metadata"] = kwargs["metadata"]
        return state

    return _create


@pytest.fixture
def create_state_with_slots():
    """Factory fixture to create state with slots."""

    def _create(flow_name: str, slots: dict, current_step: str | None = None, **kwargs):
        state = create_empty_state()
        flow_id = f"{flow_name}_123"
        state["flow_stack"] = [
            {
                "flow_id": flow_id,
                "flow_name": flow_name,
                "flow_state": "active",
                "current_step": current_step,
                "outputs": {},
                "started_at": 0.0,
                "paused_at": None,
                "completed_at": None,
                "context": None,
            }
        ]
        state["flow_slots"] = {flow_id: slots.copy()}
        if "conversation_state" in kwargs:
            state["conversation_state"] = kwargs["conversation_state"]
        if "metadata" in kwargs:
            state["metadata"] = kwargs["metadata"]
        return state

    return _create


@pytest.mark.asyncio
async def test_confirm_action_builds_confirmation_message(create_state_with_slots, mock_runtime):
    """Test that confirm_action builds confirmation message."""
    # Arrange
    state = create_state_with_slots(
        "book_flight",
        slots={"origin": "Madrid", "destination": "Barcelona", "date": "2025-12-25"},
        current_step="confirm_booking",
        conversation_state="ready_for_confirmation",
    )

    mock_step_config = MagicMock()
    mock_step_config.step = "confirm_booking"
    mock_step_config.type = "confirm"
    mock_step_config.message = "You want to fly from {origin} to {destination} on {date}, correct?"
    mock_runtime.context["step_manager"].get_current_step_config.return_value = mock_step_config

    # Mock interrupt to avoid RuntimeError
    with patch("langgraph.types.interrupt", return_value="yes"):
        # Act
        result = await confirm_action_node(state, mock_runtime)

        # Assert
        assert "last_response" in result
        assert "Madrid" in result["last_response"]
        assert "Barcelona" in result["last_response"]
        assert "2025-12-25" in result["last_response"]


@pytest.mark.asyncio
async def test_confirm_action_interpolates_slots(create_state_with_slots, mock_runtime):
    """Test that confirm_action interpolates slots correctly."""
    # Arrange
    state = create_state_with_slots(
        "book_flight",
        slots={"origin": "Madrid", "destination": "Barcelona"},
        current_step="confirm_booking",
    )

    mock_step_config = MagicMock()
    mock_step_config.step = "confirm_booking"
    mock_step_config.type = "confirm"
    mock_step_config.message = "Confirm: {origin} → {destination}?"
    mock_runtime.context["step_manager"].get_current_step_config.return_value = mock_step_config

    # Mock interrupt
    with patch("langgraph.types.interrupt", return_value="yes"):
        # Act
        result = await confirm_action_node(state, mock_runtime)

        # Assert
        assert "last_response" in result
        assert "Madrid" in result["last_response"]
        assert "Barcelona" in result["last_response"]
        assert "{origin}" not in result["last_response"]
        assert "{destination}" not in result["last_response"]


@pytest.mark.asyncio
async def test_confirm_action_missing_slot_in_interpolation(create_state_with_slots, mock_runtime):
    """Test that confirm_action handles missing slots in template."""
    # Arrange
    state = create_state_with_slots(
        "book_flight",
        slots={"origin": "Madrid"},  # Missing destination
        current_step="confirm_booking",
    )

    mock_step_config = MagicMock()
    mock_step_config.step = "confirm_booking"
    mock_step_config.type = "confirm"
    mock_step_config.message = "From {origin} to {destination}?"
    mock_runtime.context["step_manager"].get_current_step_config.return_value = mock_step_config

    # Mock interrupt
    with patch("langgraph.types.interrupt", return_value="yes"):
        # Act
        result = await confirm_action_node(state, mock_runtime)

        # Assert - Placeholder may remain or use default
        assert "last_response" in result
        assert "Madrid" in result["last_response"]


@pytest.mark.asyncio
async def test_confirm_action_no_slots_interpolated(create_state_with_flow, mock_runtime):
    """Test that confirm_action works without slot interpolation."""
    # Arrange
    state = create_state_with_flow("simple_flow", current_step="confirm_action")

    mock_step_config = MagicMock()
    mock_step_config.step = "confirm_action"
    mock_step_config.type = "confirm"
    mock_step_config.message = "Are you sure you want to proceed?"
    mock_runtime.context["step_manager"].get_current_step_config.return_value = mock_step_config

    # Mock interrupt
    with patch("langgraph.types.interrupt", return_value="yes"):
        # Act
        result = await confirm_action_node(state, mock_runtime)

        # Assert
        assert "last_response" in result
        assert "Are you sure you want to proceed?" in result["last_response"]


@pytest.mark.asyncio
async def test_confirm_action_first_execution_interrupts(create_state_with_slots, mock_runtime):
    """Test that first execution of confirm_action interrupts flow."""
    # Arrange
    state = create_state_with_slots(
        "book_flight",
        slots={"origin": "Madrid", "destination": "Barcelona"},
        current_step="confirm_booking",
        metadata={},  # No _confirmation_processed flag
    )

    mock_step_config = MagicMock()
    mock_step_config.step = "confirm_booking"
    mock_step_config.type = "confirm"
    mock_step_config.message = "Confirm?"
    mock_runtime.context["step_manager"].get_current_step_config.return_value = mock_step_config

    # Mock interrupt - first execution
    with patch("langgraph.types.interrupt", return_value="yes"):
        # Act
        result = await confirm_action_node(state, mock_runtime)

        # Assert - First execution should generate response
        assert "last_response" in result
        assert result["conversation_state"] == "confirming"
        assert result["user_message"] == "yes"


@pytest.mark.asyncio
async def test_confirm_action_re_execution_after_resume(create_state_with_slots, mock_runtime):
    """Test that re-execution after resume passes through."""
    # Arrange
    state = create_state_with_slots(
        "book_flight",
        slots={"origin": "Madrid"},
        current_step="confirm_booking",
        metadata={"_confirmation_processed": True},  # Already processed
    )
    state["user_message"] = "yes"
    state["conversation_state"] = "confirming"
    state["last_response"] = "Confirm?"

    mock_step_config = MagicMock()
    mock_step_config.step = "confirm_booking"
    mock_step_config.type = "confirm"
    mock_step_config.message = "Confirm?"
    mock_runtime.context["step_manager"].get_current_step_config.return_value = mock_step_config

    # Act
    result = await confirm_action_node(state, mock_runtime)

    # Assert - Re-execution should preserve existing response
    assert result["conversation_state"] == "confirming"
    assert result["last_response"] == "Confirm?"


@pytest.mark.asyncio
async def test_confirm_action_preserves_existing_response(create_state_with_slots, mock_runtime):
    """Test that confirm_action preserves existing response in re-execution."""
    # Arrange
    state = create_state_with_slots(
        "book_flight",
        slots={"origin": "Madrid"},
        current_step="confirm_booking",
        metadata={"_confirmation_processed": True},
    )
    state["user_message"] = "yes"
    state["conversation_state"] = "confirming"
    state["last_response"] = "Previous response"

    mock_step_config = MagicMock()
    mock_step_config.step = "confirm_booking"
    mock_step_config.type = "confirm"
    mock_step_config.message = "New prompt"
    mock_runtime.context["step_manager"].get_current_step_config.return_value = mock_step_config

    # Act
    result = await confirm_action_node(state, mock_runtime)

    # Assert - Should preserve existing last_response
    assert result["last_response"] == "Previous response"


@pytest.mark.asyncio
async def test_confirm_action_no_active_flow(mock_runtime):
    """Test that confirm_action returns error when no active flow."""
    # Arrange
    state = create_empty_state()
    mock_runtime.context["flow_manager"].get_active_context.return_value = None

    # Act
    result = await confirm_action_node(state, mock_runtime)

    # Assert - Should return error state
    assert result["conversation_state"] == "error"


@pytest.mark.asyncio
async def test_confirm_action_not_confirm_step(create_state_with_flow, mock_runtime):
    """Test that confirm_action handles step that is not confirm type."""
    # Arrange
    state = create_state_with_flow("book_flight", current_step="collect_origin")

    mock_step_config = MagicMock()
    mock_step_config.step = "collect_origin"
    mock_step_config.type = "collect"  # Not confirm
    mock_step_config.slot = "origin"
    mock_runtime.context["step_manager"].get_current_step_config.return_value = mock_step_config

    # Act
    result = await confirm_action_node(state, mock_runtime)

    # Assert - Should return error
    assert result["conversation_state"] == "error"


@pytest.mark.asyncio
async def test_confirm_action_no_step_config(create_state_with_flow, mock_runtime):
    """Test that confirm_action returns error when step config is missing."""
    # Arrange
    state = create_state_with_flow("book_flight", current_step="confirm_booking")

    mock_runtime.context["step_manager"].get_current_step_config.return_value = None

    # Act
    result = await confirm_action_node(state, mock_runtime)

    # Assert - Should return error state
    assert result["conversation_state"] == "error"


@pytest.mark.asyncio
async def test_confirm_action_no_message_template(create_state_with_slots, mock_runtime):
    """Test that confirm_action uses default message when no template."""
    # Arrange
    state = create_state_with_slots(
        "book_flight",
        slots={"origin": "Madrid", "destination": "Barcelona"},
        current_step="confirm_booking",
    )

    mock_step_config = MagicMock()
    mock_step_config.step = "confirm_booking"
    mock_step_config.type = "confirm"
    mock_step_config.message = None  # No message template
    mock_runtime.context["step_manager"].get_current_step_config.return_value = mock_step_config

    # Mock interrupt
    with patch("langgraph.types.interrupt", return_value="yes"):
        # Act
        result = await confirm_action_node(state, mock_runtime)

        # Assert - Should use default message
        assert "last_response" in result
        assert "Let me confirm" in result["last_response"]
        assert "Is this correct?" in result["last_response"]


@pytest.mark.asyncio
async def test_confirm_action_first_re_execution_passes_through(
    create_state_with_slots, mock_runtime
):
    """Test that first re-execution passes through without interrupting."""
    # Arrange
    state = create_state_with_slots(
        "book_flight",
        slots={"origin": "Madrid"},
        current_step="confirm_booking",
        metadata={},  # No _confirmation_processed flag yet
    )
    state["user_message"] = "yes"
    state["conversation_state"] = "confirming"

    mock_step_config = MagicMock()
    mock_step_config.step = "confirm_booking"
    mock_step_config.type = "confirm"
    mock_step_config.message = "Confirm?"
    mock_runtime.context["step_manager"].get_current_step_config.return_value = mock_step_config

    # Act - Re-execution after interrupt
    result = await confirm_action_node(state, mock_runtime)

    # Assert - Should pass through without setting last_response
    assert result["conversation_state"] == "confirming"
    assert "last_response" not in result or result.get("last_response") is None
