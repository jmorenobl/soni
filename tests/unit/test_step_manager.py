"""Unit tests for FlowStepManager."""

from typing import cast
from unittest.mock import MagicMock

import pytest

from soni.core.config import SoniConfig, StepConfig
from soni.core.state import create_empty_state
from soni.core.types import DialogueState, RuntimeContext
from soni.flow.step_manager import FlowStepManager


@pytest.fixture
def mock_config():
    """Create a mock SoniConfig with a simple flow."""
    config = MagicMock(spec=SoniConfig)
    config.flows = {
        "book_flight": MagicMock(
            steps_or_process=[
                StepConfig(step="collect_origin", type="collect", slot="origin"),
                StepConfig(step="collect_destination", type="collect", slot="destination"),
                StepConfig(step="collect_date", type="collect", slot="departure_date"),
                StepConfig(step="search_flights", type="action", call="search_available_flights"),
            ]
        )
    }
    return config


@pytest.fixture
def mock_flow_manager():
    """Create a mock FlowManager with get_active_context."""
    from soni.flow.manager import FlowManager

    flow_manager = FlowManager()

    # Mock pop_flow to avoid side effects in tests
    original_pop_flow = flow_manager.pop_flow
    flow_manager.pop_flow = MagicMock(side_effect=original_pop_flow)

    return flow_manager


@pytest.fixture
def mock_context(mock_config, mock_flow_manager):
    """Create a mock RuntimeContext."""
    return {
        "config": mock_config,
        "scope_manager": MagicMock(),
        "normalizer": MagicMock(),
        "action_handler": MagicMock(),
        "du": MagicMock(),
        "flow_manager": mock_flow_manager,
        "step_manager": MagicMock(),
    }


@pytest.fixture
def state_with_flow():
    """Create a state with an active flow."""
    state = create_empty_state()
    state["flow_stack"] = [
        {
            "flow_id": "book_flight_123",
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
    state["flow_slots"] = {}
    return state


class TestAdvanceThroughCompletedSteps:
    """Test iterative step advancement."""

    def test_single_step_advancement(self, mock_config, state_with_flow, mock_flow_manager):
        """Test advancing through one completed step."""
        # Arrange: One collect step complete, next step incomplete
        state = state_with_flow
        state["flow_slots"]["book_flight_123"] = {"origin": "New York"}
        state["flow_stack"][0]["current_step"] = "collect_origin"

        step_manager = FlowStepManager(mock_config)
        context: RuntimeContext = {
            "config": mock_config,
            "scope_manager": MagicMock(),
            "normalizer": MagicMock(),
            "action_handler": MagicMock(),
            "du": MagicMock(),
            "flow_manager": mock_flow_manager,
            "step_manager": step_manager,
        }

        # Act
        updates = step_manager.advance_through_completed_steps(state, context)

        # Assert: Should advance once and stop at incomplete step
        assert updates["conversation_state"] == "waiting_for_slot"
        assert updates["waiting_for_slot"] == "destination"
        assert updates["all_slots_filled"] is False
        assert state["flow_stack"][0]["current_step"] == "collect_destination"

    def test_multiple_steps_advancement(self, mock_config, state_with_flow, mock_flow_manager):
        """Test advancing through multiple completed steps."""
        # Arrange: Two collect steps complete, third incomplete
        state = state_with_flow
        state["flow_slots"]["book_flight_123"] = {
            "origin": "New York",
            "destination": "Los Angeles",
            # departure_date NOT filled - so collect_date step is incomplete
        }
        state["flow_stack"][0]["current_step"] = "collect_origin"

        step_manager = FlowStepManager(mock_config)
        context: RuntimeContext = {
            "config": mock_config,
            "scope_manager": MagicMock(),
            "normalizer": MagicMock(),
            "action_handler": MagicMock(),
            "du": MagicMock(),
            "flow_manager": mock_flow_manager,
            "step_manager": step_manager,
        }

        # Act
        updates = step_manager.advance_through_completed_steps(state, context)

        # Assert: Should advance through collect_origin and collect_destination, stop at collect_date
        assert updates["conversation_state"] == "waiting_for_slot"
        assert updates["waiting_for_slot"] == "departure_date"
        assert updates["all_slots_filled"] is False
        assert state["flow_stack"][0]["current_step"] == "collect_date"

    def test_flow_completion(self, mock_config, mock_flow_manager):
        """Test advancement when flow completes."""
        # Arrange: All steps complete, at last step (action step)
        state = create_empty_state()
        state["flow_stack"] = [
            {
                "flow_id": "book_flight_123",
                "flow_name": "book_flight",
                "flow_state": "active",
                "current_step": "search_flights",  # Last step (action)
                "outputs": {},
                "started_at": 0.0,
                "paused_at": None,
                "completed_at": None,
                "context": None,
            }
        ]
        state["flow_slots"] = {
            "book_flight_123": {
                "origin": "New York",
                "destination": "Los Angeles",
                "departure_date": "2025-12-15",
            }
        }

        step_manager = FlowStepManager(mock_config)
        context: RuntimeContext = {
            "config": mock_config,
            "scope_manager": MagicMock(),
            "normalizer": MagicMock(),
            "action_handler": MagicMock(),
            "du": MagicMock(),
            "flow_manager": mock_flow_manager,
            "step_manager": step_manager,
        }

        # Act
        updates = step_manager.advance_through_completed_steps(state, context)

        # Assert: Should reach action step (not complete yet, action steps are incomplete by design)
        assert updates["conversation_state"] == "ready_for_action"
        assert updates["all_slots_filled"] is True
        assert updates["waiting_for_slot"] is None

    def test_all_slots_filled_reaches_action(self, mock_config, state_with_flow, mock_flow_manager):
        """Test that when all slots are filled, flow advances to action step."""
        # Arrange: All collect steps complete, should reach action step
        state = state_with_flow
        state["flow_slots"]["book_flight_123"] = {
            "origin": "Madrid",
            "destination": "Barcelona",
            "departure_date": "2025-12-09",
        }
        state["flow_stack"][0]["current_step"] = "collect_date"  # Last collect step

        step_manager = FlowStepManager(mock_config)
        context: RuntimeContext = {
            "config": mock_config,
            "scope_manager": MagicMock(),
            "normalizer": MagicMock(),
            "action_handler": MagicMock(),
            "du": MagicMock(),
            "flow_manager": mock_flow_manager,
            "step_manager": step_manager,
        }

        # Act
        updates = step_manager.advance_through_completed_steps(state, context)

        # Assert: Should advance to action step
        assert updates["conversation_state"] == "ready_for_action"
        assert updates["all_slots_filled"] is True
        assert updates["waiting_for_slot"] is None
        assert state["flow_stack"][0]["current_step"] == "search_flights"

    def test_all_slots_filled_reaches_confirm(
        self, mock_config, state_with_flow, mock_flow_manager
    ):
        """Test that when all slots are filled and next step is confirm, reaches confirm step."""
        # Arrange: Flow with confirm step after collect steps
        config_with_confirm = MagicMock(spec=SoniConfig)
        config_with_confirm.flows = {
            "book_flight": MagicMock(
                steps_or_process=[
                    StepConfig(step="collect_origin", type="collect", slot="origin"),
                    StepConfig(step="collect_destination", type="collect", slot="destination"),
                    StepConfig(step="confirm_booking", type="confirm"),
                    StepConfig(
                        step="search_flights", type="action", call="search_available_flights"
                    ),
                ]
            )
        }

        state = state_with_flow
        state["flow_slots"]["book_flight_123"] = {
            "origin": "Madrid",
            "destination": "Barcelona",
        }
        state["flow_stack"][0]["current_step"] = "collect_destination"  # Last collect step

        step_manager = FlowStepManager(config_with_confirm)
        context: RuntimeContext = {
            "config": config_with_confirm,
            "scope_manager": MagicMock(),
            "normalizer": MagicMock(),
            "action_handler": MagicMock(),
            "du": MagicMock(),
            "flow_manager": mock_flow_manager,
            "step_manager": step_manager,
        }

        # Act
        updates = step_manager.advance_through_completed_steps(state, context)

        # Assert: Should advance to confirm step
        assert updates["conversation_state"] == "ready_for_confirmation"
        assert updates["all_slots_filled"] is True
        assert updates["waiting_for_slot"] is None
        assert state["flow_stack"][0]["current_step"] == "confirm_booking"

    def test_no_more_steps_completes_flow(self, mock_config, state_with_flow):
        """Test that when no more steps after last collect, flow completes."""
        # Arrange: Flow with only collect steps (no action/confirm)
        config_collect_only = MagicMock(spec=SoniConfig)
        config_collect_only.flows = {
            "book_flight": MagicMock(
                steps_or_process=[
                    StepConfig(step="collect_origin", type="collect", slot="origin"),
                    StepConfig(step="collect_destination", type="collect", slot="destination"),
                ]
            )
        }

        # Create a mock flow manager with pop_flow tracking
        flow_manager = MagicMock()
        pop_flow_called = {"called": False}

        def get_active_context(state):
            flow_stack = state.get("flow_stack", [])
            if flow_stack:
                return flow_stack[-1]
            return None

        def pop_flow(state, result=None, outputs=None):
            pop_flow_called["called"] = True
            # Actually pop the flow for the test
            if state["flow_stack"]:
                state["flow_stack"].pop()

        flow_manager.get_active_context = get_active_context
        flow_manager.pop_flow = pop_flow

        state = state_with_flow
        state["flow_slots"]["book_flight_123"] = {
            "origin": "Madrid",
            "destination": "Barcelona",
        }
        state["flow_stack"][0]["current_step"] = "collect_destination"  # Last step

        step_manager = FlowStepManager(config_collect_only)
        context: RuntimeContext = {
            "config": config_collect_only,
            "scope_manager": MagicMock(),
            "normalizer": MagicMock(),
            "action_handler": MagicMock(),
            "du": MagicMock(),
            "flow_manager": flow_manager,
            "step_manager": step_manager,
        }

        # Act
        updates = step_manager.advance_through_completed_steps(state, context)

        # Assert: Should complete flow
        assert updates["conversation_state"] == "completed"
        assert updates["all_slots_filled"] is True
        assert pop_flow_called["called"], "pop_flow should be called when flow completes"

    def test_max_iterations_safety(self, mock_config, state_with_flow, mock_flow_manager):
        """Test that max_iterations prevents infinite loops."""
        # Arrange: Create a scenario that would loop
        # We'll mock advance_to_next_step to always return a non-completed state
        # and is_step_complete to always return True (would cause infinite loop)
        state = state_with_flow
        state["flow_slots"]["book_flight_123"] = {"origin": "New York"}

        step_manager = FlowStepManager(mock_config)

        # Track iterations
        iteration_count = 0

        # Mock is_step_complete to always return True (would cause infinite loop)
        def mock_is_step_complete(state, step_config, context):
            return True

        # Mock advance_to_next_step to always return a non-completed state
        def mock_advance_to_next_step(state, context):
            nonlocal iteration_count
            iteration_count += 1
            # Always return a state that indicates more steps (not completed)
            # This simulates an infinite loop scenario
            state["flow_stack"][0]["current_step"] = "collect_origin"  # Reset to same step
            return {
                "flow_stack": state["flow_stack"],
                "conversation_state": "waiting_for_slot",  # Not "completed"
            }

        step_manager.is_step_complete = mock_is_step_complete
        step_manager.advance_to_next_step = mock_advance_to_next_step

        context: RuntimeContext = {
            "config": mock_config,
            "scope_manager": MagicMock(),
            "normalizer": MagicMock(),
            "action_handler": MagicMock(),
            "du": MagicMock(),
            "flow_manager": mock_flow_manager,
            "step_manager": step_manager,
        }

        # Act
        updates = step_manager.advance_through_completed_steps(state, context)

        # Assert: Should stop after max_iterations, return error state
        assert updates["conversation_state"] == "error"
        # Should have iterated max_iterations times
        assert iteration_count == 20


# === get_current_step_config ===


def test_get_current_step_config_exists(mock_config, state_with_flow, mock_context):
    """Test get_current_step_config returns config when step exists."""
    step_manager = FlowStepManager(mock_config)
    state = state_with_flow
    state["flow_stack"][0]["current_step"] = "collect_origin"

    result = step_manager.get_current_step_config(state, mock_context)

    assert result is not None
    assert result.step == "collect_origin"
    assert result.type == "collect"


def test_get_current_step_config_not_exists(mock_config, state_with_flow, mock_context):
    """Test get_current_step_config returns None when step doesn't exist."""
    step_manager = FlowStepManager(mock_config)
    state = state_with_flow
    state["flow_stack"][0]["current_step"] = "nonexistent_step"

    result = step_manager.get_current_step_config(state, mock_context)

    assert result is None


def test_get_current_step_config_no_active_flow(mock_config, mock_context):
    """Test get_current_step_config returns None when no active flow."""
    step_manager = FlowStepManager(mock_config)
    state = create_empty_state()
    state["flow_stack"] = []

    result = step_manager.get_current_step_config(state, mock_context)

    assert result is None


def test_get_current_step_config_no_current_step(mock_config, state_with_flow, mock_context):
    """Test get_current_step_config returns None when no current_step."""
    step_manager = FlowStepManager(mock_config)
    state = state_with_flow
    state["flow_stack"][0]["current_step"] = None

    result = step_manager.get_current_step_config(state, mock_context)

    assert result is None


def test_get_current_step_config_flow_not_found(mock_config, state_with_flow, mock_context):
    """Test get_current_step_config returns None when flow not in config."""
    step_manager = FlowStepManager(mock_config)
    state = state_with_flow
    state["flow_stack"][0]["flow_name"] = "nonexistent_flow"
    state["flow_stack"][0]["current_step"] = "collect_origin"

    result = step_manager.get_current_step_config(state, mock_context)

    assert result is None


# === get_next_step_config ===


def test_get_next_step_config_exists(mock_config, state_with_flow, mock_context):
    """Test get_next_step_config returns next step when it exists."""
    step_manager = FlowStepManager(mock_config)
    state = state_with_flow
    state["flow_stack"][0]["current_step"] = "collect_origin"

    result = step_manager.get_next_step_config(state, mock_context)

    assert result is not None
    assert result.step == "collect_destination"


def test_get_next_step_config_not_exists(mock_config, state_with_flow, mock_context):
    """Test get_next_step_config returns None when at end of flow."""
    step_manager = FlowStepManager(mock_config)
    state = state_with_flow
    state["flow_stack"][0]["current_step"] = "search_flights"  # Last step

    result = step_manager.get_next_step_config(state, mock_context)

    assert result is None


def test_get_next_step_config_no_active_flow(mock_config, mock_context):
    """Test get_next_step_config returns None when no active flow."""
    step_manager = FlowStepManager(mock_config)
    state = create_empty_state()
    state["flow_stack"] = []

    result = step_manager.get_next_step_config(state, mock_context)

    assert result is None


def test_get_next_step_config_no_current_step_returns_first(
    mock_config, state_with_flow, mock_context
):
    """Test get_next_step_config returns first step when no current_step."""
    step_manager = FlowStepManager(mock_config)
    state = state_with_flow
    state["flow_stack"][0]["current_step"] = None

    result = step_manager.get_next_step_config(state, mock_context)

    assert result is not None
    assert result.step == "collect_origin"  # First step


def test_get_next_step_config_current_not_found_returns_first(
    mock_config, state_with_flow, mock_context
):
    """Test get_next_step_config returns first step when current not found."""
    step_manager = FlowStepManager(mock_config)
    state = state_with_flow
    state["flow_stack"][0]["current_step"] = "nonexistent_step"

    result = step_manager.get_next_step_config(state, mock_context)

    assert result is not None
    assert result.step == "collect_origin"  # First step


def test_get_next_step_config_flow_not_found(mock_config, state_with_flow, mock_context):
    """Test get_next_step_config returns None when flow not in config."""
    step_manager = FlowStepManager(mock_config)
    state = state_with_flow
    state["flow_stack"][0]["flow_name"] = "nonexistent_flow"
    state["flow_stack"][0]["current_step"] = "collect_origin"

    result = step_manager.get_next_step_config(state, mock_context)

    assert result is None


def test_get_next_step_config_empty_steps(mock_config, state_with_flow, mock_context):
    """Test get_next_step_config returns None when flow has no steps."""
    config_empty = MagicMock(spec=SoniConfig)
    config_empty.flows = {"book_flight": MagicMock(steps_or_process=[])}

    step_manager = FlowStepManager(config_empty)
    state = state_with_flow
    state["flow_stack"][0]["current_step"] = "collect_origin"
    context = cast(
        RuntimeContext,
        {
            **mock_context,
            "config": config_empty,
        },
    )

    result = step_manager.get_next_step_config(state, context)

    assert result is None


# === advance_to_next_step ===


def test_advance_to_next_step_success(mock_config, state_with_flow, mock_context):
    """Test advance_to_next_step advances to next step."""
    step_manager = FlowStepManager(mock_config)
    state = state_with_flow
    state["flow_stack"][0]["current_step"] = "collect_origin"

    result = step_manager.advance_to_next_step(state, mock_context)

    assert result["conversation_state"] == "waiting_for_slot"
    assert state["flow_stack"][0]["current_step"] == "collect_destination"


def test_advance_to_next_step_at_end(mock_config, state_with_flow, mock_context):
    """Test advance_to_next_step marks flow as completed when at end."""
    step_manager = FlowStepManager(mock_config)
    state = state_with_flow
    state["flow_stack"][0]["current_step"] = "search_flights"  # Last step

    result = step_manager.advance_to_next_step(state, mock_context)

    assert result["conversation_state"] == "completed"
    assert state["flow_stack"][0]["current_step"] is None
    assert state["flow_stack"][0]["flow_state"] == "completed"


def test_advance_to_next_step_action_type(mock_config, state_with_flow, mock_context):
    """Test advance_to_next_step sets correct state for action step."""
    step_manager = FlowStepManager(mock_config)
    state = state_with_flow
    state["flow_stack"][0]["current_step"] = "collect_date"  # Before action

    result = step_manager.advance_to_next_step(state, mock_context)

    assert result["conversation_state"] == "ready_for_action"
    assert state["flow_stack"][0]["current_step"] == "search_flights"


def test_advance_to_next_step_confirm_type(mock_config, state_with_flow, mock_context):
    """Test advance_to_next_step sets correct state for confirm step."""
    config_with_confirm = MagicMock(spec=SoniConfig)
    config_with_confirm.flows = {
        "book_flight": MagicMock(
            steps_or_process=[
                StepConfig(step="collect_origin", type="collect", slot="origin"),
                StepConfig(step="confirm_booking", type="confirm"),
            ]
        )
    }

    step_manager = FlowStepManager(config_with_confirm)
    state = state_with_flow
    state["flow_stack"][0]["current_step"] = "collect_origin"
    context = cast(
        RuntimeContext,
        {
            **mock_context,
            "config": config_with_confirm,
        },
    )

    result = step_manager.advance_to_next_step(state, context)

    assert result["conversation_state"] == "ready_for_confirmation"
    assert state["flow_stack"][0]["current_step"] == "confirm_booking"


def test_advance_to_next_step_branch_type(mock_config, state_with_flow, mock_context):
    """Test advance_to_next_step sets correct state for branch step."""
    config_with_branch = MagicMock(spec=SoniConfig)
    config_with_branch.flows = {
        "book_flight": MagicMock(
            steps_or_process=[
                StepConfig(step="collect_origin", type="collect", slot="origin"),
                StepConfig(step="branch_route", type="branch"),
            ]
        )
    }

    step_manager = FlowStepManager(config_with_branch)
    state = state_with_flow
    state["flow_stack"][0]["current_step"] = "collect_origin"
    context = cast(
        RuntimeContext,
        {
            **mock_context,
            "config": config_with_branch,
        },
    )

    result = step_manager.advance_to_next_step(state, context)

    assert result["conversation_state"] == "understanding"
    assert state["flow_stack"][0]["current_step"] == "branch_route"


def test_advance_to_next_step_say_type(mock_config, state_with_flow, mock_context):
    """Test advance_to_next_step sets correct state for say step."""
    config_with_say = MagicMock(spec=SoniConfig)
    config_with_say.flows = {
        "book_flight": MagicMock(
            steps_or_process=[
                StepConfig(step="collect_origin", type="collect", slot="origin"),
                StepConfig(step="say_greeting", type="say"),
            ]
        )
    }

    step_manager = FlowStepManager(config_with_say)
    state = state_with_flow
    state["flow_stack"][0]["current_step"] = "collect_origin"
    context = cast(
        RuntimeContext,
        {
            **mock_context,
            "config": config_with_say,
        },
    )

    result = step_manager.advance_to_next_step(state, context)

    assert result["conversation_state"] == "generating_response"
    assert state["flow_stack"][0]["current_step"] == "say_greeting"


def test_advance_to_next_step_unknown_type(mock_config, state_with_flow, mock_context):
    """Test advance_to_next_step defaults to waiting_for_slot for unknown type."""
    config_unknown = MagicMock(spec=SoniConfig)
    config_unknown.flows = {
        "book_flight": MagicMock(
            steps_or_process=[
                StepConfig(step="collect_origin", type="collect", slot="origin"),
                StepConfig(step="unknown_step", type="unknown"),
            ]
        )
    }

    step_manager = FlowStepManager(config_unknown)
    state = state_with_flow
    state["flow_stack"][0]["current_step"] = "collect_origin"
    context = cast(
        RuntimeContext,
        {
            **mock_context,
            "config": config_unknown,
        },
    )

    result = step_manager.advance_to_next_step(state, context)

    assert result["conversation_state"] == "waiting_for_slot"
    assert state["flow_stack"][0]["current_step"] == "unknown_step"


def test_advance_to_next_step_no_flow_stack(mock_config, mock_context):
    """Test advance_to_next_step handles empty flow_stack."""
    step_manager = FlowStepManager(mock_config)
    state = create_empty_state()
    state["flow_stack"] = []

    result = step_manager.advance_to_next_step(state, mock_context)

    assert result["conversation_state"] == "completed"


# === is_step_complete ===


def test_is_step_complete_collect_filled(mock_config, state_with_flow, mock_context):
    """Test is_step_complete returns True for filled collect step."""
    step_manager = FlowStepManager(mock_config)
    state = state_with_flow
    state["flow_slots"]["book_flight_123"] = {"origin": "New York"}

    step_config = StepConfig(step="collect_origin", type="collect", slot="origin")
    result = step_manager.is_step_complete(state, step_config, mock_context)

    assert result is True


def test_is_step_complete_collect_not_filled(mock_config, state_with_flow, mock_context):
    """Test is_step_complete returns False for unfilled collect step."""
    step_manager = FlowStepManager(mock_config)
    state = state_with_flow
    state["flow_slots"]["book_flight_123"] = {}  # No origin

    step_config = StepConfig(step="collect_origin", type="collect", slot="origin")
    result = step_manager.is_step_complete(state, step_config, mock_context)

    assert result is False


def test_is_step_complete_action_always_false(mock_config, state_with_flow, mock_context):
    """Test is_step_complete returns False for action steps."""
    step_manager = FlowStepManager(mock_config)
    state = state_with_flow

    step_config = StepConfig(step="search_flights", type="action", call="search")
    result = step_manager.is_step_complete(state, step_config, mock_context)

    assert result is False


def test_is_step_complete_confirm_always_false(mock_config, state_with_flow, mock_context):
    """Test is_step_complete returns False for confirm steps."""
    step_manager = FlowStepManager(mock_config)
    state = state_with_flow

    step_config = StepConfig(step="confirm_booking", type="confirm")
    result = step_manager.is_step_complete(state, step_config, mock_context)

    assert result is False


def test_is_step_complete_collect_no_slot(mock_config, state_with_flow, mock_context):
    """Test is_step_complete returns False for collect step with no slot."""
    step_manager = FlowStepManager(mock_config)
    state = state_with_flow

    step_config = StepConfig(step="collect_origin", type="collect", slot=None)
    result = step_manager.is_step_complete(state, step_config, mock_context)

    assert result is False


def test_is_step_complete_collect_empty_string(mock_config, state_with_flow, mock_context):
    """Test is_step_complete returns False for collect step with empty string value."""
    step_manager = FlowStepManager(mock_config)
    state = state_with_flow
    state["flow_slots"]["book_flight_123"] = {"origin": ""}

    step_config = StepConfig(step="collect_origin", type="collect", slot="origin")
    result = step_manager.is_step_complete(state, step_config, mock_context)

    assert result is False


def test_is_step_complete_collect_whitespace_only(mock_config, state_with_flow, mock_context):
    """Test is_step_complete returns False for collect step with whitespace-only value."""
    step_manager = FlowStepManager(mock_config)
    state = state_with_flow
    state["flow_slots"]["book_flight_123"] = {"origin": "   "}

    step_config = StepConfig(step="collect_origin", type="collect", slot="origin")
    result = step_manager.is_step_complete(state, step_config, mock_context)

    assert result is False


def test_is_step_complete_branch_returns_true(mock_config, state_with_flow, mock_context):
    """Test is_step_complete returns True for branch steps."""
    step_manager = FlowStepManager(mock_config)
    state = state_with_flow

    step_config = StepConfig(step="branch_route", type="branch")
    result = step_manager.is_step_complete(state, step_config, mock_context)

    assert result is True


def test_is_step_complete_say_returns_true(mock_config, state_with_flow, mock_context):
    """Test is_step_complete returns True for say steps."""
    step_manager = FlowStepManager(mock_config)
    state = state_with_flow

    step_config = StepConfig(step="say_greeting", type="say")
    result = step_manager.is_step_complete(state, step_config, mock_context)

    assert result is True


# === get_next_required_slot ===


def test_get_next_required_slot_collect_not_filled(mock_config, state_with_flow, mock_context):
    """Test get_next_required_slot returns slot name for unfilled collect step."""
    step_manager = FlowStepManager(mock_config)
    state = state_with_flow
    state["flow_slots"]["book_flight_123"] = {}  # No origin

    step_config = StepConfig(step="collect_origin", type="collect", slot="origin")
    result = step_manager.get_next_required_slot(state, step_config, mock_context)

    assert result == "origin"


def test_get_next_required_slot_collect_filled(mock_config, state_with_flow, mock_context):
    """Test get_next_required_slot returns None for filled collect step."""
    step_manager = FlowStepManager(mock_config)
    state = state_with_flow
    state["flow_slots"]["book_flight_123"] = {"origin": "New York"}

    step_config = StepConfig(step="collect_origin", type="collect", slot="origin")
    result = step_manager.get_next_required_slot(state, step_config, mock_context)

    assert result is None


def test_get_next_required_slot_action_returns_none(mock_config, state_with_flow, mock_context):
    """Test get_next_required_slot returns None for action steps."""
    step_manager = FlowStepManager(mock_config)
    state = state_with_flow

    step_config = StepConfig(step="search_flights", type="action", call="search")
    result = step_manager.get_next_required_slot(state, step_config, mock_context)

    assert result is None


def test_get_next_required_slot_collect_no_slot(mock_config, state_with_flow, mock_context):
    """Test get_next_required_slot returns None for collect step with no slot."""
    step_manager = FlowStepManager(mock_config)
    state = state_with_flow

    step_config = StepConfig(step="collect_origin", type="collect", slot=None)
    result = step_manager.get_next_required_slot(state, step_config, mock_context)

    assert result is None


# === advance_through_completed_steps edge cases ===


def test_advance_through_completed_steps_no_active_flow(mock_config, mock_flow_manager):
    """Test advance_through_completed_steps handles no active flow."""
    step_manager = FlowStepManager(mock_config)
    state = create_empty_state()
    state["flow_stack"] = []
    context: RuntimeContext = {
        "config": mock_config,
        "scope_manager": MagicMock(),
        "normalizer": MagicMock(),
        "action_handler": MagicMock(),
        "du": MagicMock(),
        "flow_manager": mock_flow_manager,
        "step_manager": step_manager,
    }

    result = step_manager.advance_through_completed_steps(state, context)

    assert result["conversation_state"] == "idle"


def test_advance_through_completed_steps_no_steps_in_flow(
    mock_config, state_with_flow, mock_flow_manager
):
    """Test advance_through_completed_steps handles flow with no steps."""
    config_no_steps = MagicMock(spec=SoniConfig)
    config_no_steps.flows = {"book_flight": MagicMock(steps_or_process=[])}

    step_manager = FlowStepManager(config_no_steps)
    state = state_with_flow
    state["flow_stack"][0]["current_step"] = None
    context: RuntimeContext = {
        "config": config_no_steps,
        "scope_manager": MagicMock(),
        "normalizer": MagicMock(),
        "action_handler": MagicMock(),
        "du": MagicMock(),
        "flow_manager": mock_flow_manager,
        "step_manager": step_manager,
    }

    result = step_manager.advance_through_completed_steps(state, context)

    assert result["conversation_state"] == "completed"
    assert result["all_slots_filled"] is True


def test_advance_through_completed_steps_flow_not_found(
    mock_config, state_with_flow, mock_flow_manager
):
    """Test advance_through_completed_steps handles flow not found in config."""
    step_manager = FlowStepManager(mock_config)
    state = state_with_flow
    state["flow_stack"][0]["flow_name"] = "nonexistent_flow"
    state["flow_stack"][0]["current_step"] = None
    context: RuntimeContext = {
        "config": mock_config,
        "scope_manager": MagicMock(),
        "normalizer": MagicMock(),
        "action_handler": MagicMock(),
        "du": MagicMock(),
        "flow_manager": mock_flow_manager,
        "step_manager": step_manager,
    }

    result = step_manager.advance_through_completed_steps(state, context)

    assert result["conversation_state"] == "error"
