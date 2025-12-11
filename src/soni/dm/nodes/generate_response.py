"""Generate response node with single responsibility."""

import logging
from typing import Any

from soni.core.types import DialogueState, NodeRuntime
from soni.utils.flow_cleanup import FlowCleanupManager
from soni.utils.response_generator import ResponseGenerator

logger = logging.getLogger(__name__)


async def generate_response_node(
    state: DialogueState,
    runtime: NodeRuntime,
) -> dict:
    """Generate final response to user (single responsibility).

    This node is responsible ONLY for generating the response text.
    Flow cleanup is handled separately.

    Args:
        state: Current dialogue state
        runtime: Runtime context

    Returns:
        Partial state updates with last_response and conversation_state
    """
    # DEBUG: Log input state to investigate last_response update issue
    logger.info("=" * 80)
    logger.info("generate_response_node INPUTS:")
    logger.info(f"  last_response: '{state.get('last_response')}'")
    logger.info(f"  waiting_for_slot: '{state.get('waiting_for_slot')}'")
    logger.info(f"  current_prompted_slot: '{state.get('current_prompted_slot')}'")
    logger.info(f"  user_message: '{state.get('user_message')}'")
    logger.info(f"  conversation_state: '{state.get('conversation_state')}'")

    # Check for high-priority items that might override last_response
    from soni.core.state import get_all_slots

    all_slots = get_all_slots(state)
    logger.info(f"  confirmation slot: {all_slots.get('confirmation')}")
    logger.info(f"  action_result: {state.get('action_result')}")
    logger.info("=" * 80)

    # Generate response using priority-based logic
    response = ResponseGenerator.generate_from_priority(state)
    logger.info(f"generate_response_node OUTPUT: '{response[:100]}...'")

    # Determine conversation_state based on current state
    current_conv_state = state.get("conversation_state")
    waiting_for_slot: str | None = state.get("waiting_for_slot")

    # CRITICAL: If waiting_for_slot exists, preserve waiting_for_slot state
    # This handles the case where handle_digression (or other nodes) set waiting_for_slot
    # but the state hasn't been fully merged yet, or conversation_state isn't set correctly
    if waiting_for_slot:
        # Preserve waiting_for_slot state (e.g., after digression)
        conversation_state = "waiting_for_slot"
        logger.info(
            f"generate_response: Detected waiting_for_slot='{waiting_for_slot}', "
            f"preserving conversation_state='waiting_for_slot'"
        )
    elif current_conv_state == "completed":
        # Flow cleanup is now handled by routing or separate node
        # This node only sets conversation_state
        conversation_state = "completed"
        # Optionally clean up completed flow here (or in routing)
        cleanup_updates = FlowCleanupManager.cleanup_completed_flow(state)
        if cleanup_updates:
            return {
                "last_response": response,
                "conversation_state": conversation_state,
                **cleanup_updates,
            }
    elif current_conv_state == "confirming":
        # Preserve confirming state
        conversation_state = "confirming"
    else:
        conversation_state = "idle"
        # When idle, clear waiting_for_slot to prevent routing loops
        waiting_for_slot = None

    result: dict[str, Any] = {
        "last_response": response,
        "conversation_state": conversation_state,
    }

    # Preserve waiting_for_slot if it exists and conversation_state is waiting_for_slot
    # Clear it when idle to prevent routing loops
    if conversation_state == "waiting_for_slot" and waiting_for_slot:
        result["waiting_for_slot"] = waiting_for_slot
        logger.info(f"generate_response: Preserving waiting_for_slot='{waiting_for_slot}'")
    elif conversation_state == "idle":
        result["waiting_for_slot"] = None

    return result
