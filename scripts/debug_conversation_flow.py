#!/usr/bin/env python3
"""
Conversation Flow Debugger for Soni Framework.

This script simulates a conversation with the Soni system and visualizes
the internal state changes, NLU results, and flow transitions at each step.
It is designed to show "how the gears work" for debugging and demonstration.
"""

import asyncio
import json
import logging
import os
import sys
from datetime import datetime
from pathlib import Path
from typing import Any

import dspy

# Add src to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

try:
    from dotenv import load_dotenv

    load_dotenv()
except ImportError:
    pass

from soni.core.state import DialogueState, get_all_slots, state_from_dict
from soni.runtime import RuntimeLoop

# Configure logging to be less noisy for libraries, but clear for our script
logging.basicConfig(level=logging.WARNING)
logger = logging.getLogger("soni_debugger")
logger.setLevel(logging.INFO)


# ANSI Colors for terminal output
class Colors:
    HEADER = "\033[95m"
    BLUE = "\033[94m"
    CYAN = "\033[96m"
    GREEN = "\033[92m"
    YELLOW = "\033[93m"
    RED = "\033[91m"
    ENDC = "\033[0m"
    BOLD = "\033[1m"
    UNDERLINE = "\033[4m"


def print_header(text: str):
    print(f"\n{Colors.HEADER}{Colors.BOLD}=== {text} ==={Colors.ENDC}")


def print_section(text: str):
    print(f"\n{Colors.CYAN}>> {text}{Colors.ENDC}")


def print_info(label: str, value: Any):
    print(f"{Colors.BLUE}{label}:{Colors.ENDC} {value}")


def print_success(text: str):
    print(f"{Colors.GREEN}✓ {text}{Colors.ENDC}")


def print_warning(text: str):
    print(f"{Colors.YELLOW}⚠ {text}{Colors.ENDC}")


def format_json(data: Any) -> str:
    return json.dumps(data, indent=2, default=str)


async def debug_conversation():
    print_header("SONI SYSTEM DEBUGGER - CONVERSATION SIMULATION")

    # 1. Initialization
    print_section("GEAR 1: INITIALIZATION")
    config_path = Path("examples/flight_booking/soni.yaml")
    print_info("Configuration", config_path)

    # Configure DSPy
    api_key = os.getenv("OPENAI_API_KEY")
    if api_key:
        lm = dspy.LM("openai/gpt-4o-mini", api_key=api_key)
        dspy.configure(lm=lm)
        print_success("DSPy configured with OpenAI (gpt-4o-mini)")
    else:
        print_warning("OPENAI_API_KEY not found. NLU might fail or use mock.")

    # Initialize Runtime
    try:
        runtime = RuntimeLoop(config_path)
        # Use sqlite backend for debugging to ensure persistence works as expected
        runtime.config.settings.persistence.backend = "sqlite"
        runtime.config.settings.persistence.path = (
            f"./debug_state_{int(datetime.now().timestamp())}.db"
        )

        await runtime._ensure_graph_initialized()
        print_success("RuntimeLoop initialized")
        print_success(f"Checkpointer type: {type(runtime.builder.checkpointer)}")
        print_success(f"DB Path: {runtime.config.settings.persistence.path}")
        print_success("Graph built and validated")
    except Exception as e:
        print(f"{Colors.RED}Initialization Failed: {e}{Colors.ENDC}")
        return

    # Define Conversation Scenario
    user_id = f"debug_user_{int(datetime.now().timestamp())}"
    conversation_turns = [
        "I want to book a flight",
        "New York",
        "Los Angeles",
        "Next Friday",
    ]

    print_header("STARTING SIMULATION")
    print_info("User ID", user_id)
    print_info("Scenario", f"{len(conversation_turns)} turns planned")

    for i, user_msg in enumerate(conversation_turns, 1):
        print_header(f"TURN {i}")

        # 2. User Input
        print_section("GEAR 2: USER INPUT")
        print(f"User says: {Colors.BOLD}'{user_msg}'{Colors.ENDC}")

        # Get Pre-Execution State
        config = {"configurable": {"thread_id": user_id}}
        state_snapshot_before = await runtime.graph.aget_state(config)
        slots_before = {}
        if state_snapshot_before and state_snapshot_before.values:
            # Use allow_partial=True to be robust against partial state updates
            state_before = state_from_dict(state_snapshot_before.values, allow_partial=True)
            slots_before = get_all_slots(state_before)

        # 3. Processing
        print_section("GEAR 3: PROCESSING (RUNTIME LOOP)")
        print("Invoking RuntimeLoop.process_message()...")
        start_time = datetime.now()

        try:
            response = await runtime.process_message(user_msg, user_id)
            duration = (datetime.now() - start_time).total_seconds()
            print_success(f"Processed in {duration:.2f}s")
        except Exception as e:
            print(f"{Colors.RED}Processing Error: {e}{Colors.ENDC}")
            import traceback

            traceback.print_exc()
            break

        # 4. Internal Inspection (Post-Execution)
        print_section("GEAR 4: INTERNAL INSPECTION")

        # Fetch updated state
        state_snapshot = await runtime.graph.aget_state(config)
        # Debug: Print raw snapshot metadata to see if it's finding anything
        # print(f"Debug Snapshot: {state_snapshot}")

        if not state_snapshot or not state_snapshot.values:
            print_warning("No state found after execution!")
            continue

        current_state = state_from_dict(state_snapshot.values, allow_partial=True)

        # Inspect NLU (from State or Trace)
        # Assuming trace contains 'nlu_result' event or similar
        nlu_trace = next(
            (t for t in reversed(current_state.get("trace", [])) if t.get("event") == "nlu_result"),
            None,
        )

        if nlu_trace:
            data = nlu_trace.get("data", {})
            print(f"{Colors.YELLOW}[NLU DETECTED]{Colors.ENDC}")
            print(f"  Intent: {Colors.BOLD}{data.get('intent')}{Colors.ENDC}")
            print(f"  Slots: {format_json(data.get('slots', {}))}")
        else:
            # Fallback: Check explicit nlu_result field if exists in state
            nlu_res = current_state.get("nlu_result")
            if nlu_res:
                print(f"{Colors.YELLOW}[NLU RESULT]{Colors.ENDC}")
                # Handle if it's an object or dict
                if hasattr(nlu_res, "intent"):
                    print(f"  Intent: {Colors.BOLD}{nlu_res.intent}{Colors.ENDC}")
                    print(f"  Slots: {nlu_res.slots}")
                else:
                    print(f"  Raw: {nlu_res}")
            else:
                print_warning("No NLU trace found")

        # Inspect Flow Stack
        print(f"\n{Colors.YELLOW}[FLOW STATE]{Colors.ENDC}")
        flow_stack = current_state.get("flow_stack", [])
        if flow_stack:
            active = flow_stack[-1]
            print(f"  Active Flow: {Colors.BOLD}{active.get('flow_name')}{Colors.ENDC}")
            print(f"  Step: {active.get('current_step')}")
            print(f"  Stack Depth: {len(flow_stack)}")
        else:
            print("  Stack: [Empty]")

        # Inspect Slots Changes
        # Extract current slots logic again
        slots_after = get_all_slots(current_state)

        new_slots = {
            k: v for k, v in slots_after.items() if k not in slots_before or slots_before[k] != v
        }

        if new_slots:
            print(f"\n{Colors.YELLOW}[MEMORY UPDATES]{Colors.ENDC}")
            for k, v in new_slots.items():
                print(f"  + {k}: {Colors.GREEN}{v}{Colors.ENDC}")
        else:
            print(f"\n{Colors.YELLOW}[MEMORY]{Colors.ENDC} No changes this turn")

        # 5. Response
        print_section("GEAR 5: SYSTEM RESPONSE")
        print(f"🤖 Agent: {Colors.BOLD}{response}{Colors.ENDC}")

    # Cleanup
    await runtime.cleanup()
    # Clean up db file
    try:
        if os.path.exists(runtime.config.settings.persistence.path):
            os.remove(runtime.config.settings.persistence.path)
            print_success("Cleaned up temp database")
    except Exception as e:
        print_warning(f"Could not delete temp db: {e}")

    print_header("SIMULATION COMPLETE")


if __name__ == "__main__":
    asyncio.run(debug_conversation())
