"""Graph builder for LangGraph dialogue management."""

from typing import TYPE_CHECKING, Any

from langgraph.checkpoint.memory import InMemorySaver
from langgraph.graph import END, START, StateGraph

if TYPE_CHECKING:
    pass

from soni.core.types import DialogueState, RuntimeContext
from soni.dm.nodes.collect_next_slot import collect_next_slot_node
from soni.dm.nodes.execute_action import execute_action_node
from soni.dm.nodes.generate_response import generate_response_node
from soni.dm.nodes.handle_digression import handle_digression_node
from soni.dm.nodes.handle_intent_change import handle_intent_change_node
from soni.dm.nodes.understand import understand_node
from soni.dm.nodes.validate_slot import validate_slot_node
from soni.dm.routing import route_after_understand, route_after_validate


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

    # Add nodes
    builder.add_node("understand", understand_node)
    builder.add_node("validate_slot", validate_slot_node)
    builder.add_node("collect_next_slot", collect_next_slot_node)
    builder.add_node("handle_intent_change", handle_intent_change_node)
    builder.add_node("handle_digression", handle_digression_node)
    builder.add_node("execute_action", execute_action_node)
    builder.add_node("generate_response", generate_response_node)

    # Entry point: START → understand (ALWAYS)
    builder.add_edge(START, "understand")

    # Conditional routing from understand
    builder.add_conditional_edges(
        "understand",
        route_after_understand,
        {
            "validate_slot": "validate_slot",
            "handle_digression": "handle_digression",
            "handle_intent_change": "handle_intent_change",
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
            "collect_next_slot": "collect_next_slot",
        },
    )

    # After collecting slot, back to understand
    builder.add_edge("collect_next_slot", "understand")

    # After intent change, back to understand
    builder.add_edge("handle_intent_change", "understand")

    # Action → response → END
    builder.add_edge("execute_action", "generate_response")
    builder.add_edge("generate_response", END)

    # Compile with checkpointer
    if checkpointer is None:
        checkpointer = InMemorySaver()

    return builder.compile(checkpointer=checkpointer)
