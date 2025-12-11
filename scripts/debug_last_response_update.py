"""Debug script to investigate last_response update issue.

This script creates a minimal reproduction of the problem where:
1. validate_slot clears user_message
2. collect_next_slot sets last_response to next slot prompt
3. generate_response should read the updated last_response
But generate_response reads the OLD last_response instead of the new one.
"""

import asyncio
import logging
from typing import Any

from langgraph.checkpoint.memory import MemorySaver
from langgraph.graph import StateGraph

from soni.core.types import DialogueState

# Configure logging
logging.basicConfig(level=logging.DEBUG, format="%(levelname)s [%(name)s] %(message)s")
logger = logging.getLogger(__name__)


# Simplified nodes
async def node_a(state: DialogueState) -> dict[str, Any]:
    """Simulates validate_slot: clears user_message."""
    logger.info("=== NODE A (validate_slot) ===")
    logger.info(f"  Input last_response: {state.get('last_response')}")
    logger.info(f"  Input user_message: {state.get('user_message')}")

    result = {
        "user_message": "",  # Clear user_message like validate_slot does
        "conversation_state": "waiting_for_slot",
    }

    logger.info(f"  Returns: {result}")
    return result


async def node_b(state: DialogueState) -> dict[str, Any]:
    """Simulates collect_next_slot: sets last_response to new prompt."""
    logger.info("=== NODE B (collect_next_slot) ===")
    logger.info(f"  Input last_response: {state.get('last_response')}")
    logger.info(f"  Input user_message: {state.get('user_message')}")
    logger.info(f"  Input current_prompted_slot: {state.get('current_prompted_slot')}")

    # Simulate the transition detection (lines 105-112 in collect_next_slot.py)
    current_prompted_slot = state.get("current_prompted_slot")
    next_slot = "destination"

    result = {
        "last_response": "Where would you like to go?",  # New prompt
        "waiting_for_slot": next_slot,
        "current_prompted_slot": next_slot,
        "conversation_state": "waiting_for_slot",
    }

    logger.info(f"  Transitioning from '{current_prompted_slot}' to '{next_slot}'")
    logger.info(f"  Returns: {result}")
    return result


async def node_c(state: DialogueState) -> dict[str, Any]:
    """Simulates generate_response: reads last_response."""
    logger.info("=== NODE C (generate_response) ===")
    logger.info(f"  Input last_response: {state.get('last_response')}")
    logger.info(f"  Input user_message: {state.get('user_message')}")
    logger.info(f"  Input waiting_for_slot: {state.get('waiting_for_slot')}")
    logger.info(f"  Input current_prompted_slot: {state.get('current_prompted_slot')}")

    # This is what generate_response does (via ResponseGenerator)
    existing_response = state.get("last_response", "")

    logger.info(f"  Read last_response: '{existing_response}'")
    logger.info("  EXPECTED: 'Where would you like to go?' (from collect_next_slot)")

    if existing_response != "Where would you like to go?":
        logger.error(
            "  ❌ BUG: generate_response read OLD last_response "
            "instead of the new one from collect_next_slot!"
        )
    else:
        logger.info("  ✅ OK: generate_response read the correct last_response")

    return {
        "last_response": existing_response,
        "conversation_state": "idle",
    }


def route_after_a(state: DialogueState) -> str:
    """Route after node_a (validate_slot)."""
    conv_state = state.get("conversation_state")
    logger.info(f"  ROUTING after node_a: conversation_state={conv_state}")
    if conv_state == "waiting_for_slot":
        return "node_b"
    return "node_c"


def route_after_b(state: DialogueState) -> str:
    """Route after node_b (collect_next_slot)."""
    conv_state = state.get("conversation_state")
    user_message = state.get("user_message", "")
    logger.info(
        f"  ROUTING after node_b: conversation_state={conv_state}, user_message='{user_message}'"
    )

    # This is what route_after_collect_next_slot does (lines 555-568)
    if conv_state == "waiting_for_slot":
        if user_message and user_message.strip():
            return "understand"  # Not relevant for this test
        else:
            # No user message - generate response
            logger.info("    → Going to node_c (generate_response)")
            return "node_c"
    return "node_c"


async def main() -> None:
    """Run the test."""
    # Build graph
    builder = StateGraph(DialogueState)
    builder.add_node("node_a", node_a)
    builder.add_node("node_b", node_b)
    builder.add_node("node_c", node_c)

    builder.set_entry_point("node_a")
    builder.add_conditional_edges("node_a", route_after_a, {"node_b": "node_b", "node_c": "node_c"})
    builder.add_conditional_edges("node_b", route_after_b, {"node_c": "node_c"})
    builder.add_edge("node_c", "__end__")

    # Compile with checkpointer
    checkpointer = MemorySaver()
    graph = builder.compile(checkpointer=checkpointer)

    # Initial state: simulating after user provided "origin"
    initial_state: DialogueState = {
        "user_message": "San Francisco",  # User just provided origin
        "last_response": "Which city are you departing from?",  # Old prompt for origin
        "messages": [],
        "flow_stack": [],
        "flow_slots": {},
        "conversation_state": "waiting_for_slot",
        "current_step": None,
        "waiting_for_slot": "origin",
        "current_prompted_slot": "origin",  # We were asking for origin
    }

    logger.info("=" * 80)
    logger.info("INITIAL STATE:")
    logger.info(f"  last_response: '{initial_state['last_response']}'")
    logger.info(f"  user_message: '{initial_state['user_message']}'")
    logger.info(f"  current_prompted_slot: '{initial_state['current_prompted_slot']}'")
    logger.info("=" * 80)

    # Run graph
    config = {"configurable": {"thread_id": "test-1"}}
    final_state = await graph.ainvoke(initial_state, config)

    logger.info("=" * 80)
    logger.info("FINAL STATE:")
    logger.info(f"  last_response: '{final_state.get('last_response')}'")
    logger.info(f"  user_message: '{final_state.get('user_message')}'")
    logger.info(f"  waiting_for_slot: '{final_state.get('waiting_for_slot')}'")
    logger.info(f"  current_prompted_slot: '{final_state.get('current_prompted_slot')}'")
    logger.info("=" * 80)


if __name__ == "__main__":
    asyncio.run(main())
