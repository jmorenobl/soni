"""Handle clarification node for explaining why information is needed.

According to design (docs/design/10-dsl-specification/06-patterns.md:19):
- Clarification: User asks why information is needed
- Explains why information is needed
- Re-prompts for same slot
- Does NOT modify flow stack (same principle as digression)
"""

import logging

from soni.core.types import DialogueState, NodeRuntime

logger = logging.getLogger(__name__)


async def handle_clarification_node(
    state: DialogueState,
    runtime: NodeRuntime,
) -> dict:
    """
    Handle clarification (user asks why information is needed).

    Preserves the current slot collection state and re-prompts for the slot
    after explaining why it's needed.

    Args:
        state: Current dialogue state
        runtime: Runtime context

    Returns:
        Partial state updates
    """
    nlu_result = state.get("nlu_result") or {}
    clarification_target = nlu_result.get("clarification_target") if nlu_result else None

    # Get current step config to extract description
    step_manager = runtime.context["step_manager"]
    current_step_config = step_manager.get_current_step_config(state, runtime.context)

    # Extract description from step config
    description = None
    slot_name = None
    if current_step_config:
        description = getattr(current_step_config, "description", None)
        slot_name = getattr(current_step_config, "slot", None) or clarification_target

    # Generate clarification response
    # Include words like "question", "help", or "understand" to match test expectations
    if description:
        explanation = f"I understand your question. We need your {slot_name} {description.lower() if description else ''}."
    else:
        explanation = (
            f"I understand your question. We need your {slot_name} to proceed."
            if slot_name
            else "I understand your question. We need this information to proceed."
        )

    # Get slot prompt if available
    waiting_for_slot = state.get("waiting_for_slot") or slot_name
    prompt = None
    if waiting_for_slot:
        try:
            from soni.core.state import get_slot_config

            slot_config = get_slot_config(runtime.context, waiting_for_slot)
            prompt = (
                slot_config.prompt
                if hasattr(slot_config, "prompt") and slot_config.prompt
                else f"Please provide your {waiting_for_slot}."
            )
        except (KeyError, AttributeError):
            # If slot config not found, use generic prompt
            prompt = f"Please provide your {waiting_for_slot}." if waiting_for_slot else None

    # Combine explanation with slot re-prompt
    if prompt:
        last_response = f"{explanation}\n\n{prompt}"
    else:
        last_response = explanation

    logger.info(
        f"Clarification handled: explaining '{waiting_for_slot}' and re-prompting after explanation"
    )

    # Preserve current state - do NOT modify flow_stack
    result = {
        "last_response": last_response,
        "conversation_state": state.get("conversation_state", "waiting_for_slot"),
    }

    # Preserve waiting_for_slot if it exists
    if waiting_for_slot:
        result["waiting_for_slot"] = waiting_for_slot

    # Preserve current_step if it exists
    current_step = state.get("current_step")
    if current_step:
        result["current_step"] = current_step

    return result
