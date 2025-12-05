"""Validate slot node for slot validation and normalization."""

import logging
from typing import Any

from soni.core.types import DialogueState

logger = logging.getLogger(__name__)


async def validate_slot_node(
    state: DialogueState,
    runtime: Any,  # Runtime[RuntimeContext] - using Any to avoid import issues
) -> dict:
    """
    Validate and normalize slot value.

    Args:
        state: Current dialogue state
        runtime: Runtime context with dependencies

    Returns:
        Partial state updates
    """
    normalizer = runtime.context["normalizer"]
    nlu_result = state.get("nlu_result", {})

    if not nlu_result or not nlu_result.get("slots"):
        return {"conversation_state": "error"}

    # Get first slot from NLU result
    slots = nlu_result.get("slots", [])
    if not slots:
        return {"conversation_state": "error"}

    slot = slots[0]
    slot_name = slot.get("name")
    raw_value = slot.get("value")

    # Normalize slot value
    try:
        normalized_value = await normalizer.normalize(slot_name, raw_value)

        # Update flow slots
        flow_manager = runtime.context["flow_manager"]
        active_ctx = flow_manager.get_active_context(state)

        if active_ctx:
            flow_id = active_ctx["flow_id"]
            flow_slots = state.get("flow_slots", {}).copy()
            if flow_id not in flow_slots:
                flow_slots[flow_id] = {}
            flow_slots[flow_id][slot_name] = normalized_value

            return {
                "flow_slots": flow_slots,
                "conversation_state": "validating_slot",
            }
        else:
            return {"conversation_state": "error"}
    except Exception as e:
        logger.error(f"Validation failed for slot {slot_name}: {e}")
        return {
            "conversation_state": "error",
            "validation_error": str(e),
        }
