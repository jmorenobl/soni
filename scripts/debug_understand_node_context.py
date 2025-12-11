"""Debug what context understand_node is building for the first message."""

import asyncio
import os
import tempfile
from pathlib import Path

import dspy
import yaml
from dotenv import load_dotenv

from soni.core.config import ConfigLoader, SoniConfig
from soni.core.state import DialogueState
from soni.dm.nodes.understand import understand_node
from soni.runtime.runtime import RuntimeLoop

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
    """Debug understand_node context building."""
    print("=" * 80)
    print("DEBUG: understand_node context building")
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

        # Get runtime context
        context = runtime._context

        # Build initial state (like first message)
        # Initial state
        initial_state: DialogueState = {
            "user_message": "I want to book a flight",
            "messages": [],
            "flow_stack": [],
            "flow_slots": {},
            "conversation_state": "idle",
            "metadata": {},
        }

        print("\n📝 Initial State:")
        print(f"  user_message: {initial_state['user_message']}")
        print(f"  flow_stack: {initial_state['flow_stack']}")
        print(f"  conversation_state: {initial_state['conversation_state']}")

        # Check what context understand_node would build
        from soni.flow.manager import FlowManager

        flow_manager: FlowManager = context.flow_manager
        active_ctx = flow_manager.get_active_context(initial_state)
        current_flow_name = active_ctx["flow_name"] if active_ctx else "none"

        print("\n🔍 Context Analysis:")
        print(f"  active_ctx: {active_ctx}")
        print(f"  current_flow_name: {current_flow_name}")

        from soni.core.scope import ScopeManager

        scope_manager: ScopeManager = context.scope_manager
        available_actions = scope_manager.get_available_actions(initial_state)
        available_flows = scope_manager.get_available_flows(initial_state)

        print(f"  available_actions: {available_actions}")
        print(f"  available_flows: {list(available_flows.keys())}")

        expected_slots = []
        if current_flow_name and current_flow_name != "none":
            expected_slots = scope_manager.get_expected_slots(
                flow_name=current_flow_name,
                available_actions=available_actions,
            )

        print(f"  expected_slots: {expected_slots}")

        # Check if two-stage prediction would be used
        if current_flow_name == "none" and not expected_slots and available_flows:
            print("\n⚠️  Two-stage prediction would be used")
            print("   This might be causing the issue!")
        else:
            print("\n✅ Single-stage prediction would be used")

        # Now call understand_node
        print("\n🔍 Calling understand_node...")
        result = await understand_node(initial_state, context)

        print("\n📊 Result from understand_node:")
        nlu_result = result.get("nlu_result", {})
        print(f"  message_type: {nlu_result.get('message_type')}")
        print(f"  command: {nlu_result.get('command')}")
        print(f"  slots: {nlu_result.get('slots')}")
        print(f"  confidence: {nlu_result.get('confidence')}")

        if nlu_result.get("message_type") == "continuation" and not nlu_result.get("command"):
            print("\n❌ PROBLEM: NLU returned continuation with no command")
            print("   This is why the flow doesn't activate!")
        elif nlu_result.get("command") == "book_flight":
            print("\n✅ NLU detected command correctly")
        else:
            print("\n⚠️  Unexpected result")

        await runtime.cleanup()

    finally:
        Path(temp_config_path).unlink(missing_ok=True)


if __name__ == "__main__":
    asyncio.run(main())
