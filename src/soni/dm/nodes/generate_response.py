"""Generate response node with single responsibility."""

import logging

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
    # Generate response using priority-based logic
    response = ResponseGenerator.generate_from_priority(state)
    logger.info(f"generate_response_node returning: {response[:50]}...")

    # Determine conversation_state based on current state
    current_conv_state = state.get("conversation_state")

    if current_conv_state == "completed":
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

    return {
        "last_response": response,
        "conversation_state": conversation_state,
    }
