#!/usr/bin/env python3
"""Debug script to trace node execution step by step."""

import asyncio
import logging
import os
import sys
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).parent / "src"))

try:
    from dotenv import load_dotenv

    load_dotenv()
except ImportError:
    pass

import dspy

from soni.runtime import RuntimeLoop

# Enable detailed logging
logging.basicConfig(
    level=logging.INFO,
    format="%(levelname)-8s [%(name)s:%(lineno)d] %(message)s",
)

# Focus on specific loggers
logging.getLogger("soni.dm.nodes").setLevel(logging.INFO)
logging.getLogger("soni.dm.routing").setLevel(logging.INFO)
logging.getLogger("soni.dm.builder").setLevel(logging.INFO)
logging.getLogger("soni.runtime.runtime").setLevel(logging.INFO)


class NodeExecutionTracker:
    """Track node executions to identify loops."""

    def __init__(self):
        self.executions = []
        self.node_counts = {}

    def track(self, node_name: str, state_snapshot: dict):
        """Track a node execution."""
        conv_state = state_snapshot.get("conversation_state", "unknown")
        last_response = state_snapshot.get("last_response", "")[:50]
        user_message = state_snapshot.get("user_message", "")[:50]

        self.executions.append(
            {
                "node": node_name,
                "conversation_state": conv_state,
                "last_response": last_response,
                "user_message": user_message,
            }
        )

        self.node_counts[node_name] = self.node_counts.get(node_name, 0) + 1

        print(f"\n{'=' * 70}")
        print(f"EXECUTING: {node_name}")
        print(f"  conversation_state: {conv_state}")
        print(f"  last_response: {last_response}")
        print(f"  user_message: {user_message}")
        print(f"  Total executions of {node_name}: {self.node_counts[node_name]}")
        print(f"{'=' * 70}")

    def detect_loop(self):
        """Detect if there's a loop pattern."""
        if len(self.executions) < 4:
            return False

        # Check last 4 nodes
        last_4 = [e["node"] for e in self.executions[-4:]]
        if len(set(last_4)) <= 2:
            print(f"\n⚠️  LOOP DETECTED: Last 4 nodes: {last_4}")
            return True

        return False


tracker = NodeExecutionTracker()


async def main():
    # Configure DSPy
    api_key = os.getenv("OPENAI_API_KEY")
    if not api_key:
        print("ERROR: OPENAI_API_KEY not found")
        return

    lm = dspy.LM("openai/gpt-4o-mini", api_key=api_key)
    dspy.configure(lm=lm)

    # Initialize runtime
    config_path = Path("examples/flight_booking/soni.yaml")
    runtime = RuntimeLoop(config_path)
    runtime.config.settings.persistence.backend = "memory"
    await runtime._ensure_graph_initialized()

    user_id = "test_debug_detailed"

    print("\n" + "=" * 70)
    print("STARTING TEST - Confirmation unclear scenario")
    print("=" * 70 + "\n")

    # Complete to confirmation
    print("Step 1: Book a flight")
    await runtime.process_message("Book a flight", user_id)

    print("\nStep 2: Boston")
    await runtime.process_message("Boston", user_id)

    print("\nStep 3: Seattle")
    await runtime.process_message("Seattle", user_id)

    print("\nStep 4: Next week")
    await runtime.process_message("Next week", user_id)

    print("\n" + "=" * 70)
    print("Step 5: Unclear response - THIS SHOULD TRIGGER THE LOOP")
    print("=" * 70 + "\n")

    # Try to intercept node executions
    # This is a simplified approach - in production we'd use LangGraph's stream events
    try:
        response = await runtime.process_message("hmm, I'm not sure", user_id)
        print(f"\n✅ Response received: {response}")
    except Exception as e:
        print(f"\n❌ ERROR: {type(e).__name__}: {e}")
        import traceback

        traceback.print_exc()

    # Print execution summary
    print("\n" + "=" * 70)
    print("EXECUTION SUMMARY")
    print("=" * 70)
    print(f"Total node executions tracked: {len(tracker.executions)}")
    print("\nNode execution counts:")
    for node, count in sorted(tracker.node_counts.items()):
        print(f"  {node}: {count}")

    await runtime.cleanup()


if __name__ == "__main__":
    asyncio.run(main())
