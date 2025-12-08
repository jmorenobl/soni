#!/usr/bin/env python3
"""
Soni Framework - Scenario-Based Debugger

This script tests different conversation scenarios from simple to complex,
showing internal state at each step.

Run with: uv run python scripts/debug_scenarios.py [scenario_number]

Scenarios:
  1. Simple: Complete flight booking flow
  2. Medium: Slot correction mid-flow
  3. Complex: Digression (question) then continue
  4. Edge: Cancel and restart
"""

import asyncio
import json
import os
import sys
from dataclasses import dataclass
from datetime import datetime
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


@dataclass
class TestTurn:
    """A single turn in a test scenario."""

    user_input: str
    description: str
    expected_flow: str | None = None
    expected_slots: dict[str, str] | None = None
    expected_response_contains: str | None = None


@dataclass
class TestScenario:
    """A complete test scenario."""

    name: str
    description: str
    turns: list[TestTurn]


# =============================================================================
# TEST SCENARIOS
# =============================================================================

SCENARIOS: list[TestScenario] = [
    # Scenario 1: Simple complete flow
    TestScenario(
        name="Simple: Complete Flight Booking",
        description="Happy path - user provides all slots in sequence",
        turns=[
            TestTurn(
                "I want to book a flight",
                "Trigger book_flight flow",
                expected_flow="book_flight",
            ),
            TestTurn(
                "Madrid",
                "Provide origin",
                expected_slots={"origin": "Madrid"},
            ),
            TestTurn(
                "Barcelona",
                "Provide destination",
                expected_slots={"origin": "Madrid", "destination": "Barcelona"},
            ),
            TestTurn(
                "Tomorrow",
                "Provide date",
                expected_slots={"origin": "Madrid", "destination": "Barcelona"},
            ),
        ],
    ),
    # Scenario 2: Provide multiple slots at once
    TestScenario(
        name="Medium: Multiple Slots at Once",
        description="User provides multiple pieces of info in one message",
        turns=[
            TestTurn(
                "I want to fly from New York to Los Angeles",
                "Trigger flow with origin and destination",
                expected_flow="book_flight",
            ),
            TestTurn(
                "Next Friday",
                "Provide date to complete",
            ),
        ],
    ),
    # Scenario 3: Correction mid-flow
    TestScenario(
        name="Medium: Slot Correction",
        description="User corrects a previously provided slot",
        turns=[
            TestTurn(
                "Book a flight",
                "Trigger flow",
                expected_flow="book_flight",
            ),
            TestTurn(
                "Chicago",
                "Provide origin",
                expected_slots={"origin": "Chicago"},
            ),
            TestTurn(
                "Actually, I meant Denver not Chicago",
                "Correct origin slot",
            ),
            TestTurn(
                "Seattle",
                "Provide destination",
            ),
        ],
    ),
    # Scenario 4: Question (digression)
    TestScenario(
        name="Complex: Digression Question",
        description="User asks a question mid-flow without changing flow",
        turns=[
            TestTurn(
                "I want to book a flight",
                "Trigger flow",
                expected_flow="book_flight",
            ),
            TestTurn(
                "San Francisco",
                "Provide origin",
            ),
            TestTurn(
                "What airports do you support?",
                "Question - should be digression, not change flow",
                expected_flow="book_flight",  # Should stay in flow
            ),
            TestTurn(
                "Miami",
                "Continue with destination after digression",
            ),
        ],
    ),
    # Scenario 5: Cancel
    TestScenario(
        name="Edge: Cancel Flow",
        description="User cancels the flow mid-way",
        turns=[
            TestTurn(
                "Book a flight please",
                "Trigger flow",
                expected_flow="book_flight",
            ),
            TestTurn(
                "Boston",
                "Provide origin",
            ),
            TestTurn(
                "Actually, cancel this",
                "Cancel the flow",
            ),
            TestTurn(
                "I want to book a new flight",
                "Start fresh",
            ),
        ],
    ),
]


# =============================================================================
# DEBUG RUNNER
# =============================================================================


async def run_scenario(
    runtime: RuntimeLoop, scenario: TestScenario, user_id: str
) -> dict[str, Any]:
    """Run a single scenario and collect results."""

    print(f"\n{C.H}{C.BOLD}{'=' * 70}{C.E}")
    print(f"{C.H}{C.BOLD}  SCENARIO: {scenario.name}{C.E}")
    print(f"{C.H}{C.BOLD}{'=' * 70}{C.E}")
    print(f"{C.DIM}{scenario.description}{C.E}\n")

    results = {
        "scenario": scenario.name,
        "turns": [],
        "success": True,
        "errors": [],
    }

    for i, turn in enumerate(scenario.turns, 1):
        print(f"{C.C}{'─' * 60}{C.E}")
        print(f"{C.BOLD}Turn {i}: {turn.description}{C.E}")
        print(f'{C.B}User:{C.E} "{turn.user_input}"')

        turn_result = {
            "turn": i,
            "input": turn.user_input,
            "expected": {},
            "actual": {},
            "passed": True,
        }

        try:
            # Process message
            start = datetime.now()
            response = await runtime.process_message(turn.user_input, user_id)
            latency = (datetime.now() - start).total_seconds()

            # Get state
            config = {"configurable": {"thread_id": user_id}}
            snapshot = await runtime.graph.aget_state(config)

            # Show NLU result if available
            if snapshot and snapshot.values:
                nlu_result = snapshot.values.get("nlu_result")
                if nlu_result:
                    print(f"\n{C.Y}NLU Output:{C.E}")
                    print(f"  Type: {nlu_result.get('message_type', 'N/A')}")
                    print(f"  Command: {nlu_result.get('command', 'N/A')}")
                    slots_from_nlu = nlu_result.get("slots", [])
                    if slots_from_nlu:
                        print("  Extracted slots:")
                        for slot in slots_from_nlu:
                            if isinstance(slot, dict):
                                print(
                                    f"    - {slot.get('name')}: {slot.get('value')} (conf: {slot.get('confidence', 'N/A')})"
                                )
                            else:
                                print(f"    - {slot}")
                    # Reasoning field has been removed from NLUOutput

            if snapshot and snapshot.values:
                state = state_from_dict(snapshot.values, allow_partial=True)
                current_flow = get_current_flow(state)
                slots = get_all_slots(state)
                stack_depth = len(state.get("flow_stack", []))

                # Show actual state
                print(f"\n{C.Y}State:{C.E}")
                print(f"  Flow: {C.BOLD}{current_flow}{C.E} (stack depth: {stack_depth})")
                print(f"  Current Step: {state.get('current_step', 'None')}")
                print(f"  Conversation State: {state.get('conversation_state', 'N/A')}")
                print(f"  Waiting for Slot: {state.get('waiting_for_slot', 'None')}")
                print(f"  Current Prompted Slot: {state.get('current_prompted_slot', 'None')}")
                print(f"  All Slots Filled: {state.get('all_slots_filled', False)}")
                print(f"  Slots: {json.dumps(slots, indent=2) if slots else '{}'}")

                # Show last 3 trace events
                trace = state.get("trace", [])
                if trace:
                    print(f"\n{C.Y}Last Trace Events:{C.E}")
                    for event in trace[-3:]:
                        event_type = event.get("event", "unknown")
                        event_data = event.get("data", {})
                        # Convert to JSON-safe format
                        try:
                            safe_data = json.dumps(event_data, indent=4, default=str)[:200]
                        except (TypeError, ValueError):
                            safe_data = str(event_data)[:200]
                        print(f"  - {event_type}: {safe_data}...")

                print(f"  Latency: {latency:.2f}s")

                turn_result["actual"] = {
                    "flow": current_flow,
                    "slots": slots,
                    "stack_depth": stack_depth,
                }

                # Check expectations
                checks = []

                if turn.expected_flow is not None:
                    turn_result["expected"]["flow"] = turn.expected_flow
                    if current_flow == turn.expected_flow:
                        checks.append(f"{C.G}✓ Flow matches{C.E}")
                    else:
                        checks.append(
                            f"{C.R}✗ Flow mismatch: expected '{turn.expected_flow}', got '{current_flow}'{C.E}"
                        )
                        turn_result["passed"] = False
                        results["success"] = False

                if turn.expected_slots is not None:
                    turn_result["expected"]["slots"] = turn.expected_slots
                    slots_match = all(slots.get(k) == v for k, v in turn.expected_slots.items())
                    if slots_match:
                        checks.append(f"{C.G}✓ Expected slots present{C.E}")
                    else:
                        checks.append(f"{C.R}✗ Slot mismatch{C.E}")
                        turn_result["passed"] = False
                        results["success"] = False

                if turn.expected_response_contains is not None:
                    if turn.expected_response_contains.lower() in response.lower():
                        checks.append(f"{C.G}✓ Response contains expected text{C.E}")
                    else:
                        checks.append(f"{C.R}✗ Response missing expected text{C.E}")
                        turn_result["passed"] = False
                        results["success"] = False

                if checks:
                    print(f"\n{C.Y}Checks:{C.E}")
                    for check in checks:
                        print(f"  {check}")

            # Show response
            print(f'\n{C.G}Agent:{C.E} "{response}"')
            turn_result["response"] = response

        except Exception as e:
            print(f"\n{C.R}ERROR: {e}{C.E}")
            turn_result["error"] = str(e)
            turn_result["passed"] = False
            results["success"] = False
            results["errors"].append(str(e))

        results["turns"].append(turn_result)

    # Summary
    passed = sum(1 for t in results["turns"] if t["passed"])
    total = len(results["turns"])
    status = f"{C.G}PASSED{C.E}" if results["success"] else f"{C.R}FAILED{C.E}"

    print(f"\n{C.C}{'─' * 60}{C.E}")
    print(f"{C.BOLD}Scenario Result: {status} ({passed}/{total} turns){C.E}")

    return results


async def main():
    # Configure DSPy
    api_key = os.getenv("OPENAI_API_KEY")
    if api_key:
        lm = dspy.LM("openai/gpt-4o-mini", api_key=api_key)
        dspy.configure(lm=lm)
    else:
        print(f"{C.R}ERROR: OPENAI_API_KEY not found{C.E}")
        return

    # Parse arguments
    if len(sys.argv) > 1:
        try:
            scenario_num = int(sys.argv[1])
            if 1 <= scenario_num <= len(SCENARIOS):
                scenarios_to_run = [SCENARIOS[scenario_num - 1]]
            else:
                print(f"{C.R}Invalid scenario number. Choose 1-{len(SCENARIOS)}{C.E}")
                return
        except ValueError:
            print(
                f"{C.R}Invalid argument. Use: python debug_scenarios.py [1-{len(SCENARIOS)}]{C.E}"
            )
            return
    else:
        scenarios_to_run = SCENARIOS

    print(f"{C.H}{C.BOLD}")
    print("=" * 70)
    print("  SONI FRAMEWORK - SCENARIO DEBUGGER")
    print("=" * 70)
    print(f"{C.E}")

    print(f"{C.B}Available scenarios:{C.E}")
    for i, s in enumerate(SCENARIOS, 1):
        marker = "→" if s in scenarios_to_run else " "
        print(f"  {marker} {i}. {s.name}")

    # Initialize runtime
    config_path = Path("examples/flight_booking/soni.yaml")
    runtime = RuntimeLoop(config_path)
    runtime.config.settings.persistence.backend = "memory"
    await runtime._ensure_graph_initialized()

    # Show configuration
    use_reasoning = getattr(runtime.config.settings.models.nlu, "use_reasoning", False)
    use_cot = getattr(runtime.du, "use_cot", None)
    print(f"\n{C.B}Configuration:{C.E}")
    print(f"  use_reasoning (YAML): {C.BOLD}{use_reasoning}{C.E}")
    print(f"  use_cot (SoniDU): {C.BOLD}{use_cot}{C.E}")
    if use_reasoning != use_cot:
        print(f"  {C.Y}⚠ Warning: use_reasoning != use_cot{C.E}")
    print()

    # Run scenarios
    all_results = []
    for scenario in scenarios_to_run:
        user_id = f"test_{scenario.name.replace(' ', '_').replace(':', '')}_{int(datetime.now().timestamp())}"
        result = await run_scenario(runtime, scenario, user_id)
        all_results.append(result)

    # Final summary
    print(f"\n{C.H}{C.BOLD}{'=' * 70}{C.E}")
    print(f"{C.H}{C.BOLD}  FINAL SUMMARY{C.E}")
    print(f"{C.H}{C.BOLD}{'=' * 70}{C.E}\n")

    for result in all_results:
        status = f"{C.G}PASSED{C.E}" if result["success"] else f"{C.R}FAILED{C.E}"
        print(f"  {status} - {result['scenario']}")
        if result["errors"]:
            for err in result["errors"]:
                print(f"    {C.R}Error: {err}{C.E}")

    passed = sum(1 for r in all_results if r["success"])
    total = len(all_results)
    print(f"\n{C.BOLD}Total: {passed}/{total} scenarios passed{C.E}")

    await runtime.cleanup()


if __name__ == "__main__":
    # Suppress library logs for cleaner output
    import logging

    logging.basicConfig(level=logging.WARNING)
    logging.getLogger("soni").setLevel(logging.WARNING)

    asyncio.run(main())
