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
    nlu_provider = runtime.context["nlu_provider"]
    flow_manager = runtime.context["flow_manager"]
    scope_manager = runtime.context["scope_manager"]

    # Build NLU context
    active_ctx = flow_manager.get_active_context(state)
    current_flow_name = active_ctx["flow_name"] if active_ctx else "none"

    dialogue_context = {
        "current_slots": (state["flow_slots"].get(active_ctx["flow_id"], {}) if active_ctx else {}),
        "available_actions": scope_manager.get_available_actions(state),
        "available_flows": scope_manager.get_available_flows(state),
        "current_flow": current_flow_name,
        "expected_slots": [],  # TODO: Get from flow definition
        "history": state["messages"][-5:] if state["messages"] else [],  # Last 5 messages
    }

    # Call NLU
    nlu_result = await nlu_provider.understand(
        state["user_message"],
        dialogue_context,
    )

    return {
        "nlu_result": nlu_result,
        "conversation_state": "understanding",
        "last_nlu_call": time.time(),
    }
