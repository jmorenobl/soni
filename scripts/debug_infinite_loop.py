"""Debug script to trace infinite loop in dialogue graph execution."""

import asyncio
import json
import os
import sys
from datetime import datetime
from pathlib import Path
from typing import Any

import dspy

# Add src to path
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

try:
    from dotenv import load_dotenv

    load_dotenv()
except ImportError:
    pass

from soni.core.state import get_all_slots, get_current_flow, state_from_dict
from soni.runtime import RuntimeLoop


# ANSI Colors
class C:
    H = "\033[95m"
    B = "\033[94m"
    C = "\033[96m"
    G = "\033[92m"
    Y = "\033[93m"
    R = "\033[91m"
    E = "\033[0m"
    BOLD = "\033[1m"
    DIM = "\033[2m"


def print_section(title: str):
    print(f"\n{C.H}{C.BOLD}{'=' * 80}{C.E}")
    print(f"{C.H}{C.BOLD}  {title}{C.E}")
    print(f"{C.H}{C.BOLD}{'=' * 80}{C.E}\n")


def print_node_execution(node_name: str, state: dict[str, Any], node_output: dict[str, Any]):
    """Print detailed information about node execution."""
    print(f"\n{C.C}{'─' * 80}{C.E}")
    print(f"{C.BOLD}Node: {C.G}{node_name}{C.E}")

    # Conversation state
    conv_state = state.get("conversation_state", "N/A")
    print(f"  Conversation State: {C.Y}{conv_state}{C.E}")

    # Flow info
    flow_stack = state.get("flow_stack", [])
    if flow_stack:
        active_ctx = flow_stack[-1]
        print(f"  Active Flow: {active_ctx.get('flow_name')} (id: {active_ctx.get('flow_id')})")
        print(f"  Current Step: {active_ctx.get('current_step', 'N/A')}")

    # Slots
    slots = get_all_slots(state)
    print(f"  Slots: {slots if slots else '(empty)'}")

    # Waiting for slot
    waiting_for = state.get("waiting_for_slot")
    if waiting_for:
        print(f"  Waiting for Slot: {C.Y}{waiting_for}{C.E}")

    # NLU result
    nlu_result = state.get("nlu_result")
    if nlu_result:
        msg_type = nlu_result.get("message_type", "N/A")
        command = nlu_result.get("command", "N/A")
        nlu_slots = nlu_result.get("slots", [])
        print(f"  NLU: type={msg_type}, command={command}, slots={len(nlu_slots)}")
        if nlu_slots:
            for slot in nlu_slots[:3]:  # Show first 3
                if isinstance(slot, dict):
                    print(f"    - {slot.get('name')}: {slot.get('value')}")

    # Node output
    if node_output:
        output_keys = list(node_output.keys())
        if output_keys:
            print(f"  Node Output Keys: {output_keys}")
            if "conversation_state" in node_output:
                print(f"    → conversation_state: {node_output['conversation_state']}")
            if "last_response" in node_output:
                resp = node_output["last_response"]
                print(
                    f"    → last_response: {resp[:60]}..."
                    if len(resp) > 60
                    else f"    → last_response: {resp}"
                )

    # Check for interrupt
    if "__interrupt__" in node_output:
        print(f"  {C.Y}⚠ INTERRUPT: {node_output['__interrupt__']}{C.E}")


async def trace_execution(
    runtime: RuntimeLoop, user_message: str, user_id: str, max_iterations: int = 30
):
    """Trace execution and detect infinite loops."""
    print_section(f"TRACING EXECUTION: '{user_message}'")

    config = {"configurable": {"thread_id": user_id}}

    # Track node execution history
    node_history = []
    state_history = []

    print(f"\n{C.B}Processing message with detailed node-by-node tracing...{C.E}\n")

    iteration = 0
    try:
        # Build initial state with all required fields
        initial_state = {
            "user_message": user_message,
            "messages": [],
            "flow_stack": [],
            "flow_slots": {},
            "conversation_state": "understanding",
            "current_step": None,
            "waiting_for_slot": None,
            "current_prompted_slot": None,
            "all_slots_filled": False,
            "last_response": None,
            "nlu_result": None,
            "last_nlu_call": None,
            "digression_depth": 0,
            "last_digression_type": None,
            "turn_count": 0,
            "trace": [],
            "metadata": {},
        }

        async for chunk in runtime.graph.astream(initial_state, config=config):
            iteration += 1
            if iteration > max_iterations:
                print(
                    f"\n{C.R}⚠ MAX ITERATIONS REACHED ({max_iterations}) - POSSIBLE INFINITE LOOP{C.E}\n"
                )
                break

            for node_name, node_output in chunk.items():
                if node_name == "__end__":
                    print(f"\n{C.G}✓ Graph execution completed{C.E}")
                    break

                # Get current state
                current_snapshot = await runtime.graph.aget_state(config)
                current_state = (
                    state_from_dict(current_snapshot.values)
                    if current_snapshot and current_snapshot.values
                    else {}
                )

                # Track execution
                node_history.append(node_name)
                state_history.append(
                    {
                        "node": node_name,
                        "conversation_state": current_state.get("conversation_state"),
                        "waiting_for_slot": current_state.get("waiting_for_slot"),
                        "current_step": (
                            current_state.get("flow_stack", [{}])[-1].get("current_step")
                            if current_state.get("flow_stack")
                            else None
                        ),
                    }
                )

                # Print node execution
                print_node_execution(node_name, current_state, node_output)

                # Check for loops (same node sequence repeating)
                if len(node_history) >= 4:
                    # Check if last 4 nodes form a repeating pattern
                    last_4 = node_history[-4:]
                    if len(set(last_4)) <= 2:  # Only 1-2 unique nodes
                        print(f"\n{C.R}⚠ LOOP DETECTED: Last 4 nodes: {last_4}{C.E}")
                        # Check if conversation_state is also repeating
                        if len(state_history) >= 4:
                            last_4_states = [s["conversation_state"] for s in state_history[-4:]]
                            if len(set(last_4_states)) <= 2:
                                print(f"{C.R}⚠ State also repeating: {last_4_states}{C.E}")
                                print(f"\n{C.R}🔴 INFINITE LOOP CONFIRMED!{C.E}")
                                print(f"{C.R}Pattern: {last_4}{C.E}")
                                print(f"{C.R}States: {last_4_states}{C.E}")
                                return

                # Check if we're stuck in a state
                if len(state_history) >= 6:
                    last_6_states = [s["conversation_state"] for s in state_history[-6:]]
                    if len(set(last_6_states)) == 1 and last_6_states[0] not in (
                        "idle",
                        "completed",
                    ):
                        print(f"\n{C.R}⚠ STUCK IN STATE: {last_6_states[0]} (6+ iterations){C.E}")
                        print(f"{C.R}Node sequence: {node_history[-6:]}{C.E}")
                        return

                if "last_response" in node_output:
                    final_response = node_output["last_response"]
                    print(f"\n{C.G}Final Response: {final_response}{C.E}\n")

        # Final state (for future use if needed)
        _final_snapshot = await runtime.graph.aget_state(config)

        print_section("EXECUTION SUMMARY")
        print(f"{C.Y}Total iterations: {iteration}{C.E}")
        print(f"{C.Y}Nodes executed: {len(node_history)}{C.E}")
        print(f"{C.Y}Node sequence: {node_history}{C.E}")

        if state_history:
            print(f"\n{C.Y}State transitions:{C.E}")
            for i, state_info in enumerate(state_history[-10:]):  # Last 10
                print(
                    f"  {i + 1}. {state_info['node']}: {state_info['conversation_state']} (waiting: {state_info['waiting_for_slot']})"
                )

    except Exception as e:
        print(f"\n{C.R}ERROR during execution: {e}{C.E}")
        import traceback

        traceback.print_exc()
        print(f"\n{C.Y}Node history: {node_history}{C.E}")
        print(f"{C.Y}State history: {state_history[-10:] if state_history else []}{C.E}")


async def main():
    # Configure DSPy
    api_key = os.getenv("OPENAI_API_KEY")
    if api_key:
        lm = dspy.LM("openai/gpt-4o-mini", api_key=api_key)
        dspy.configure(lm=lm)
    else:
        print(f"{C.R}ERROR: OPENAI_API_KEY not found{C.E}")
        return

    # Initialize runtime
    config_path = Path("examples/flight_booking/soni.yaml")
    runtime = RuntimeLoop(config_path)
    runtime.config.settings.persistence.backend = "memory"
    await runtime._ensure_graph_initialized()

    user_id = f"loop_debug_{int(datetime.now().timestamp())}"

    # Test with first message from scenario 1
    print_section("TURN 1: Initial message")
    user_message = "I want to book a flight"
    await trace_execution(runtime, user_message, user_id, max_iterations=10)

    # Test with second message
    print_section("TURN 2: Provide origin")
    user_message = "Madrid"
    await trace_execution(runtime, user_message, user_id, max_iterations=30)

    await runtime.cleanup()


if __name__ == "__main__":
    # Suppress library logs for cleaner output
    import logging

    logging.basicConfig(level=logging.WARNING)
    logging.getLogger("soni").setLevel(logging.WARNING)
    logging.getLogger("langchain").setLevel(logging.WARNING)
    logging.getLogger("langgraph").setLevel(logging.WARNING)

    asyncio.run(main())
