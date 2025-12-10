"""Collect next slot node with interrupt pattern."""

import logging
from typing import Any

from soni.core.types import DialogueState, NodeRuntime

logger = logging.getLogger(__name__)


async def collect_next_slot_node(
    state: DialogueState,
    runtime: NodeRuntime,
) -> dict[str, Any]:
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
    step_manager = runtime.context["step_manager"]
    active_ctx = flow_manager.get_active_context(state)

    if not active_ctx:
        # No active flow - this shouldn't happen if routing is correct
        # But if it does, generate a response instead of going idle
        logger.warning("collect_next_slot called but no active flow context")
        return {
            "conversation_state": "idle",
            "last_response": "I'm not sure what you're asking for. Could you rephrase?",
        }

    # Get current step configuration
    current_step_config = step_manager.get_current_step_config(state, runtime.context)

    if not current_step_config:
        # No current step, try to get next step
        next_step_config = step_manager.get_next_step_config(state, runtime.context)
        if next_step_config and next_step_config.type == "collect":
            # Advance to next step
            _ = step_manager.advance_to_next_step(state, runtime.context)
            current_step_config = next_step_config
        else:
            return {"conversation_state": "error"}

    # Get next required slot from current step
    next_slot = step_manager.get_next_required_slot(state, current_step_config, runtime.context)

    if not next_slot:
        # No slot to collect, advance to next step
        step_updates = step_manager.advance_to_next_step(state, runtime.context)
        # CRITICAL: If we advanced to next step, return updates and let routing handle it
        # Don't go to interrupt() if there's no slot to collect
        return dict(step_updates) if step_updates else {}

    # Get slot configuration for proper prompt
    from soni.core.state import get_slot_config

    try:
        slot_config = get_slot_config(runtime.context, next_slot)
        prompt = (
            slot_config.prompt
            if hasattr(slot_config, "prompt")
            else f"Please provide your {next_slot}."
        )
    except KeyError:
        # Slot config not found, use generic prompt
        prompt = f"Please provide your {next_slot}."

    # CRITICAL: Set last_response BEFORE interrupt() so that if the flow goes to
    # generate_response (e.g., after a digression), it has the correct prompt
    # The prompt will be shown to the user immediately
    result = {
        "last_response": prompt,
        "waiting_for_slot": next_slot,
        "current_prompted_slot": next_slot,
        "conversation_state": "waiting_for_slot",
    }

    # Pause here - wait for user response
    # The prompt is passed as the interrupt value
    # It will be available in result['__interrupt__'] after ainvoke()
    user_response = interrupt(prompt)

    # Code after interrupt() executes when user responds
    # The node re-executes from the beginning, and interrupt() returns the resume value
    # Update result with user_message from resume
    result["user_message"] = user_response
    return result
