"""Debug script to check if ResponseGenerator priorities are causing the issue.

Checks if confirmation slot or action_result is interfering with last_response.
"""

import asyncio
import logging
from typing import Any

from langgraph.checkpoint.memory import MemorySaver
from langgraph.graph import StateGraph

from soni.core.state import get_all_slots
from soni.core.types import DialogueState
from soni.utils.response_generator import ResponseGenerator

# Configure logging
logging.basicConfig(level=logging.DEBUG, format="%(levelname)s [%(name)s] %(message)s")
logger = logging.getLogger(__name__)


async def node_a(state: DialogueState) -> dict[str, Any]:
    """Simulates validate_slot."""
    logger.info("=== NODE A (validate_slot) ===")
    return {
        "user_message": "",
        "conversation_state": "waiting_for_slot",
        "flow_slots": {
            "book_flight_1": {
                "origin": "San Francisco",  # Just validated origin
            }
        },
    }


async def node_b(state: DialogueState) -> dict[str, Any]:
    """Simulates collect_next_slot."""
    logger.info("=== NODE B (collect_next_slot) ===")
    return {
        "last_response": "Where would you like to go?",
        "waiting_for_slot": "destination",
        "current_prompted_slot": "destination",
        "conversation_state": "waiting_for_slot",
    }


async def node_c(state: DialogueState) -> dict[str, Any]:
    """Simulates generate_response."""
    logger.info("=== NODE C (generate_response) ===")

    # Check what ResponseGenerator would return
    all_slots = get_all_slots(state)
    logger.info(f"  All slots: {all_slots}")
    logger.info(f"  last_response: '{state.get('last_response')}'")
    logger.info(f"  action_result: {state.get('action_result')}")
    logger.info(f"  confirmation slot: {all_slots.get('confirmation')}")

    # This is what generate_response does
    response = ResponseGenerator.generate_from_priority(state)

    logger.info(f"  ResponseGenerator returned: '{response}'")
    logger.info("  EXPECTED: 'Where would you like to go?'")

    if response != "Where would you like to go?":
        logger.error(
            f"  ❌ BUG: ResponseGenerator returned '{response}' instead of "
            f"the last_response from collect_next_slot!"
        )
    else:
        logger.info("  ✅ OK: ResponseGenerator returned the correct response")

    return {
        "last_response": response,
        "conversation_state": "idle",
    }


def route_after_a(state: DialogueState) -> str:
    return "node_b"


def route_after_b(state: DialogueState) -> str:
    return "node_c"


async def main() -> None:
    """Run the test."""
    # Build graph
    builder = StateGraph(DialogueState)
    builder.add_node("node_a", node_a)
    builder.add_node("node_b", node_b)
    builder.add_node("node_c", node_c)

    builder.set_entry_point("node_a")
    builder.add_conditional_edges("node_a", route_after_a, {"node_b": "node_b"})
    builder.add_conditional_edges("node_b", route_after_b, {"node_c": "node_c"})
    builder.add_edge("node_c", "__end__")

    # Compile with checkpointer
    checkpointer = MemorySaver()
    graph = builder.compile(checkpointer=checkpointer)

    # Initial state
    initial_state: DialogueState = {
        "user_message": "San Francisco",
        "last_response": "Which city are you departing from?",
        "messages": [],
        "flow_stack": [
            {
                "flow_id": "book_flight_1",
                "flow_name": "book_flight",
                "current_step": "collect_origin",
            }
        ],
        "flow_slots": {},
        "conversation_state": "waiting_for_slot",
        "current_step": "collect_origin",
        "waiting_for_slot": "origin",
        "current_prompted_slot": "origin",
    }

    logger.info("=" * 80)
    logger.info("INITIAL STATE:")
    logger.info(f"  last_response: '{initial_state['last_response']}'")
    logger.info("=" * 80)

    # Run graph
    config = {"configurable": {"thread_id": "test-1"}}
    final_state = await graph.ainvoke(initial_state, config)

    logger.info("=" * 80)
    logger.info("FINAL STATE:")
    logger.info(f"  last_response: '{final_state.get('last_response')}'")
    logger.info("=" * 80)


if __name__ == "__main__":
    asyncio.run(main())
