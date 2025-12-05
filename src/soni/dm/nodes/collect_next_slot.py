"""Collect next slot node with interrupt pattern."""

import logging
from typing import Any

from soni.core.types import DialogueState

logger = logging.getLogger(__name__)


async def collect_next_slot_node(
    state: DialogueState,
    runtime: Any,  # Runtime[RuntimeContext] - using Any to avoid import issues
) -> dict:
    """
    Ask for next required slot and pause execution.

    Uses interrupt() to wait for user response.

    Args:
        state: Current dialogue state
        runtime: Runtime context

    Returns:
        Partial state updates
    """
    # Import interrupt at runtime (not at module level)
    from langgraph.types import interrupt

    # Get active flow (idempotent operation - safe before interrupt)
    flow_manager = runtime.context["flow_manager"]
    active_ctx = flow_manager.get_active_context(state)

    if not active_ctx:
        return {"conversation_state": "idle"}

    # Determine next slot to collect
    # TODO: Get from flow definition
    next_slot = "origin"  # Placeholder

    # Generate prompt
    prompt = f"Please provide your {next_slot}."

    # Pause here - wait for user response
    user_response = interrupt(
        {
            "type": "slot_request",
            "slot": next_slot,
            "prompt": prompt,
        }
    )

    # Code after interrupt() executes when user responds
    return {
        "user_message": user_response,
        "waiting_for_slot": next_slot,
        "conversation_state": "waiting_for_slot",
        "last_response": prompt,
    }
