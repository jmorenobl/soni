"""Graph builder for LangGraph dialogue management."""

import logging
from typing import Any

from langgraph.checkpoint.memory import InMemorySaver
from langgraph.graph import END, START, StateGraph

from soni.core.types import DialogueState, RuntimeContext
from soni.dm.nodes.collect_next_slot import collect_next_slot_node
from soni.dm.nodes.confirm_action import confirm_action_node
from soni.dm.nodes.execute_action import execute_action_node
from soni.dm.nodes.generate_response import generate_response_node
from soni.dm.nodes.handle_confirmation import handle_confirmation_node
from soni.dm.nodes.handle_correction import handle_correction_node
from soni.dm.nodes.handle_digression import handle_digression_node
from soni.dm.nodes.handle_intent_change import handle_intent_change_node
from soni.dm.nodes.handle_modification import handle_modification_node
from soni.dm.nodes.understand import understand_node
from soni.dm.nodes.validate_slot import validate_slot_node
from soni.dm.routing import (
    route_after_action,
    route_after_collect_next_slot,
    route_after_confirmation,
    route_after_correction,
    route_after_modification,
    route_after_understand,
    route_after_validate,
)

logger = logging.getLogger(__name__)


class RuntimeWrapper:
    """Wrapper to inject RuntimeContext into node functions.

    LangGraph nodes receive (state, config) but our nodes expect (state, runtime)
    where runtime.context contains dependencies. This wrapper bridges that gap.
    """

    def __init__(self, context: RuntimeContext):
        self.context = context


def _wrap_node(node_fn: Any, context: RuntimeContext) -> Any:
    """Wrap a node function to inject RuntimeContext.

    Args:
        node_fn: Original node function expecting (state, runtime)
        context: RuntimeContext to inject

    Returns:
        Wrapped function that LangGraph can call with (state) or (state, config)
    """
    runtime = RuntimeWrapper(context)

    async def wrapped(state: DialogueState) -> dict[str, Any]:
        result = await node_fn(state, runtime)
        return dict(result) if result else {}

    # Preserve function name for debugging
    wrapped.__name__ = getattr(node_fn, "__name__", "wrapped_node")
    return wrapped


def build_graph(
    context: RuntimeContext,
    checkpointer: Any | None = None,  # BaseCheckpointSaver - using Any to avoid import issues
) -> Any:  # CompiledStateGraph - using Any to avoid import issues
    """
    Build LangGraph from Soni configuration.

    Args:
        context: Runtime context with dependencies
        checkpointer: Optional checkpointer (defaults to InMemorySaver)

    Returns:
        Compiled graph ready for execution
    """
    # Create graph with state schema
    # Note: context_schema may not be supported in all LangGraph versions
    # Runtime context is passed via runtime parameter in nodes
    builder = StateGraph(DialogueState)

    # Wrap nodes to inject RuntimeContext
    # LangGraph calls nodes with (state) or (state, config), but our nodes expect (state, runtime)
    # where runtime.context contains dependencies
    builder.add_node("understand", _wrap_node(understand_node, context))
    builder.add_node("validate_slot", _wrap_node(validate_slot_node, context))
    builder.add_node("handle_correction", _wrap_node(handle_correction_node, context))
    builder.add_node("handle_modification", _wrap_node(handle_modification_node, context))
    builder.add_node("collect_next_slot", _wrap_node(collect_next_slot_node, context))
    builder.add_node("confirm_action", _wrap_node(confirm_action_node, context))
    builder.add_node("handle_confirmation", _wrap_node(handle_confirmation_node, context))
    builder.add_node("handle_intent_change", _wrap_node(handle_intent_change_node, context))
    builder.add_node("handle_digression", _wrap_node(handle_digression_node, context))
    builder.add_node("execute_action", _wrap_node(execute_action_node, context))
    builder.add_node("generate_response", _wrap_node(generate_response_node, context))

    # Entry point: START → understand (ALWAYS)
    builder.add_edge(START, "understand")

    # Conditional routing from understand
    builder.add_conditional_edges(
        "understand",
        route_after_understand,
        {
            "validate_slot": "validate_slot",
            "handle_correction": "handle_correction",
            "handle_modification": "handle_modification",
            "handle_digression": "handle_digression",
            "handle_intent_change": "handle_intent_change",
            "handle_confirmation": "handle_confirmation",
            "collect_next_slot": "collect_next_slot",  # For continuation
            "generate_response": "generate_response",
        },
    )

    # After digression, back to understand
    builder.add_edge("handle_digression", "understand")

    # After validating slot
    builder.add_conditional_edges(
        "validate_slot",
        route_after_validate,
        {
            "execute_action": "execute_action",
            "confirm_action": "confirm_action",
            "collect_next_slot": "collect_next_slot",
            "generate_response": "generate_response",  # For completed flows or fallback
        },
    )

    # After handling correction
    builder.add_conditional_edges(
        "handle_correction",
        route_after_correction,
        {
            "execute_action": "execute_action",
            "confirm_action": "confirm_action",
            "collect_next_slot": "collect_next_slot",
            "generate_response": "generate_response",
        },
    )

    # After handling modification
    builder.add_conditional_edges(
        "handle_modification",
        route_after_modification,
        {
            "execute_action": "execute_action",
            "confirm_action": "confirm_action",
            "collect_next_slot": "collect_next_slot",
            "generate_response": "generate_response",
        },
    )

    # After collecting slot, route based on conversation_state
    # If all slots are filled and we advanced to next step, go directly to that step
    # Otherwise, go to understand to process user's response
    builder.add_conditional_edges(
        "collect_next_slot",
        route_after_collect_next_slot,
        {
            "execute_action": "execute_action",
            "confirm_action": "confirm_action",
            "understand": "understand",
            "generate_response": "generate_response",
        },
    )

    # After confirmation request, route based on whether confirmation was already processed
    # If confirm_action already processed the response (after resume), go to generate_response
    # Otherwise, go to understand to process the user's yes/no
    def route_after_confirm_action(state: DialogueState) -> str:
        """Route after confirm_action based on whether confirmation was already processed.

        When confirm_action is re-executed after resume and detects that the confirmation
        was already processed (has last_response from handle_confirmation), it should
        go directly to generate_response instead of understand to avoid loops.
        """
        # Check if handle_confirmation already processed this confirmation
        # Use metadata flag instead of checking response text (more robust and configurable)
        metadata = state.get("metadata", {})
        confirmation_processed = metadata.get("_confirmation_processed", False)

        if confirmation_processed:
            # handle_confirmation already processed the response
            # Go directly to generate_response to avoid loop
            logger.info(
                "route_after_confirm_action: Confirmation already processed by handle_confirmation, "
                "routing to generate_response"
            )
            return "generate_response"
        else:
            # First time or no response yet - go to understand to process user's yes/no
            return "understand"

    builder.add_conditional_edges(
        "confirm_action",
        route_after_confirm_action,
        {
            "understand": "understand",  # First time - process user's response
            "generate_response": "generate_response",  # Already processed - show response
        },
    )

    # After handling confirmation response, route based on result
    builder.add_conditional_edges(
        "handle_confirmation",
        route_after_confirmation,
        {
            "execute_action": "execute_action",  # User confirmed
            "generate_response": "generate_response",  # Unclear, errors, or denials
        },
    )

    # After intent change, go to collect_next_slot to start the new flow
    # (not back to understand, which would create an infinite loop)
    builder.add_edge("handle_intent_change", "collect_next_slot")

    # After executing action, route based on conversation_state
    builder.add_conditional_edges(
        "execute_action",
        route_after_action,
        {
            "execute_action": "execute_action",  # Another action to execute
            "confirm_action": "confirm_action",  # Ready for confirmation
            "generate_response": "generate_response",  # Flow complete
        },
    )
    builder.add_edge("generate_response", END)

    # Compile with checkpointer
    if checkpointer is None:
        checkpointer = InMemorySaver()

    return builder.compile(checkpointer=checkpointer)
