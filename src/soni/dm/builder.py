"""Graph builder for LangGraph dialogue management (v2.0 Command-Driven)."""

import logging
from typing import Any

from langgraph.checkpoint.memory import InMemorySaver
from langgraph.graph import END, START, StateGraph

from soni.core.constants import NodeName
from soni.core.types import DialogueState, RuntimeContext
from soni.dm.executor import execute_commands_node
from soni.dm.nodes.collect_next_slot import collect_next_slot_node
from soni.dm.nodes.confirm_action import confirm_action_node
from soni.dm.nodes.execute_action import execute_action_node
from soni.dm.nodes.generate_response import generate_response_node
from soni.dm.nodes.understand import understand_node
from soni.dm.routing import route_next

logger = logging.getLogger(__name__)


class RuntimeWrapper:
    """Wrapper to inject RuntimeContext into node functions."""

    def __init__(self, context: RuntimeContext):
        self.context = context


def _wrap_node(node_fn: Any, context: RuntimeContext) -> Any:
    """Wrap a node function to inject RuntimeContext."""
    runtime = RuntimeWrapper(context)

    async def wrapped(state: DialogueState) -> dict[str, Any]:
        result = await node_fn(state, runtime)
        return dict(result) if result else {}

    wrapped.__name__ = getattr(node_fn, "__name__", "wrapped_node")
    return wrapped


def build_graph(
    context: RuntimeContext,
    checkpointer: Any | None = None,
) -> Any:
    """
    Build LangGraph from Soni configuration (v2.0).

    Graph Structure:
    START -> Understand (NLU) -> Execute Commands -> Router -> [Next Node]
    """
    builder = StateGraph(DialogueState)

    # 1. Add Nodes
    # Understand: NLU -> Commands
    builder.add_node("understand", _wrap_node(understand_node, context))

    # Execute Commands: Commands -> State Updates
    builder.add_node(NodeName.EXECUTE_COMMANDS, _wrap_node(execute_commands_node, context))

    # Execution Nodes
    builder.add_node(NodeName.COLLECT_NEXT_SLOT, _wrap_node(collect_next_slot_node, context))
    builder.add_node(NodeName.CONFIRM_ACTION, _wrap_node(confirm_action_node, context))
    builder.add_node(NodeName.EXECUTE_ACTION, _wrap_node(execute_action_node, context))
    builder.add_node(NodeName.GENERATE_RESPONSE, _wrap_node(generate_response_node, context))

    # 2. Define Edges

    # START -> Understand
    builder.add_edge(START, "understand")

    # Understand -> Execute Commands
    builder.add_edge("understand", NodeName.EXECUTE_COMMANDS)

    # Execute Commands -> Router (Conditional)
    builder.add_conditional_edges(
        NodeName.EXECUTE_COMMANDS,
        route_next,
        {
            NodeName.EXECUTE_ACTION: NodeName.EXECUTE_ACTION,
            NodeName.CONFIRM_ACTION: NodeName.CONFIRM_ACTION,
            NodeName.COLLECT_NEXT_SLOT: NodeName.COLLECT_NEXT_SLOT,
            NodeName.GENERATE_RESPONSE: NodeName.GENERATE_RESPONSE,
            "END": NodeName.GENERATE_RESPONSE,  # If ending turn, usually generate response unless streaming
        },
    )

    # Post-Node Routing logic (simplified for now - always generate response or loop back?)
    # In v2.0, we usually generate response after doing something, then END.

    builder.add_edge(NodeName.COLLECT_NEXT_SLOT, NodeName.GENERATE_RESPONSE)
    builder.add_edge(NodeName.CONFIRM_ACTION, NodeName.GENERATE_RESPONSE)
    builder.add_edge(NodeName.EXECUTE_ACTION, NodeName.GENERATE_RESPONSE)

    builder.add_edge(NodeName.GENERATE_RESPONSE, END)

    # Compile
    if checkpointer is None:
        checkpointer = InMemorySaver()

    return builder.compile(checkpointer=checkpointer)
