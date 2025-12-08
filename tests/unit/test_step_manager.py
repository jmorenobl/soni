"""Unit tests for FlowStepManager."""

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
