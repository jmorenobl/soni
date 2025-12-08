"""Handle confirmation response node for processing user confirmation (yes/no)."""

import logging
from typing import Any

from soni.core.types import DialogueState

logger = logging.getLogger(__name__)


async def handle_confirmation_node(
    state: DialogueState,
    runtime: Any,  # Runtime[RuntimeContext] - using Any to avoid import issues
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
        return {
            "conversation_state": "ready_for_action",
            "last_response": "Great! Processing your request...",
        }

    # User denied - wants to change something
    elif confirmation_value is False:
        logger.info("User denied confirmation, allowing modification")
        # For now, go back to understanding to allow user to modify
        # In the future, we could route to a specific modification handler
        return {
            "conversation_state": "understanding",
            "last_response": "What would you like to change?",
        }

    # Confirmation value not extracted or unclear
    else:
        logger.warning(f"Confirmation value unclear: {confirmation_value}, asking again")
        return {
            "conversation_state": "confirming",
            "last_response": "I didn't understand. Is this information correct? (yes/no)",
        }


async def _handle_correction_during_confirmation(
    state: DialogueState,
    runtime: Any,
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
    metadata = state.get("metadata", {}).copy()
    if message_type == "correction":
        metadata["_correction_slot"] = slot_name
        metadata["_correction_value"] = normalized_value
        # Clear modification variables if any
        metadata.pop("_modification_slot", None)
        metadata.pop("_modification_value", None)
    elif message_type == "modification":
        metadata["_modification_slot"] = slot_name
        metadata["_modification_value"] = normalized_value
        # Clear correction variables if any
        metadata.pop("_correction_slot", None)
        metadata.pop("_correction_value", None)

    # Re-generate confirmation message with updated values
    step_manager = runtime.context["step_manager"]
    current_step_config = step_manager.get_current_step_config(state, runtime.context)

    confirmation_message = _generate_confirmation_message(
        flow_slots[flow_id], current_step_config, runtime.context
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


def _generate_confirmation_message(
    slots: dict[str, Any],
    step_config: Any | None,  # StepConfig - using Any to avoid import issues
    context: Any,  # RuntimeContext - using Any to avoid import issues
) -> str:
    """
    Generate confirmation message with current slot values.

    Uses step_config.message template if available, otherwise generates default.

    Args:
        slots: Dictionary of slot name to value
        step_config: Current step configuration (may be None)
        context: Runtime context with config

    Returns:
        Confirmation message string
    """
    # Try to use template from step config if available
    if step_config and hasattr(step_config, "message") and step_config.message:
        message_str = str(step_config.message)
        # Interpolate slot values in template
        for slot_name, value in slots.items():
            message_str = message_str.replace(f"{{{slot_name}}}", str(value))
        return message_str

    # Default confirmation message
    config = context["config"]
    message = "Let me confirm:\n"
    for slot_name, value in slots.items():
        # Get display name from slot config if available
        display_name = slot_name
        if hasattr(config, "slots") and config.slots:
            slot_config = config.slots.get(slot_name, {})
            if isinstance(slot_config, dict):
                display_name = slot_config.get("display_name", slot_name)
        message += f"- {display_name}: {value}\n"
    message += "\nIs this correct?"

    return message


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
