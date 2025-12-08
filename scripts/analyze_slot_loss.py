#!/usr/bin/env python3
"""
Analyze slot loss problem when multiple slots are extracted in one message.

This script traces the execution flow to identify where slots are being lost.
"""

import asyncio
import json
import os
import sys
from pathlib import Path
from typing import Any

# Add src to path
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

try:
    from dotenv import load_dotenv

    load_dotenv()
except ImportError:
    pass

import dspy

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
    """Print a section header."""
    print(f"\n{C.H}{C.BOLD}{'=' * 80}{C.E}")
    print(f"{C.H}{C.BOLD}  {title}{C.E}")
    print(f"{C.H}{C.BOLD}{'=' * 80}{C.E}\n")


def print_state_analysis(state: dict[str, Any], step_name: str):
    """Print detailed state analysis."""
    print(f"{C.C}{'─' * 80}{C.E}")
    print(f"{C.BOLD}Step: {step_name}{C.E}\n")

    # Flow stack analysis
    flow_stack = state.get("flow_stack", [])
    print(f"{C.Y}Flow Stack:{C.E}")
    if flow_stack:
        for i, flow_ctx in enumerate(flow_stack):
            flow_id = flow_ctx.get("flow_id", "N/A")
            flow_name = flow_ctx.get("flow_name", "N/A")
            current_step = flow_ctx.get("current_step", "N/A")
            print(f"  [{i}] flow_id: {C.BOLD}{flow_id}{C.E}")
            print(f"      flow_name: {flow_name}")
            print(f"      current_step: {current_step}")
    else:
        print(f"  {C.R}Empty{C.E}")

    # Flow slots analysis
    flow_slots = state.get("flow_slots", {})
    print(f"\n{C.Y}Flow Slots (by flow_id):{C.E}")
    if flow_slots:
        for flow_id, slots in flow_slots.items():
            print(f"  {C.BOLD}{flow_id}{C.E}:")
            if slots:
                for slot_name, slot_value in slots.items():
                    print(f"    - {slot_name}: {slot_value}")
            else:
                print(f"    {C.R}(empty){C.E}")
    else:
        print(f"  {C.R}Empty{C.E}")

    # Current slots (from active flow)
    current_flow = get_current_flow(state)
    all_slots = get_all_slots(state)
    print(f"\n{C.Y}Current Flow: {C.BOLD}{current_flow}{C.E}")
    print(f"{C.Y}All Slots (from active flow):{C.E}")
    if all_slots:
        for slot_name, slot_value in all_slots.items():
            print(f"  - {slot_name}: {slot_value}")
    else:
        print(f"  {C.R}(empty){C.E}")

    # NLU result
    nlu_result = state.get("nlu_result")
    if nlu_result:
        print(f"\n{C.Y}NLU Result:{C.E}")
        print(f"  Command: {nlu_result.get('command', 'N/A')}")
        print(f"  Message Type: {nlu_result.get('message_type', 'N/A')}")
        slots_from_nlu = nlu_result.get("slots", [])
        if slots_from_nlu:
            print("  Extracted Slots:")
            for slot in slots_from_nlu:
                if isinstance(slot, dict):
                    print(
                        f"    - {slot.get('name')}: {slot.get('value')} (conf: {slot.get('confidence', 'N/A')})"
                    )
                else:
                    print(f"    - {slot}")
        else:
            print(f"  {C.R}No slots extracted{C.E}")

    # Conversation state
    print(f"\n{C.Y}Conversation State:{C.E}")
    print(f"  State: {state.get('conversation_state', 'N/A')}")
    print(f"  Waiting for Slot: {state.get('waiting_for_slot', 'N/A')}")
    print(f"  Current Prompted Slot: {state.get('current_prompted_slot', 'N/A')}")
    print(f"  All Slots Filled: {state.get('all_slots_filled', False)}")


async def trace_execution(runtime: RuntimeLoop, user_message: str, user_id: str):
    """Trace execution and capture state at each step."""
    print_section(f"TRACING EXECUTION: '{user_message}'")

    # Capture initial state
    config = {"configurable": {"thread_id": user_id}}
    initial_snapshot = await runtime.graph.aget_state(config)
    initial_state = {}
    if initial_snapshot and initial_snapshot.values:
        initial_state = state_from_dict(initial_snapshot.values, allow_partial=True)
        print_state_analysis(initial_state, "INITIAL STATE")

    # Process message using astream to capture state after each node
    print(f"\n{C.B}Processing message with node-by-node tracing...{C.E}\n")

    # Prepare initial state - use the runtime's process_message but intercept with astream
    # We'll use a custom approach: call process_message but also trace internally
    from soni.core.types import DialogueState

    # Get or create initial state dict
    if not initial_snapshot or not initial_snapshot.values:
        initial_state_dict: dict[str, Any] = {
            "user_message": user_message,
            "last_response": "",
            "messages": [],
            "flow_stack": [],
            "flow_slots": {},
            "conversation_state": "idle",
            "current_step": None,
            "waiting_for_slot": None,
            "current_prompted_slot": None,
            "nlu_result": None,
            "last_nlu_call": None,
            "digression_depth": 0,
            "last_digression_type": None,
            "turn_count": 0,
            "trace": [],
            "metadata": {},
            "all_slots_filled": False,
        }
    else:
        initial_state_dict = dict(initial_snapshot.values)
        initial_state_dict["user_message"] = user_message

    # Stream execution to capture state after each node
    node_states: list[tuple[str, dict[str, Any]]] = []

    try:
        async for event in runtime.graph.astream(initial_state_dict, config):
            # event is a dict with node names as keys
            for node_name, _node_output in event.items():
                # Get state after this node
                snapshot = await runtime.graph.aget_state(config)
                if snapshot and snapshot.values:
                    state_after_node = state_from_dict(snapshot.values, allow_partial=True)
                    node_states.append((node_name, state_after_node))

                    print(f"\n{C.C}{'─' * 80}{C.E}")
                    print(f"{C.BOLD}After node: {C.G}{node_name}{C.E}")

                    # Show conversation state
                    conv_state = state_after_node.get("conversation_state", "N/A")
                    print(f"  Conversation State: {C.Y}{conv_state}{C.E}")

                    # Show key changes
                    slots_after = get_all_slots(state_after_node)
                    flow_stack_after = state_after_node.get("flow_stack", [])
                    nlu_result_after = state_after_node.get("nlu_result")

                    print(f"  Flow stack depth: {len(flow_stack_after)}")
                    if flow_stack_after:
                        print(f"  Active flow_id: {flow_stack_after[-1].get('flow_id')}")
                        print(f"  Active flow_name: {flow_stack_after[-1].get('flow_name')}")
                    else:
                        print(f"  {C.R}No flow active!{C.E}")

                    print(f"  Slots: {slots_after}")

                    if nlu_result_after:
                        extracted = {}
                        for slot in nlu_result_after.get("slots", []):
                            if isinstance(slot, dict):
                                extracted[slot.get("name")] = slot.get("value")
                        if extracted:
                            print(f"  NLU extracted: {extracted}")
                            # Check if extracted slots are in flow_slots
                            flow_slots_after = state_after_node.get("flow_slots", {})
                            if flow_stack_after:
                                active_flow_id = flow_stack_after[-1].get("flow_id")
                                active_slots = flow_slots_after.get(active_flow_id, {})
                                missing = set(extracted.keys()) - set(active_slots.keys())
                                if missing:
                                    print(f"  {C.R}⚠ Missing in flow_slots: {missing}{C.E}")

                    # Show flow_slots structure
                    flow_slots_after = state_after_node.get("flow_slots", {})
                    if flow_slots_after:
                        print("  Flow slots structure:")
                        for flow_id, slots in flow_slots_after.items():
                            print(f"    {flow_id}: {slots}")
                    else:
                        print(f"  {C.R}No flow_slots!{C.E}")

        # Get final response
        final_snapshot = await runtime.graph.aget_state(config)
        if final_snapshot and final_snapshot.values:
            final_state = state_from_dict(final_snapshot.values, allow_partial=True)
            response = final_state.get("last_response", "")
            print(f"\n{C.G}Final Response: {response}{C.E}\n")
    except Exception as e:
        print(f"{C.R}Error during execution: {e}{C.E}\n")
        import traceback

        traceback.print_exc()

    # Capture final state
    final_snapshot = await runtime.graph.aget_state(config)
    if final_snapshot and final_snapshot.values:
        final_state = state_from_dict(final_snapshot.values, allow_partial=True)
        print_state_analysis(final_state, "FINAL STATE")

    # Analysis
    print_section("ANALYSIS")

    if initial_snapshot and final_snapshot:
        initial_state = (
            state_from_dict(initial_snapshot.values, allow_partial=True)
            if initial_snapshot.values
            else {}
        )
        final_state = (
            state_from_dict(final_snapshot.values, allow_partial=True)
            if final_snapshot.values
            else {}
        )

        initial_slots = get_all_slots(initial_state)
        final_slots = get_all_slots(final_state)

        nlu_result = final_state.get("nlu_result", {})
        extracted_slots = {}
        if nlu_result:
            slots_from_nlu = nlu_result.get("slots", [])
            for slot in slots_from_nlu:
                if isinstance(slot, dict):
                    extracted_slots[slot.get("name")] = slot.get("value")

        print(f"{C.Y}Slots Analysis:{C.E}")
        print(f"  Initial slots: {initial_slots}")
        print(f"  Extracted by NLU: {extracted_slots}")
        print(f"  Final slots: {final_slots}")

        # Check for lost slots
        lost_slots = set(extracted_slots.keys()) - set(final_slots.keys())
        if lost_slots:
            print(f"\n{C.R}⚠ LOST SLOTS: {lost_slots}{C.E}")
            print("  These slots were extracted by NLU but are missing in final state!")

            # Analyze node-by-node to find where slots were lost
            print(f"\n{C.Y}Node-by-node slot tracking:{C.E}")
            previous_slots = set(initial_slots.keys())
            for node_name, node_state in node_states:
                current_slots = set(get_all_slots(node_state).keys())
                if current_slots != previous_slots:
                    added = current_slots - previous_slots
                    removed = previous_slots - current_slots
                    if added:
                        print(f"  {C.G}+{node_name}: Added slots {added}{C.E}")
                    if removed:
                        print(f"  {C.R}-{node_name}: Removed slots {removed}{C.E}")
                    previous_slots = current_slots
                else:
                    print(f"  {C.DIM}{node_name}: No slot changes{C.E}")
        else:
            print(f"\n{C.G}✓ All extracted slots are present in final state{C.E}")

        # Check flow stack changes
        initial_stack = initial_state.get("flow_stack", [])
        final_stack = final_state.get("flow_stack", [])
        if len(initial_stack) != len(final_stack):
            print(f"\n{C.Y}Flow Stack Changed:{C.E}")
            print(f"  Initial: {len(initial_stack)} flows")
            print(f"  Final: {len(final_stack)} flows")
            if final_stack:
                print(f"  Active flow_id: {final_stack[-1].get('flow_id')}")
                print(f"  Active flow_name: {final_stack[-1].get('flow_name')}")

        # Check flow_slots structure
        initial_flow_slots = initial_state.get("flow_slots", {})
        final_flow_slots = final_state.get("flow_slots", {})
        print(f"\n{C.Y}Flow Slots Structure:{C.E}")
        print(f"  Initial flow_slots keys: {list(initial_flow_slots.keys())}")
        print(f"  Final flow_slots keys: {list(final_flow_slots.keys())}")
        for flow_id, slots in final_flow_slots.items():
            print(f"  {flow_id}: {slots}")


async def main():
    """Main analysis function."""
    # Configure DSPy
    api_key = os.getenv("OPENAI_API_KEY")
    if api_key:
        lm = dspy.LM("openai/gpt-4o-mini", api_key=api_key)
        dspy.configure(lm=lm)
    else:
        print(f"{C.R}ERROR: OPENAI_API_KEY not found{C.E}")
        return

    print(f"{C.H}{C.BOLD}")
    print("=" * 80)
    print("  SLOT LOSS ANALYSIS TOOL")
    print("=" * 80)
    print(f"{C.E}")

    # Initialize runtime
    config_path = Path("examples/flight_booking/soni.yaml")
    runtime = RuntimeLoop(config_path)
    runtime.config.settings.persistence.backend = "memory"
    await runtime._ensure_graph_initialized()

    # Test case: Multiple slots in one message
    user_id = f"analysis_{int(asyncio.get_event_loop().time())}"
    user_message = "I want to fly from New York to Los Angeles"

    await trace_execution(runtime, user_message, user_id)

    await runtime.cleanup()


if __name__ == "__main__":
    # Suppress library logs for cleaner output
    import logging

    logging.basicConfig(level=logging.WARNING)
    logging.getLogger("soni").setLevel(logging.INFO)  # Keep INFO for debugging

    asyncio.run(main())
