"""Confirm action node for requesting user confirmation before executing actions."""

import logging

from soni.core.types import DialogueState, NodeRuntime

logger = logging.getLogger(__name__)


async def confirm_action_node(
    state: DialogueState,
    runtime: NodeRuntime,
) -> dict:
    """
    Request user confirmation before executing an action.

    This node:
    1. Gets the current confirm step configuration
    2. Builds a confirmation message showing collected slots
    3. Uses interrupt() to wait for user response (yes/no)
    4. Returns state with conversation_state = "confirming"

    Args:
        state: Current dialogue state
        runtime: Runtime context

    Returns:
        Partial state updates with confirmation prompt and user message
    """
    # Import interrupt at runtime (not at module level)
    import traceback

    from langgraph.types import interrupt

    logger.info(
        "confirm_action_node ENTRY",
        extra={
            "user_message": state.get("user_message", "")[:50],
            "conversation_state": state.get("conversation_state"),
            "last_response": state.get("last_response", "")[:50],
            "stack_trace": "".join(traceback.format_stack()[-5:]),
        },
    )

    flow_manager = runtime.context["flow_manager"]
    step_manager = runtime.context["step_manager"]
    active_ctx = flow_manager.get_active_context(state)

    if not active_ctx:
        logger.error("No active flow context for confirmation")
        return {"conversation_state": "error"}

    # Get current step configuration (should be a confirm step)
    current_step_config = step_manager.get_current_step_config(state, runtime.context)

    if not current_step_config or current_step_config.type != "confirm":
        logger.error(
            f"Current step is not a confirm step: {current_step_config.type if current_step_config else 'None'}"
        )
        return {"conversation_state": "error"}

    # Get slots from active flow
    from soni.core.state import get_all_slots

    slots = get_all_slots(state)

    # Build confirmation message
    # First, try to get message from step config
    confirmation_msg = None
    if hasattr(current_step_config, "message") and current_step_config.message:
        confirmation_msg = current_step_config.message
    else:
        # Default confirmation message
        confirmation_msg = "Let me confirm:\n"

    # Interpolate slot values in the message
    # Simple interpolation: {slot_name} -> value
    try:
        confirmation_msg = confirmation_msg.format(**slots)
    except KeyError as e:
        logger.warning(f"Slot {e} not found for interpolation, using placeholder")
        # Replace missing slots with placeholder
        for slot_name in slots:
            confirmation_msg = confirmation_msg.replace(f"{{{slot_name}}}", str(slots[slot_name]))

    # If no slots were interpolated, add them manually
    if "{origin}" in confirmation_msg or "{destination}" in confirmation_msg:
        # Still has placeholders, add slots at the end
        confirmation_msg += "\n"
        for slot_name, value in slots.items():
            if value:  # Only show non-empty slots
                confirmation_msg += f"- {slot_name}: {value}\n"

    confirmation_msg += "\nIs this correct?"

    # Check if we already have a user message (node re-executed after resume)
    # If user_message is already set and conversation_state is "confirming",
    # we need to check if this is the FIRST re-execution (go to understand)
    # or SECOND re-execution (after handle_confirmation set error message)
    existing_user_message = state.get("user_message", "")
    existing_conv_state = state.get("conversation_state")

    if existing_user_message and existing_conv_state == "confirming":
        # Node re-executed after resume - user already responded
        # Check if handle_confirmation already processed and set error message
        existing_last_response = state.get("last_response", "")

        # Check if handle_confirmation already processed this confirmation
        # Use metadata flag instead of checking response text (more robust)
        metadata = state.get("metadata", {})
        confirmation_processed = metadata.get("_confirmation_processed", False)

        if confirmation_processed:
            # handle_confirmation already processed and set response
            # Preserve it and signal to routing that we should go to generate_response
            logger.debug(
                f"confirm_action: handle_confirmation already processed, "
                f"preserving response: {existing_last_response[:50]}..."
            )
            return {
                "conversation_state": "confirming",
                "last_response": existing_last_response,  # Preserve from handle_confirmation
            }
        else:
            # First re-execution after resume - this is the original confirmation message
            # Don't interrupt again, just pass through to let routing send to understand
            logger.debug(
                f"confirm_action: First re-execution, passing through to understand. "
                f"user_message={existing_user_message[:50]}..."
            )
            return {
                "conversation_state": "confirming",
                # Don't set last_response - let it pass through
            }

    # Pause and wait for user confirmation
    # The prompt is passed as the interrupt value and will be extracted by RuntimeLoop
    # RuntimeLoop._process_interrupts() will set last_response = confirmation_msg
    user_response = interrupt(confirmation_msg)

    # Code after interrupt() executes when user responds
    # The node re-executes from the beginning, and interrupt() returns the resume value
    return {
        "user_message": user_response,
        "conversation_state": "confirming",
        "last_response": confirmation_msg,
    }
