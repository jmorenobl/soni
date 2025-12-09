"""Generate response node for final response generation."""

import logging
from typing import Any

from soni.core.types import DialogueState

logger = logging.getLogger(__name__)


async def generate_response_node(
    state: DialogueState,
    runtime: Any,  # Runtime[RuntimeContext] - using Any to avoid import issues
) -> dict:
    """
    Generate final response to user.

    Args:
        state: Current dialogue state
        runtime: Runtime context

    Returns:
        Partial state updates
    """
    # For now, simple response generation
    # TODO: Integrate with LLM for natural response generation

    # Try to get confirmation message from slots first
    from soni.core.state import get_all_slots

    slots = get_all_slots(state)

    logger.info(
        "generate_response_node called",
        extra={
            "slots_keys": list(slots.keys()),
            "has_confirmation": "confirmation" in slots,
            "has_booking_ref": "booking_ref" in slots,
            "action_result": state.get("action_result") is not None,
        },
    )

    # Check for confirmation message in slots (from action outputs)
    if "confirmation" in slots and slots["confirmation"]:
        response = slots["confirmation"]
        logger.info(f"Using confirmation message from slots: {response[:50]}...")
    elif "booking_ref" in slots and slots["booking_ref"]:
        response = f"Booking confirmed! Your reference is: {slots['booking_ref']}"
        logger.info("Using booking_ref to generate response")
    else:
        # Fallback to action_result
        action_result = state.get("action_result")
        if action_result:
            # Try to extract a meaningful message from action_result
            if isinstance(action_result, dict):
                response = (
                    action_result.get("message")
                    or action_result.get("confirmation")
                    or f"Action completed successfully. Result: {action_result}"
                )
            else:
                response = f"Action completed successfully. Result: {action_result}"
            logger.info("Using action_result to generate response")
        else:
            response = "How can I help you?"
            logger.warning(
                "No confirmation, booking_ref, or action_result found, using default response"
            )

    logger.info(f"generate_response_node returning: {response[:50]}...")

    # Preserve conversation_state if already completed
    # Don't override "completed" with "idle"
    current_conv_state = state.get("conversation_state")
    if current_conv_state == "completed":
        conversation_state = "completed"

        # Clean up completed flow from stack AFTER generating response
        # This ensures slots are still available for response generation
        flow_stack = state.get("flow_stack", [])
        if flow_stack and flow_stack[-1].get("flow_state") == "completed":
            # Pop the completed flow manually
            completed_flow = flow_stack.pop()

            # Archive it in metadata
            if "metadata" not in state:
                state["metadata"] = {}
            if "completed_flows" not in state["metadata"]:
                state["metadata"]["completed_flows"] = []
            state["metadata"]["completed_flows"].append(completed_flow)

            # Note: We intentionally DON'T delete flow_slots here
            # Slots remain available for logging, debugging, and potential follow-up interactions
            # They will be naturally cleaned up when a new flow starts or session resets
            logger.info(f"Completed flow removed from stack: {completed_flow['flow_id']}")

            return {
                "last_response": response,
                "conversation_state": conversation_state,
                "flow_stack": flow_stack,
            }
    else:
        conversation_state = "idle"

    return {
        "last_response": response,
        "conversation_state": conversation_state,
    }
