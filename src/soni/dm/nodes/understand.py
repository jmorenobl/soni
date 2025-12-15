"""Understand node for NLU processing."""

import logging
import time

from soni.core.types import DialogueState, NodeRuntime
from soni.utils.metadata_manager import MetadataManager

logger = logging.getLogger(__name__)


async def understand_node(
    state: DialogueState,
    runtime: NodeRuntime,
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
    available_flows = scope_manager.get_available_flows(state)
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

    # Get the specific slot we're waiting for (if any)
    waiting_for_slot = state.get("waiting_for_slot")

    # Build structured types directly (no adapter needed)
    # This follows the design in docs/design/05-message-flow.md
    import dspy

    from soni.du.models import DialogueContext

    # Build conversation history
    history_messages = state["messages"][-5:] if state["messages"] else []  # Last 5 messages
    history = dspy.History(messages=history_messages)

    # Check if we should use two-stage prediction
    # Two-stage: first detect command, then extract slots with correct expected_slots
    # Only applies when no active flow, no expected_slots, and there are available flows
    # This avoids passing all expected_slots from all flows (doesn't scale with many flows)
    # Note: Legacy two-stage prediction logic was removed here.
    # It relied on legacy 'command' strings and 'activate_flow_by_intent'.
    # With Command-Driven architecture, NLU directly produces StartFlow commands via dspy signatures.
    # We fall back to the standard prediction path below, which handles 'none' flow with available actions.
    if False and current_flow_name == "none" and not expected_slots and available_flows:
        pass  # Disabled legacy logic

    else:
        # Normal single-stage prediction (flow active or expected_slots provided)
        # If no active flow and no expected_slots yet, try fallback: combine all expected_slots
        # This helps NLU extract slots when user provides all slots at once (for simple cases)
        if current_flow_name == "none" and not expected_slots and available_flows:
            # Fallback: combine all expected_slots from available flows
            # This works for simple cases but doesn't scale with many flows
            all_expected_slots = set()
            for flow_name in available_flows.keys():
                flow_slots = scope_manager.get_expected_slots(
                    flow_name=flow_name,
                    available_actions=available_actions,
                )
                all_expected_slots.update(flow_slots)
            expected_slots = list(all_expected_slots)
            logger.debug(
                f"No active flow, providing expected_slots from available_flows {list(available_flows.keys())}: {expected_slots}"
            )

        # Build structured dialogue context
        dialogue_context = DialogueContext(
            current_slots=(
                state["flow_slots"].get(active_ctx["flow_id"], {}) if active_ctx else {}
            ),
            available_actions=available_actions,
            available_flows=available_flows,
            current_flow=current_flow_name,
            expected_slots=expected_slots,
            current_prompted_slot=waiting_for_slot,  # Prioritize this slot
            conversation_state=state.get("conversation_state"),
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
        # mode='json' ensures enums are serialized as strings (not enum objects)
        # This is required for routing functions to match message_type correctly
        nlu_result = nlu_result_raw.model_dump(mode="json")

    # Clear correction/modification state variables at start of new turn
    # These should only reflect the most recent correction/modification
    metadata = state.get("metadata", {})
    # Clear correction and modification flags at start of new turn
    # (confirmation flags are NOT cleared here - they persist across understand)
    metadata = MetadataManager.clear_correction_flags(metadata)
    metadata = MetadataManager.clear_modification_flags(metadata)

    # Preserve conversation_state if we're in a special state (e.g., confirming)
    # This prevents understand_node from overwriting states that should persist
    current_conv_state = state.get("conversation_state", "")
    if current_conv_state in ("confirming", "ready_for_confirmation"):
        # Preserve the confirmation state - don't overwrite with "understanding"
        new_conv_state = current_conv_state
    else:
        # Normal case - set to understanding
        new_conv_state = "understanding"

    return {
        "nlu_result": nlu_result,
        "conversation_state": new_conv_state,
        "last_nlu_call": time.time(),
        "metadata": metadata,
    }
