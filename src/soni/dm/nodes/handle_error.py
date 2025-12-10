"""Error handling node for dialogue recovery."""

import logging

from soni.core.types import DialogueState, NodeRuntime

logger = logging.getLogger(__name__)


async def handle_error_node(
    state: DialogueState,
    runtime: NodeRuntime,
) -> dict:
    """
    Handle errors and attempt recovery.

    Pattern: With Dependencies (uses context_schema)

    Args:
        state: Current dialogue state
        runtime: Runtime context with dependencies

    Returns:
        Partial state updates with recovery strategy
    """
    # Access dependencies
    flow_manager = runtime.context["flow_manager"]

    # Extract error information from metadata
    metadata = state.get("metadata", {})
    error = metadata.get("error")
    error_type = metadata.get("error_type")

    # Log error with context
    logger.error(
        f"Error in dialogue flow: {error}",
        extra={
            "error_type": error_type,
            "conversation_state": state.get("conversation_state"),
            "turn_count": state.get("turn_count", 0),
        },
    )

    # Attempt recovery based on error type
    if error_type == "validation_error":
        # Clear invalid data and retry
        if state.get("flow_stack"):
            flow_manager.pop_flow(state, result="cancelled")

        return {
            "last_response": "Let's try that again. What would you like to do?",
            "conversation_state": "idle",
            "metadata": {**metadata, "error": None, "error_type": None},
        }

    elif error_type == "nlu_error":
        return {
            "last_response": "I didn't understand that. Could you rephrase?",
            "conversation_state": "understanding",
            "metadata": {**metadata, "error": None, "error_type": None},
        }

    elif error_type == "action_error":
        return {
            "last_response": "Something went wrong while processing your request. Please try again.",
            "conversation_state": "idle",
            "flow_stack": [],
            "flow_slots": {},
            "metadata": {**metadata, "error": None, "error_type": None},
        }

    # Generic error - clear stack and start over
    return {
        "last_response": "Something went wrong. Let's start fresh.",
        "conversation_state": "idle",
        "flow_stack": [],
        "flow_slots": {},
        "metadata": {**metadata, "error": None, "error_type": None},
    }
