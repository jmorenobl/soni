"""Unit tests for collect_next_slot node.

All tests use mocked dependencies for determinism.
"""

from unittest.mock import MagicMock, patch

import pytest

from soni.core.config import StepConfig
from soni.core.state import create_empty_state
from soni.dm.nodes.collect_next_slot import collect_next_slot_node


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


@pytest.mark.asyncio
async def test_collect_next_slot_gets_slot_config(create_state_with_flow, mock_runtime):
    """Test that collect_next_slot gets slot configuration."""
    # Arrange
    state = create_state_with_flow(
        "book_flight", current_step="collect_origin", conversation_state="waiting_for_slot"
    )

    mock_step_config = MagicMock()
    mock_step_config.step = "collect_origin"
    mock_step_config.type = "collect"
    mock_step_config.slot = "origin"
    mock_runtime.context["step_manager"].get_current_step_config.return_value = mock_step_config
    mock_runtime.context["step_manager"].get_next_required_slot.return_value = "origin"

    mock_slot_config = MagicMock()
    mock_slot_config.prompt = "Where are you flying from?"
    mock_runtime.context["config"].slots = {"origin": mock_slot_config}

    def get_slot_config(context, slot_name):
        return context["config"].slots.get(slot_name)

    # Mock get_slot_config and interrupt
    with patch("soni.core.state.get_slot_config", get_slot_config):
        with patch("langgraph.types.interrupt", return_value="Madrid"):
            # Act
            result = await collect_next_slot_node(state, mock_runtime)

            # Assert
            assert "last_response" in result or "waiting_for_slot" in result
            assert result.get("waiting_for_slot") == "origin" or "origin" in str(result)


@pytest.mark.asyncio
async def test_collect_next_slot_no_active_flow(mock_runtime):
    """Test that collect_next_slot handles absence of active flow."""
    # Arrange
    state = create_empty_state()
    mock_runtime.context["flow_manager"].get_active_context.return_value = None

    # Act
    result = await collect_next_slot_node(state, mock_runtime)

    # Assert
    assert result["conversation_state"] == "idle"
    assert "last_response" in result


@pytest.mark.asyncio
async def test_collect_next_slot_no_current_step_advances(create_state_with_flow, mock_runtime):
    """Test that collect_next_slot advances if no current_step."""
    # Arrange
    state = create_state_with_flow("book_flight")
    state["flow_stack"][0]["current_step"] = None

    mock_next_step = StepConfig(step="collect_origin", type="collect", slot="origin")
    mock_runtime.context["step_manager"].get_current_step_config.return_value = None
    mock_runtime.context["step_manager"].get_next_step_config.return_value = mock_next_step
    mock_runtime.context["step_manager"].advance_to_next_step.return_value = {
        "flow_stack": state["flow_stack"],
        "conversation_state": "waiting_for_slot",
    }
    mock_runtime.context["step_manager"].get_next_required_slot.return_value = "origin"

    # Mock interrupt
    with patch("langgraph.types.interrupt", return_value="Madrid"):
        # Act
        await collect_next_slot_node(state, mock_runtime)

        # Assert
        assert mock_runtime.context["step_manager"].advance_to_next_step.called


@pytest.mark.asyncio
async def test_collect_next_slot_no_current_step_no_next_step(create_state_with_flow, mock_runtime):
    """Test that collect_next_slot returns error when no next step."""
    # Arrange
    state = create_state_with_flow("book_flight")
    state["flow_stack"][0]["current_step"] = None

    mock_runtime.context["step_manager"].get_current_step_config.return_value = None
    mock_runtime.context["step_manager"].get_next_step_config.return_value = None

    # Act
    result = await collect_next_slot_node(state, mock_runtime)

    # Assert
    assert result["conversation_state"] == "error"


@pytest.mark.asyncio
async def test_collect_next_slot_slot_config_not_found(create_state_with_flow, mock_runtime):
    """Test that collect_next_slot handles slot config not found."""
    # Arrange
    state = create_state_with_flow("book_flight", current_step="collect_origin")

    mock_step_config = MagicMock()
    mock_step_config.type = "collect"
    mock_step_config.slot = "origin"
    mock_runtime.context["step_manager"].get_current_step_config.return_value = mock_step_config
    mock_runtime.context["step_manager"].get_next_required_slot.return_value = "origin"

    # Mock get_slot_config to raise KeyError
    def get_slot_config_side_effect(context, slot_name):
        raise KeyError(f"Slot {slot_name} not found")

    with patch("soni.core.state.get_slot_config", side_effect=get_slot_config_side_effect):
        with patch("langgraph.types.interrupt", return_value="Madrid"):
            # Act
            result = await collect_next_slot_node(state, mock_runtime)

            # Assert - Should use generic prompt
            assert result.get("waiting_for_slot") == "origin"


@pytest.mark.asyncio
async def test_collect_next_slot_no_next_slot_advances_step(create_state_with_flow, mock_runtime):
    """Test that collect_next_slot advances step if no next slot."""
    # Arrange - All slots already filled
    state = create_state_with_flow(
        "book_flight",
        current_step="collect_date",
        slots={"origin": "Madrid", "destination": "Barcelona", "date": "2025-12-25"},
    )

    mock_step_config = MagicMock()
    mock_step_config.type = "collect"
    mock_step_config.slot = "date"
    mock_runtime.context["step_manager"].get_current_step_config.return_value = mock_step_config
    mock_runtime.context["step_manager"].get_next_required_slot.return_value = None
    mock_runtime.context["step_manager"].advance_to_next_step.return_value = {
        "flow_stack": state["flow_stack"],
        "conversation_state": "ready_for_confirmation",
    }

    # Act
    result = await collect_next_slot_node(state, mock_runtime)

    # Assert - Should advance to confirmation
    assert result.get("conversation_state") == "ready_for_confirmation"
    assert mock_runtime.context["step_manager"].advance_to_next_step.called


@pytest.mark.asyncio
async def test_collect_next_slot_interrupts_with_prompt(create_state_with_flow, mock_runtime):
    """Test that collect_next_slot interrupts with prompt."""
    # Arrange
    state = create_state_with_flow("book_flight", current_step="collect_destination")

    mock_step_config = MagicMock()
    mock_step_config.type = "collect"
    mock_step_config.slot = "destination"
    mock_runtime.context["step_manager"].get_current_step_config.return_value = mock_step_config
    mock_runtime.context["step_manager"].get_next_required_slot.return_value = "destination"

    mock_slot_config = MagicMock()
    mock_slot_config.prompt = "Where would you like to go?"
    mock_runtime.context["config"].slots = {"destination": mock_slot_config}

    def get_slot_config(context, slot_name):
        return context["config"].slots.get(slot_name)

    # Mock interrupt to capture the prompt
    interrupt_calls = []

    def mock_interrupt(prompt):
        interrupt_calls.append(prompt)
        return "Barcelona"  # Simulate user response

    with patch("soni.core.state.get_slot_config", get_slot_config):
        with patch("langgraph.types.interrupt", mock_interrupt):
            # Act
            result = await collect_next_slot_node(state, mock_runtime)

            # Assert
            assert len(interrupt_calls) > 0
            assert "Where would you like to go?" in interrupt_calls[0]
            assert result.get("waiting_for_slot") == "destination"
            assert result.get("user_message") == "Barcelona"


@pytest.mark.asyncio
async def test_collect_next_slot_uses_generic_prompt_when_no_config(
    create_state_with_flow, mock_runtime
):
    """Test that collect_next_slot uses generic prompt when slot config has no prompt."""
    # Arrange
    state = create_state_with_flow("book_flight", current_step="collect_origin")

    mock_step_config = MagicMock()
    mock_step_config.type = "collect"
    mock_step_config.slot = "origin"
    mock_runtime.context["step_manager"].get_current_step_config.return_value = mock_step_config
    mock_runtime.context["step_manager"].get_next_required_slot.return_value = "origin"

    # Slot config without prompt attribute
    mock_slot_config = MagicMock()
    del mock_slot_config.prompt  # No prompt attribute
    mock_runtime.context["config"].slots = {"origin": mock_slot_config}

    def get_slot_config(context, slot_name):
        return context["config"].slots.get(slot_name)

    interrupt_calls = []

    def mock_interrupt(prompt):
        interrupt_calls.append(prompt)
        return "Madrid"

    with patch("soni.core.state.get_slot_config", get_slot_config):
        with patch("langgraph.types.interrupt", mock_interrupt):
            # Act
            result = await collect_next_slot_node(state, mock_runtime)

            # Assert - Should use generic prompt
            assert len(interrupt_calls) > 0
            assert "origin" in interrupt_calls[0].lower()
            assert result.get("waiting_for_slot") == "origin"
