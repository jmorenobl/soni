"""Integration tests for all conversation scenarios."""

import tempfile
from pathlib import Path

import pytest
import yaml

from soni.core.config import ConfigLoader, SoniConfig
from soni.core.state import get_all_slots, get_current_flow, state_from_dict
from soni.runtime import RuntimeLoop


@pytest.fixture
async def runtime():
    """Create RuntimeLoop with in-memory checkpointer for test isolation."""
    config_path = Path("examples/flight_booking/soni.yaml")
    config_dir = config_path.parent

    # Import actions from original config directory
    actions_file = config_dir / "actions.py"
    if actions_file.exists():
        import importlib.util

        spec = importlib.util.spec_from_file_location("user_actions", actions_file)
        if spec and spec.loader:
            module = importlib.util.module_from_spec(spec)
            spec.loader.exec_module(module)

    init_file = config_dir / "__init__.py"
    if init_file.exists():
        import importlib
        import sys

        package_name = config_dir.name
        parent_dir = config_dir.parent
        original_path = sys.path[:]
        try:
            if str(parent_dir) not in sys.path:
                sys.path.insert(0, str(parent_dir))
            importlib.import_module(package_name)
        finally:
            sys.path[:] = original_path

    # Load config and modify persistence backend to memory
    config_dict = ConfigLoader.load(config_path)
    config = SoniConfig(**config_dict)
    config.settings.persistence.backend = "memory"

    # Create temporary config file with memory backend
    with tempfile.NamedTemporaryFile(mode="w", suffix=".yaml", delete=False) as f:
        yaml.dump(config.model_dump(), f)
        temp_config_path = f.name

    try:
        runtime_instance = RuntimeLoop(temp_config_path)
        await runtime_instance._ensure_graph_initialized()
        yield runtime_instance
        await runtime_instance.cleanup()
    finally:
        Path(temp_config_path).unlink(missing_ok=True)


class TestScenario1Sequential:
    """Test Scenario 1: Simple sequential slot collection."""

    @pytest.mark.integration
    @pytest.mark.asyncio
    async def test_scenario_1_complete_flow(
        self, runtime, configure_dspy_for_integration, skip_without_api_key
    ):
        """Test complete sequential flow."""
        user_id = "test_scenario_1"

        # Turn 1: Trigger flow
        await runtime.process_message("I want to book a flight", user_id)
        config = {"configurable": {"thread_id": user_id}}
        snapshot = await runtime.graph.aget_state(config)
        state = state_from_dict(snapshot.values, allow_partial=True)

        assert get_current_flow(state) == "book_flight"
        # Should be waiting for origin slot
        assert state.get("waiting_for_slot") in ("origin", None)

        # Turn 2: Provide origin
        await runtime.process_message("Madrid", user_id)
        snapshot = await runtime.graph.aget_state(config)
        state = state_from_dict(snapshot.values, allow_partial=True)

        slots = get_all_slots(state)
        assert slots.get("origin") == "Madrid"
        # Should advance to destination
        assert state.get("waiting_for_slot") in ("destination", None)

        # Turn 3: Provide destination
        await runtime.process_message("Barcelona", user_id)
        snapshot = await runtime.graph.aget_state(config)
        state = state_from_dict(snapshot.values, allow_partial=True)

        slots = get_all_slots(state)
        assert slots.get("destination") == "Barcelona"
        # Should advance to departure_date
        assert state.get("waiting_for_slot") in ("departure_date", None)

        # Turn 4: Provide date (CRITICAL - should complete)
        response = await runtime.process_message("Tomorrow", user_id)
        snapshot = await runtime.graph.aget_state(config)
        state = state_from_dict(snapshot.values, allow_partial=True)

        slots = get_all_slots(state)
        assert "departure_date" in slots

        # CRITICAL ASSERTIONS: Action should have been executed
        # After action execution and response generation, state may be "idle" (correct)
        # But we should have evidence that the action ran (booking_ref, confirmation, or action_result)
        assert state.get("all_slots_filled") is True, "Should mark all slots filled!"

        # Check that action was executed (not just returned to idle without executing)
        # The action should have produced outputs (booking_ref, confirmation, or flights)
        action_executed = (
            "booking_ref" in slots
            or "confirmation" in slots
            or "flights" in slots
            or state.get("action_result") is not None
        )
        assert action_executed, (
            "Action should have been executed! Expected booking_ref, confirmation, "
            "flights, or action_result in state. Got slots: " + str(list(slots.keys()))
        )

        # Response should not be the generic fallback
        assert "How can I help you?" not in response, (
            "Should not show generic fallback! Action should have executed. "
            f"Response was: {response}"
        )

        # After response generation, conversation_state may be "idle" (this is correct)
        # But if we're still in the flow, we should be at the action step, confirmation, or completed
        if state.get("conversation_state") != "idle":
            # If not idle, should be ready_for_action, ready_for_confirmation, or completed
            assert state.get("conversation_state") in (
                "ready_for_action",
                "ready_for_confirmation",
                "completed",
                "executing_action",
            ), f"Unexpected conversation_state: {state.get('conversation_state')}"


class TestScenario2MultipleSlots:
    """Test Scenario 2: Multiple slots in one message."""

    @pytest.mark.integration
    @pytest.mark.asyncio
    async def test_multiple_slots_in_one_message(
        self, runtime, configure_dspy_for_integration, skip_without_api_key
    ):
        """Test: 'I want to fly from New York to Los Angeles'"""
        user_id = "test_scenario_2"

        # Turn 1: Provide multiple slots
        await runtime.process_message("I want to fly from New York to Los Angeles", user_id)
        config = {"configurable": {"thread_id": user_id}}
        snapshot = await runtime.graph.aget_state(config)
        state = state_from_dict(snapshot.values, allow_partial=True)

        slots = get_all_slots(state)
        assert slots.get("origin") == "New York"
        assert slots.get("destination") == "Los Angeles"
        # CRITICAL: Should advance to collect_date, not stay at collect_destination
        assert state.get("waiting_for_slot") == "departure_date"
        assert state.get("conversation_state") == "waiting_for_slot"

        # Turn 2: Provide last slot
        await runtime.process_message("Next Friday", user_id)
        snapshot = await runtime.graph.aget_state(config)
        state = state_from_dict(snapshot.values, allow_partial=True)

        slots = get_all_slots(state)
        assert "departure_date" in slots
        # After providing all slots, should be ready for action, confirmation, or waiting
        # Note: current_step might be None if flow completed, but conversation_state should indicate readiness
        assert state.get("conversation_state") in (
            "ready_for_action",
            "ready_for_confirmation",
            "waiting_for_slot",
            "idle",
        )

    @pytest.mark.integration
    @pytest.mark.asyncio
    async def test_all_slots_at_once(
        self, runtime, configure_dspy_for_integration, skip_without_api_key
    ):
        """Test: 'I want to fly from X to Y on Z'"""
        user_id = "test_all_slots"

        # Provide all slots in one message
        await runtime.process_message("I want to fly from Boston to Seattle tomorrow", user_id)
        config = {"configurable": {"thread_id": user_id}}
        snapshot = await runtime.graph.aget_state(config)
        state = state_from_dict(snapshot.values, allow_partial=True)

        slots = get_all_slots(state)
        assert len(slots) >= 3
        assert slots.get("origin") == "Boston"
        assert slots.get("destination") == "Seattle"
        assert "departure_date" in slots

        # Should advance all the way to action or confirmation
        # Note: current_step might be None if flow completed
        assert state.get("conversation_state") in (
            "ready_for_action",
            "ready_for_confirmation",
            "waiting_for_slot",
            "idle",
        )


class TestScenario3Correction:
    """Test Scenario 3: Slot correction."""

    @pytest.mark.integration
    @pytest.mark.asyncio
    async def test_scenario_3_correction(
        self, runtime, configure_dspy_for_integration, skip_without_api_key
    ):
        """Test correction of a previously provided slot."""
        user_id = "test_scenario_3"

        # Turn 1: Trigger flow
        await runtime.process_message("Book a flight", user_id)

        # Turn 2: Provide origin
        await runtime.process_message("Chicago", user_id)
        config = {"configurable": {"thread_id": user_id}}
        snapshot = await runtime.graph.aget_state(config)
        state = state_from_dict(snapshot.values, allow_partial=True)

        slots = get_all_slots(state)
        assert slots.get("origin") == "Chicago"

        # Turn 3: Correct origin
        await runtime.process_message("Actually, I meant Denver not Chicago", user_id)
        snapshot = await runtime.graph.aget_state(config)
        state = state_from_dict(snapshot.values, allow_partial=True)

        slots = get_all_slots(state)
        assert slots.get("origin") == "Denver"  # Corrected value
        assert state.get("waiting_for_slot") == "destination"  # Should return to this step

        # Turn 4: Provide destination
        await runtime.process_message("Seattle", user_id)
        snapshot = await runtime.graph.aget_state(config)
        state = state_from_dict(snapshot.values, allow_partial=True)

        slots = get_all_slots(state)
        assert slots.get("origin") == "Denver"
        assert slots.get("destination") == "Seattle"


class TestScenario4Digression:
    """Test Scenario 4: Digression (question during flow)."""

    @pytest.mark.integration
    @pytest.mark.asyncio
    async def test_scenario_4_digression(
        self, runtime, configure_dspy_for_integration, skip_without_api_key
    ):
        """Test question during flow without changing flow."""
        user_id = "test_scenario_4"

        # Turn 1: Trigger flow
        await runtime.process_message("I want to book a flight", user_id)

        # Turn 2: Provide origin
        await runtime.process_message("San Francisco", user_id)
        config = {"configurable": {"thread_id": user_id}}
        snapshot = await runtime.graph.aget_state(config)
        state = state_from_dict(snapshot.values, allow_partial=True)

        slots = get_all_slots(state)
        assert slots.get("origin") == "San Francisco"
        assert get_current_flow(state) == "book_flight"

        # Turn 3: Ask question (digression)
        await runtime.process_message("What airports do you support?", user_id)
        snapshot = await runtime.graph.aget_state(config)
        state = state_from_dict(snapshot.values, allow_partial=True)

        # Flow should NOT change
        assert get_current_flow(state) == "book_flight"
        # After digression, should still be waiting for destination
        assert state.get("waiting_for_slot") in (
            "destination",
            None,
        )  # Should stay the same or be cleared
        slots = get_all_slots(state)
        assert slots.get("origin") == "San Francisco"  # Should not change

        # Turn 4: Continue with destination after digression
        await runtime.process_message("Miami", user_id)
        snapshot = await runtime.graph.aget_state(config)
        state = state_from_dict(snapshot.values, allow_partial=True)

        slots = get_all_slots(state)
        assert slots.get("origin") == "San Francisco"
        assert slots.get("destination") == "Miami"


class TestScenario5Cancellation:
    """Test Scenario 5: Flow cancellation."""

    @pytest.mark.integration
    @pytest.mark.asyncio
    async def test_scenario_5_cancellation(
        self, runtime, configure_dspy_for_integration, skip_without_api_key
    ):
        """Test canceling flow mid-way."""
        user_id = "test_scenario_5"

        # Turn 1: Trigger flow
        await runtime.process_message("Book a flight please", user_id)

        # Turn 2: Provide origin
        await runtime.process_message("Boston", user_id)
        config = {"configurable": {"thread_id": user_id}}
        snapshot = await runtime.graph.aget_state(config)
        state = state_from_dict(snapshot.values, allow_partial=True)

        assert get_current_flow(state) == "book_flight"
        slots = get_all_slots(state)
        assert slots.get("origin") == "Boston"

        # Turn 3: Cancel flow
        await runtime.process_message("Actually, cancel this", user_id)
        snapshot = await runtime.graph.aget_state(config)
        state = state_from_dict(snapshot.values, allow_partial=True)

        # Flow should be canceled
        assert len(state.get("flow_stack", [])) == 0
        assert get_current_flow(state) == "none"
        assert state.get("conversation_state") == "idle"

        # Turn 4: Start fresh
        await runtime.process_message("I want to book a new flight", user_id)
        snapshot = await runtime.graph.aget_state(config)
        state = state_from_dict(snapshot.values, allow_partial=True)

        assert get_current_flow(state) == "book_flight"
        slots = get_all_slots(state)
        assert len(slots) == 0  # New flow, no slots yet
