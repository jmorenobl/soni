"""Debug routing after validate_slot to see what's happening."""

import asyncio
import os
import tempfile
from pathlib import Path

import dspy
import yaml
from dotenv import load_dotenv

from soni.core.config import ConfigLoader, SoniConfig
from soni.runtime import RuntimeLoop

# Load environment
load_dotenv()

# Configure DSPy with real LM
api_key = os.getenv("OPENAI_API_KEY")
if not api_key:
    print("ERROR: OPENAI_API_KEY not set")
    exit(1)

lm = dspy.LM("openai/gpt-4o-mini", api_key=api_key)
dspy.configure(lm=lm)


async def main():
    """Debug routing after validate_slot."""
    print("=" * 80)
    print("DEBUG: Routing after validate_slot")
    print("=" * 80)

    # Setup runtime
    config_path = Path("examples/flight_booking/soni.yaml")
    config_dir = config_path.parent

    # Import actions
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

    # Load config
    config_dict = ConfigLoader.load(config_path)
    config = SoniConfig(**config_dict)
    config.settings.persistence.backend = "memory"

    # Create temporary config file
    with tempfile.NamedTemporaryFile(mode="w", suffix=".yaml", delete=False) as f:
        yaml.dump(config.model_dump(), f)
        temp_config_path = f.name

    try:
        runtime = RuntimeLoop(temp_config_path)
        await runtime._ensure_graph_initialized()

        user_id = "test-user-debug-routing"

        print("\n" + "=" * 80)
        print("STEP 1: User says 'I want to book a flight'")
        print("=" * 80)

        response1 = await runtime.process_message("I want to book a flight", user_id)
        print(f"Response 1: {response1}")

        # Get state after step 1
        config_checkpoint = {"configurable": {"thread_id": user_id}}

        state_after_1 = await runtime.graph.aget_state(config_checkpoint)
        print("\n📊 State after step 1:")
        print(f"  - conversation_state: {state_after_1.values.get('conversation_state')}")
        print(f"  - last_response: {state_after_1.values.get('last_response')}")
        print(f"  - current_prompted_slot: {state_after_1.values.get('current_prompted_slot')}")

        print("\n" + "=" * 80)
        print("STEP 2: User says 'New York'")
        print("=" * 80)

        # Manually trace what should happen:
        # 1. understand_node processes "New York"
        # 2. route_after_understand -> validate_slot (because message_type=slot_value)
        # 3. validate_slot validates and advances
        # 4. route_after_validate -> collect_next_slot (because conversation_state=waiting_for_slot)
        # 5. collect_next_slot should set last_response for destination
        # 6. But then route_after_collect_next_slot -> generate_response (because no user_message yet?)
        # 7. generate_response uses old last_response

        response2 = await runtime.process_message("New York", user_id)
        print(f"Response 2: {response2}")

        # Get state after step 2
        state_after_2 = await runtime.graph.aget_state(config_checkpoint)
        print("\n📊 State after step 2:")
        print(f"  - conversation_state: {state_after_2.values.get('conversation_state')}")
        print(f"  - last_response: {state_after_2.values.get('last_response')}")
        print(f"  - current_prompted_slot: {state_after_2.values.get('current_prompted_slot')}")
        print(f"  - waiting_for_slot: {state_after_2.values.get('waiting_for_slot')}")
        print(f"  - flow_stack: {state_after_2.values.get('flow_stack')}")

        await runtime.cleanup()

    finally:
        Path(temp_config_path).unlink(missing_ok=True)


if __name__ == "__main__":
    asyncio.run(main())
