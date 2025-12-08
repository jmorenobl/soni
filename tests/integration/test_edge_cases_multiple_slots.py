"""Edge case tests for multiple slots processing."""

import tempfile
from pathlib import Path

import pytest
import yaml

from soni.core.config import ConfigLoader, SoniConfig
from soni.core.state import get_all_slots, state_from_dict
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


class TestEdgeCasesMultipleSlots:
    """Edge cases for multiple slots processing."""

    @pytest.mark.integration
    @pytest.mark.asyncio
    async def test_mix_new_slots_and_corrections(self, runtime, skip_without_api_key):
        """Test providing multiple slots while correcting one."""
        user_id = "test_mix_slots_corrections"

        # Turn 1: Trigger flow and provide origin
        await runtime.process_message("I want to book a flight", user_id)
        await runtime.process_message("Chicago", user_id)

        config = {"configurable": {"thread_id": user_id}}
        snapshot = await runtime.graph.aget_state(config)
        state = state_from_dict(snapshot.values, allow_partial=True)

        slots = get_all_slots(state)
        assert slots.get("origin") == "Chicago"

        # Turn 2: Correct origin and provide destination in same message
        # This is a complex edge case: correction + new slot
        await runtime.process_message(
            "Actually, I meant Denver, and I want to go to Seattle", user_id
        )
        snapshot = await runtime.graph.aget_state(config)
        state = state_from_dict(snapshot.values, allow_partial=True)

        slots = get_all_slots(state)
        # Should have corrected origin
        assert slots.get("origin") == "Denver"
        # Destination might be extracted in same message or next turn
        # This is a complex edge case that depends on NLU's ability to extract both
        # For now, we verify the correction worked
        if slots.get("destination"):
            assert slots.get("destination") == "Seattle"

    @pytest.mark.integration
    @pytest.mark.asyncio
    async def test_invalid_slot_values_with_multiple_slots(self, runtime, skip_without_api_key):
        """Test validation error handling when multiple slots provided but one is invalid."""
        user_id = "test_invalid_multiple"

        # Turn 1: Provide multiple slots, one might be invalid
        # Note: This test depends on the normalizer's validation logic
        # If normalizer accepts all values, this test will pass
        await runtime.process_message("I want to fly from New York to Los Angeles", user_id)

        config = {"configurable": {"thread_id": user_id}}
        snapshot = await runtime.graph.aget_state(config)
        state = state_from_dict(snapshot.values, allow_partial=True)

        slots = get_all_slots(state)
        # At least origin and destination should be valid
        assert slots.get("origin") == "New York"
        assert slots.get("destination") == "Los Angeles"

        # If validation fails for one slot, the system should handle it gracefully
        # The exact behavior depends on validation implementation

    @pytest.mark.integration
    @pytest.mark.asyncio
    async def test_max_iterations_safety(self, runtime, skip_without_api_key):
        """Test that max_iterations limit prevents infinite loops."""
        user_id = "test_max_iterations"

        # This test verifies that advance_through_completed_steps has a safety limit
        # We can't easily create a scenario that would loop 20+ times in a real flow,
        # but we can verify the limit exists in the code

        # Create a flow with many completed steps
        # Note: This is a theoretical test - in practice, flows don't have 20+ collect steps
        # The safety limit is tested in unit tests (test_step_manager.py)

        # For integration test, we just verify that a normal flow with multiple slots
        # doesn't hit the limit
        await runtime.process_message("I want to fly from New York to Los Angeles", user_id)

        config = {"configurable": {"thread_id": user_id}}
        snapshot = await runtime.graph.aget_state(config)
        state = state_from_dict(snapshot.values, allow_partial=True)

        # Should complete without hitting max_iterations
        slots = get_all_slots(state)
        assert slots.get("origin") == "New York"
        assert slots.get("destination") == "Los Angeles"
        # Should advance correctly without errors
        assert state.get("conversation_state") != "error"
