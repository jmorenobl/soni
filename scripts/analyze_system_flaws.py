#!/usr/bin/env python3
"""
Soni Framework - Deep System Analysis & Flaw Detection
========================================================

This script performs an in-depth analysis of the Soni system to identify
architectural flaws, bugs, and potential improvements.

Run with: uv run python scripts/analyze_system_flaws.py
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

from soni.core.state import (
    DialogueState,
    add_message,
    create_initial_state,
    get_all_slots,
    get_current_flow,
    state_from_dict,
)
from soni.runtime import RuntimeLoop

# Suppress noise, show only our analysis
logging.basicConfig(level=logging.WARNING)
logging.getLogger("soni").setLevel(logging.DEBUG)


# ANSI Colors
class C:
    H = "\033[95m"  # Header
    B = "\033[94m"  # Blue
    C = "\033[96m"  # Cyan
    G = "\033[92m"  # Green
    Y = "\033[93m"  # Yellow
    R = "\033[91m"  # Red
    E = "\033[0m"  # End
    BOLD = "\033[1m"
    UL = "\033[4m"  # Underline


def header(text: str):
    print(f"\n{C.H}{C.BOLD}{'=' * 70}{C.E}")
    print(f"{C.H}{C.BOLD}  {text}{C.E}")
    print(f"{C.H}{C.BOLD}{'=' * 70}{C.E}")


def section(text: str):
    print(f"\n{C.C}{C.UL}>> {text}{C.E}")


def bug(id: str, title: str):
    print(f"\n{C.R}{C.BOLD}[BUG {id}] {title}{C.E}")


def finding(text: str):
    print(f"  {C.Y}→ {text}{C.E}")


def evidence(text: str):
    print(f"  {C.B}  Evidence: {text}{C.E}")


def fix(text: str):
    print(f"  {C.G}  Fix: {text}{C.E}")


def code(text: str):
    print(f"  {C.C}  ```\n  {text}\n  ```{C.E}")


async def analyze_bug_1_initial_message():
    """BUG 1: Initial message not added to messages list"""
    bug("001", "Initial message not added to `messages` list")

    finding("create_initial_state() sets user_message field but doesn't add to messages[]")

    # Demonstrate the bug
    test_state = create_initial_state("Hello world")

    evidence(f"user_message field: '{test_state['user_message']}'")
    evidence(f"messages list: {test_state['messages']} (EMPTY!)")

    # Show what understand_node sees
    from soni.core.state import get_user_messages

    user_msgs = get_user_messages(test_state)
    evidence(f"get_user_messages() returns: {user_msgs}")

    fix("Add add_message(state, 'user', user_message) to create_initial_state()")

    code("""
# In src/soni/core/state.py create_initial_state():
def create_initial_state(user_message: str) -> DialogueState:
    state = create_empty_state()
    state["user_message"] = user_message
    add_message(state, "user", user_message)  # <-- ADD THIS LINE
    ...
""")
    return True


async def analyze_bug_2_flow_activation():
    """BUG 2: Flow not activated on intent trigger"""
    bug("002", "Flow not activated when intent matches flow name")

    finding("activate_flow_by_intent() only matches exact flow names")
    finding("NLU returns commands like 'start_book_flight' not 'book_flight'")

    # Show the problematic code
    code("""
# In src/soni/dm/routing.py:
def activate_flow_by_intent(command, current_flow, config):
    if command in config.flows:  # Only exact match works!
        return command
    return current_flow
""")

    evidence("NLU command: 'start_book_flight' != 'book_flight' (flow name)")
    evidence("Result: Flow stack remains empty, no context for slot mapping")

    fix("Normalize command names: strip 'start_' prefix, handle variations")

    code("""
# Improved activate_flow_by_intent():
def activate_flow_by_intent(command, current_flow, config):
    if not command:
        return current_flow

    # Direct match
    if command in config.flows:
        return command

    # Handle 'start_<flow>' pattern
    if command.startswith("start_"):
        flow_name = command[6:]  # Remove 'start_' prefix
        if flow_name in config.flows:
            return flow_name

    return current_flow
""")
    return True


async def analyze_bug_3_slot_name_mismatch():
    """BUG 3: NLU extracts slots with wrong names"""
    bug("003", "NLU extracts slots with generic names instead of config-defined names")

    finding("NLU extracts: location, destination, date")
    finding("Flow expects: origin, destination, departure_date")
    finding("SlotValue model says 'must match expected_slots' but LLM ignores it")

    evidence("Log: Extracted slots: {'location': 'New York'}")
    evidence("Config expects: origin, destination, departure_date")
    evidence("Result: collect_slot_node checks 'origin' but finds nothing")

    fix("Option 1: Improve NLU prompt to emphasize slot name matching")
    fix("Option 2: Add slot name canonicalization/remapping layer")
    fix("Option 3: Make collect_slot_node more flexible in matching")

    code("""
# Option 2: Add slot canonicalization in understand_node
SLOT_ALIASES = {
    "location": "origin",
    "city": "origin",
    "from": "origin",
    "to": "destination",
    "date": "departure_date",
    "travel_date": "departure_date",
}

def canonicalize_slot_name(name: str, expected_slots: list[str]) -> str:
    # Direct match
    if name in expected_slots:
        return name
    # Alias match
    if name in SLOT_ALIASES and SLOT_ALIASES[name] in expected_slots:
        return SLOT_ALIASES[name]
    # Fuzzy match (e.g., 'origin' in 'origin_city')
    for expected in expected_slots:
        if name in expected or expected in name:
            return expected
    return name  # Keep original if no match
""")
    return True


async def analyze_bug_4_keyerror_swallowed():
    """BUG 4: Slot normalization KeyError silently swallowed"""
    bug("004", "Unknown slot names bypass validation silently")

    finding("When NLU extracts slot not in config, KeyError is caught and swallowed")
    finding("Unknown slots stored with wrong names, breaking downstream logic")

    code("""
# In src/soni/dm/nodes/factories.py understand_node():
for slot_name, slot_value in normalized_slots.items():
    try:
        slot_config = get_slot_config(context, slot_name)
        # ... normalize ...
    except KeyError:
        normalized_dict[slot_name] = slot_value  # Silently keeps bad name!
""")

    evidence("NLU extracts 'location', config only has 'origin'")
    evidence("KeyError caught, 'location' stored as-is")
    evidence("Later: get_slot(state, 'origin') returns None")

    fix("Log warning when unknown slot encountered")
    fix("Attempt canonicalization before storing")

    return True


async def analyze_bug_5_graph_continuity():
    """BUG 5: Graph execution continuity issues"""
    bug("005", "Graph re-executes from START on each message without proper context")

    finding("Each message triggers graph.ainvoke() from START")
    finding("State is loaded from checkpoint, but flow_stack often empty (Bug 2)")
    finding("Without flow context, expected_slots is empty, NLU has no guidance")

    code("""
# In runtime.py _execute_graph():
result_raw = await self.graph.ainvoke(
    state_to_dict(state),  # State has no flow_stack!
    config=config,
)
# Graph starts at START -> understand -> collect_origin
# But understand has no flow context, so expected_slots = []
""")

    evidence("Turn 1: flow_stack=[], expected_slots=[]")
    evidence("Turn 2+: flow_stack still [] because flow never pushed (Bug 2)")
    evidence("NLU receives no guidance on expected slot names")

    fix("Ensure flow is pushed on first intent detection")
    fix("Persist flow_stack correctly in checkpoint")

    return True


async def analyze_system_live():
    """Live system analysis with actual conversation"""
    section("LIVE SYSTEM ANALYSIS")

    config_path = Path("examples/flight_booking/soni.yaml")

    # Configure DSPy
    api_key = os.getenv("OPENAI_API_KEY")
    if api_key:
        lm = dspy.LM("openai/gpt-4o-mini", api_key=api_key)
        dspy.configure(lm=lm)
    else:
        print(f"{C.Y}⚠ OPENAI_API_KEY not found - skipping live analysis{C.E}")
        return

    runtime = RuntimeLoop(config_path)
    runtime.config.settings.persistence.backend = "memory"
    await runtime._ensure_graph_initialized()

    user_id = f"analysis_{int(datetime.now().timestamp())}"

    # Test sequence
    test_cases = [
        ("I want to book a flight", "Should trigger flow, push to stack"),
        ("New York", "Should be recognized as 'origin' slot"),
        ("Los Angeles", "Should be recognized as 'destination' slot"),
    ]

    print(f"\n{C.B}Testing with user_id: {user_id}{C.E}")

    for i, (msg, expected) in enumerate(test_cases, 1):
        print(f"\n{C.BOLD}Turn {i}: '{msg}'{C.E}")
        print(f"  Expected: {expected}")

        response = await runtime.process_message(msg, user_id)

        # Get state
        config = {"configurable": {"thread_id": user_id}}
        snapshot = await runtime.graph.aget_state(config)

        if snapshot and snapshot.values:
            state = state_from_dict(snapshot.values, allow_partial=True)
            flow = get_current_flow(state)
            slots = get_all_slots(state)
            stack_depth = len(state.get("flow_stack", []))

            print(f"  {C.Y}Actual:{C.E}")
            print(f"    Flow: {flow}")
            print(f"    Stack depth: {stack_depth}")
            print(f"    Slots: {slots}")
            print(f"    Response: {response[:60]}...")

            # Check for issues
            if i == 1 and stack_depth == 0:
                print(f"  {C.R}⚠ BUG: Flow not activated on first message!{C.E}")
            if i == 2 and "origin" not in slots and "location" not in slots:
                print(f"  {C.R}⚠ BUG: City not captured as any slot!{C.E}")
            elif i == 2 and "location" in slots and "origin" not in slots:
                print(f"  {C.R}⚠ BUG: Slot name mismatch (got 'location', expected 'origin'){C.E}")

    await runtime.cleanup()


async def main():
    header("SONI FRAMEWORK - DEEP SYSTEM ANALYSIS")

    print(f"""
{C.B}This analysis examines the internal workings of the Soni dialogue system
to identify architectural flaws, bugs, and potential improvements.{C.E}
""")

    section("STATIC CODE ANALYSIS - IDENTIFIED BUGS")

    await analyze_bug_1_initial_message()
    await analyze_bug_2_flow_activation()
    await analyze_bug_3_slot_name_mismatch()
    await analyze_bug_4_keyerror_swallowed()
    await analyze_bug_5_graph_continuity()

    section("IMPACT SUMMARY")
    print(f"""
{C.Y}The combination of these bugs creates a cascade failure:{C.E}

  1. First message: NLU skipped (no messages in list)
     → Flow not activated → flow_stack = []

  2. Subsequent messages: NLU runs but with empty expected_slots
     → LLM guesses slot names → Wrong names extracted

  3. Slot storage: Unknown slot names stored as-is
     → collect_slot_node looks for 'origin', finds nothing
     → System keeps prompting for 'origin' forever

{C.BOLD}Result: The conversation loop never progresses past first slot collection.{C.E}
""")

    await analyze_system_live()

    header("RECOMMENDATIONS")
    print(f"""
{C.G}Priority Fixes:{C.E}

1. {C.BOLD}[CRITICAL]{C.E} Fix create_initial_state() to add message to messages[]

2. {C.BOLD}[CRITICAL]{C.E} Fix activate_flow_by_intent() to handle 'start_<flow>' pattern

3. {C.BOLD}[HIGH]{C.E} Add slot name canonicalization layer

4. {C.BOLD}[MEDIUM]{C.E} Log warnings for unknown slot names

5. {C.BOLD}[LOW]{C.E} Improve NLU signature to emphasize exact slot name matching

{C.B}These fixes should restore the expected conversation flow.{C.E}
""")

    header("ANALYSIS COMPLETE")


if __name__ == "__main__":
    asyncio.run(main())
