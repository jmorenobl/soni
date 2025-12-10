"""Handle confirmation response node for processing user confirmation (yes/no)."""

import logging
from typing import Any

from soni.core.types import DialogueState, NodeRuntime
from soni.utils.metadata_manager import MetadataManager
from soni.utils.response_generator import ResponseGenerator

logger = logging.getLogger(__name__)


async def handle_confirmation_node(
    state: DialogueState,
    runtime: NodeRuntime,
) -> dict:
    """
    Handle user's confirmation response, including automatic correction detection.

    This node processes the user's yes/no response to a confirmation request.
    It also automatically detects and handles corrections/modifications during confirmation.

    Args:
        state: Current dialogue state
        runtime: Runtime context

    Returns:
        Partial state updates based on confirmation result
    """
    nlu_result = state.get("nlu_result") or {}
    confirmation_value = nlu_result.get("confirmation_value") if nlu_result else None

    logger.info(
        "handle_confirmation_node ENTRY",
        extra={
            "user_message": state.get("user_message", "")[:50],
            "conversation_state": state.get("conversation_state"),
            "nlu_message_type": nlu_result.get("message_type"),
            "confirmation_value": confirmation_value,
            "nlu_command": nlu_result.get("command"),
        },
    )

    # Add retry counter check
    metadata = state.get("metadata", {})
    confirmation_attempts = metadata.get("_confirmation_attempts", 0)

    # Safety check: prevent infinite loop
    # Check BEFORE processing - if we've already exceeded max attempts, return error immediately
    MAX_CONFIRMATION_ATTEMPTS = 3
    if confirmation_attempts >= MAX_CONFIRMATION_ATTEMPTS:
        logger.error(
            f"Maximum confirmation attempts ({MAX_CONFIRMATION_ATTEMPTS}) exceeded "
            f"(current attempts: {confirmation_attempts}). Aborting confirmation flow."
        )
        # Clear confirmation attempts and return error state
        metadata_cleared = MetadataManager.clear_confirmation_flags(metadata)

        return {
            "conversation_state": "error",
            "last_response": (
                "I'm having trouble understanding your confirmation. "
                "Let's start over. What would you like to do?"
            ),
            "metadata": metadata_cleared,
        }

    message_type = nlu_result.get("message_type") if nlu_result else None

    # Check if user is correcting/modifying during confirmation
    # This happens automatically - no DSL configuration needed
    if message_type in ("correction", "modification"):
        return await _handle_correction_during_confirmation(
            state, runtime, nlu_result, message_type
        )

    # Sanity check: should be a confirmation response
    if message_type != "confirmation":
        # Edge case: user said something unrelated during confirmation
        # Treat as digression or ask again
        logger.warning(
            f"Expected confirmation but got message_type={message_type}, treating as digression"
        )
        return {"conversation_state": "understanding"}

    # Get confirmation value from NLU result
    # The NLU should extract this as True/False
    confirmation_value = nlu_result.get("confirmation_value") if nlu_result else None

    # User confirmed
    if confirmation_value is True:
        logger.info("User confirmed, proceeding to action")
        # Clear confirmation attempts and flags on success
        metadata_cleared = MetadataManager.clear_confirmation_flags(metadata)

        # Advance to next step (should be the action step after confirm)
        step_manager = runtime.context["step_manager"]
        advance_updates = step_manager.advance_to_next_step(state, runtime.context)

        return {
            **advance_updates,  # Includes updated flow_stack and conversation_state
            "last_response": "Great! Processing your request...",
            "metadata": metadata_cleared,
        }

    # User denied - wants to change something
    elif confirmation_value is False:
        # Check if we've exceeded max attempts BEFORE allowing modification
        # If we've had too many unclear attempts, treat this as an error instead
        if confirmation_attempts >= MAX_CONFIRMATION_ATTEMPTS - 1:
            # This is likely a misinterpretation after many unclear attempts
            # Treat as error instead of allowing modification
            logger.error(
                f"Maximum confirmation attempts ({MAX_CONFIRMATION_ATTEMPTS}) exceeded. "
                f"Treating denial as error after {confirmation_attempts} unclear attempts."
            )
            metadata_cleared = MetadataManager.clear_confirmation_flags(metadata)

            return {
                "conversation_state": "error",
                "last_response": (
                    "I'm having trouble understanding your confirmation. "
                    "Let's start over. What would you like to do?"
                ),
                "metadata": metadata_cleared,
            }

        logger.info("User denied confirmation, allowing modification")
        # Clear confirmation attempts and flags on explicit denial
        metadata_cleared = MetadataManager.clear_confirmation_flags(metadata)
        # For now, go back to understanding to allow user to modify
        # In the future, we could route to a specific modification handler
        return {
            "conversation_state": "understanding",
            "last_response": "What would you like to change?",
            "metadata": metadata_cleared,
        }

    # Confirmation value not extracted or unclear
    else:
        # Increment retry counter first
        metadata_updated = MetadataManager.increment_confirmation_attempts(metadata)
        new_attempts = MetadataManager.get_confirmation_attempts(metadata_updated)

        # Check if we've exceeded max attempts AFTER incrementing
        # This ensures we check correctly: after 3 attempts (1, 2, 3), show error
        if new_attempts >= MAX_CONFIRMATION_ATTEMPTS:
            logger.error(
                f"Maximum confirmation attempts ({MAX_CONFIRMATION_ATTEMPTS}) exceeded. "
                f"Aborting confirmation flow."
            )
            # Clear confirmation attempts and return error state
            metadata_cleared = MetadataManager.clear_confirmation_flags(metadata_updated)

            return {
                "conversation_state": "error",
                "last_response": (
                    "I'm having trouble understanding your confirmation. "
                    "Let's start over. What would you like to do?"
                ),
                "metadata": metadata_cleared,
            }

        logger.warning(
            f"Confirmation value unclear: {confirmation_value}, asking again "
            f"(attempt {new_attempts}/{MAX_CONFIRMATION_ATTEMPTS})"
        )

        # Set a flag in metadata to indicate that handle_confirmation already processed this
        # This allows routing to detect it without depending on response text
        metadata_updated["_confirmation_processed"] = True
        metadata_updated["_confirmation_unclear"] = True

        return {
            "conversation_state": "confirming",
            "last_response": "I didn't understand. Is this information correct? (yes/no)",
            "metadata": metadata_updated,
        }


async def _handle_correction_during_confirmation(
    state: DialogueState,
    runtime: NodeRuntime,
    nlu_result: dict,
    message_type: str,
) -> dict:
    """
    Handle correction/modification during confirmation step.

    This happens automatically - no DSL configuration needed.
    Updates the slot and re-displays confirmation with updated values.

    Args:
        state: Current dialogue state
        runtime: Runtime context
        nlu_result: NLU result containing correction/modification
        message_type: "correction" or "modification"

    Returns:
        Partial state updates with updated slots and re-generated confirmation
    """
    slots = nlu_result.get("slots", [])
    if not slots:
        logger.warning("Correction/modification detected but no slots in NLU result")
        return {"conversation_state": "confirming"}

    # Get slot to correct/modify
    slot = slots[0]
    if hasattr(slot, "name"):
        slot_name = slot.name
        raw_value = slot.value
    elif isinstance(slot, dict):
        slot_name = slot.get("name")
        raw_value = slot.get("value")
    else:
        logger.warning(f"Unknown slot format in correction: {type(slot)}")
        return {"conversation_state": "confirming"}

    # Normalize value
    normalizer = runtime.context["normalizer"]
    try:
        normalized_value = await normalizer.normalize_slot(slot_name, raw_value)
    except Exception as e:
        logger.error(f"Normalization failed during confirmation: {e}")
        return {"conversation_state": "confirming"}

    # Update slot in state
    flow_manager = runtime.context["flow_manager"]
    active_ctx = flow_manager.get_active_context(state)

    if not active_ctx:
        return {"conversation_state": "error"}

    flow_id = active_ctx["flow_id"]
    flow_slots = state.get("flow_slots", {}).copy()
    if flow_id not in flow_slots:
        flow_slots[flow_id] = {}

    flow_slots[flow_id][slot_name] = normalized_value

    # Set state variables (for Task 004, but implementing here)
    metadata = state.get("metadata", {})
    if message_type == "correction":
        metadata = MetadataManager.set_correction_flags(metadata, slot_name, normalized_value)
    elif message_type == "modification":
        metadata = MetadataManager.set_modification_flags(metadata, slot_name, normalized_value)

    # Re-generate confirmation message with updated values
    step_manager = runtime.context["step_manager"]
    current_step_config = step_manager.get_current_step_config(state, runtime.context)

    confirmation_message = ResponseGenerator.generate_confirmation(
        flow_slots[flow_id],
        current_step_config,
        runtime.context["config"],
    )

    # Get acknowledgment message using template (Task 005)
    config = runtime.context["config"]
    if message_type == "correction":
        acknowledgment = _get_response_template(
            config,
            "correction_acknowledged",
            "Got it, I've updated {slot_name} to {new_value}.",
            slot_name=slot_name,
            new_value=normalized_value,
        )
    else:  # modification
        acknowledgment = _get_response_template(
            config,
            "modification_acknowledged",
            "Done, I've changed {slot_name} to {new_value}.",
            slot_name=slot_name,
            new_value=normalized_value,
        )

    # Combine acknowledgment with confirmation message
    combined_response = f"{acknowledgment}\n\n{confirmation_message}"

    logger.info(
        f"Correction/modification during confirmation: updated {slot_name} to {normalized_value}, "
        f"re-displaying confirmation"
    )

    return {
        "flow_slots": flow_slots,
        "conversation_state": "confirming",  # Return to confirming state
        "last_response": combined_response,
        "metadata": metadata,
    }


def _get_response_template(
    config: Any,
    template_name: str,
    default_template: str,
    **kwargs: Any,
) -> str:
    """
    Get response template from config and interpolate variables.

    Args:
        config: SoniConfig instance
        template_name: Name of template in config.responses (if it exists)
        default_template: Default template if not found
        **kwargs: Variables to interpolate (e.g., slot_name="origin", new_value="NYC")

    Returns:
        Interpolated template string
    """
    template = None
    # Check if config has responses field (may not be implemented yet)
    if hasattr(config, "responses") and config.responses:
        template_config = config.responses.get(template_name)
        if template_config:
            # Use default or first variation
            if isinstance(template_config, dict):
                template = template_config.get("default")
            elif isinstance(template_config, str):
                template = template_config

    if not template:
        template = default_template

    # Interpolate variables
    result = template
    for key, value in kwargs.items():
        result = result.replace(f"{{{key}}}", str(value))

    return result
