"""Understand node for NLU processing."""

import logging
import time
from typing import Any

from soni.core.types import DialogueState

logger = logging.getLogger(__name__)


async def understand_node(
    state: DialogueState,
    runtime: Any,  # Runtime[RuntimeContext] - using Any to avoid import issues
) -> dict:
    """
    Understand user message via NLU.

    Pattern: With Dependencies (uses context_schema)

    Args:
        state: Current dialogue state
        runtime: Runtime context with dependencies

    Returns:
        Partial state updates with NLU result
    """
    # Access dependencies (type-safe)
    # Note: "du" is the key used in create_runtime_context (Dialogue Understanding)
    nlu_provider = runtime.context["du"]
    flow_manager = runtime.context["flow_manager"]
    scope_manager = runtime.context["scope_manager"]

    # Build NLU context
    active_ctx = flow_manager.get_active_context(state)
    current_flow_name = active_ctx["flow_name"] if active_ctx else "none"

    # Get expected slots for current flow from scope manager
    available_actions = scope_manager.get_available_actions(state)
    expected_slots = []
    if current_flow_name and current_flow_name != "none":
        expected_slots = scope_manager.get_expected_slots(
            flow_name=current_flow_name,
            available_actions=available_actions,
        )
        logger.debug(
            f"Expected slots for flow '{current_flow_name}': {expected_slots}",
            extra={"flow": current_flow_name, "expected_slots": expected_slots},
        )
    else:
        logger.debug(
            f"No active flow, passing empty expected_slots. "
            f"NLU will infer from available_flows: {scope_manager.get_available_flows(state)}"
        )

    # Get the specific slot we're waiting for (if any)
    waiting_for_slot = state.get("waiting_for_slot")

    # Build structured types directly (no adapter needed)
    # This follows the design in docs/design/05-message-flow.md
    import dspy

    from soni.du.models import DialogueContext

    # Build conversation history
    history_messages = state["messages"][-5:] if state["messages"] else []  # Last 5 messages
    history = dspy.History(messages=history_messages)

    # Build structured dialogue context
    dialogue_context = DialogueContext(
        current_slots=(state["flow_slots"].get(active_ctx["flow_id"], {}) if active_ctx else {}),
        available_actions=available_actions,
        available_flows=scope_manager.get_available_flows(state),
        current_flow=current_flow_name,
        expected_slots=expected_slots,
        current_prompted_slot=waiting_for_slot,  # Prioritize this slot
    )

    logger.debug(
        f"NLU context: waiting_for_slot={waiting_for_slot}, expected_slots={expected_slots}",
        extra={"waiting_for_slot": waiting_for_slot, "expected_slots": expected_slots},
    )

    # Call NLU with structured types directly (no adapter)
    # Use predict() which is the main method, understand() is just a legacy adapter
    nlu_result_raw = await nlu_provider.predict(
        state["user_message"],
        history,
        dialogue_context,
    )

    # Convert NLUOutput to dict for state storage
    # (DialogueState uses dict, not Pydantic models)
    if hasattr(nlu_result_raw, "model_dump"):
        nlu_result = nlu_result_raw.model_dump()
    else:
        # Fallback if already a dict (shouldn't happen with SoniDU)
        nlu_result = nlu_result_raw if isinstance(nlu_result_raw, dict) else {}

    return {
        "nlu_result": nlu_result,
        "conversation_state": "understanding",
        "last_nlu_call": time.time(),
    }
