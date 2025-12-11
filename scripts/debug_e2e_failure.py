"""Debug script to analyze why test_e2e_flight_booking_complete_flow fails.

This script reproduces the exact scenario from the failing test and prints
detailed information about what's happening at each step.
"""

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
    """Reproduce the failing test scenario."""
    print("=" * 80)
    print("DEBUG: test_e2e_flight_booking_complete_flow")
    print("=" * 80)

    # Setup runtime (same as test)
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

        user_id = "test-user-debug"

        print("\n" + "=" * 80)
        print("STEP 1: User says 'I want to book a flight'")
        print("=" * 80)

        # Get initial state
        from langgraph.checkpoint.memory import MemorySaver

        checkpointer = MemorySaver()
        config_checkpoint = {"configurable": {"thread_id": user_id}}

        # Check initial state
        initial_state = await checkpointer.aget(config_checkpoint)
        print(f"\nInitial state: {initial_state}")

        # Process first message
        try:
            response1 = await runtime.process_message("I want to book a flight", user_id)
            print(f"\n✅ Response received: {response1}")
            print(f"Response length: {len(response1)}")

            # Check state after processing
            state_after = await runtime.graph.aget_state(config_checkpoint)
            print("\n📊 State after processing:")
            print(f"  - conversation_state: {state_after.values.get('conversation_state')}")
            print(f"  - flow_stack: {state_after.values.get('flow_stack')}")
            print(f"  - nlu_result: {state_after.values.get('nlu_result')}")

            # Analyze NLU result
            nlu_result = state_after.values.get("nlu_result")
            if nlu_result:
                print("\n🔍 NLU Analysis:")
                print(f"  - message_type: {nlu_result.get('message_type')}")
                print(f"  - command: {nlu_result.get('command')}")
                print(f"  - slots: {nlu_result.get('slots')}")
                print(f"  - confidence: {nlu_result.get('confidence')}")

            # Check if flow was activated
            flow_stack = state_after.values.get("flow_stack", [])
            if flow_stack:
                active_flow = flow_stack[-1]
                print("\n📋 Active Flow:")
                print(f"  - flow_name: {active_flow.get('flow_name')}")
                print(f"  - flow_id: {active_flow.get('flow_id')}")
                print(f"  - flow_state: {active_flow.get('flow_state')}")

            # Check expected vs actual
            print("\n❓ Expected: Response should mention 'origin' or 'from' or 'depart'")
            print(f"   Actual: {response1[:200]}")

            if (
                "origin" in response1.lower()
                or "from" in response1.lower()
                or "depart" in response1.lower()
            ):
                print("✅ PASS: Response mentions origin")
            elif "error" in response1.lower() or "try again" in response1.lower():
                print("⚠️  WARN: Response mentions error")
            else:
                print("❌ FAIL: Response doesn't mention origin or error")
                print(f"   Full response: {response1}")

        except Exception as e:
            print(f"\n❌ Exception occurred: {e}")
            import traceback

            traceback.print_exc()

        finally:
            await runtime.cleanup()

    finally:
        Path(temp_config_path).unlink(missing_ok=True)


if __name__ == "__main__":
    asyncio.run(main())
