"""Orchestrator builder for M4 (NLU integration)."""

from langgraph.checkpoint.base import BaseCheckpointSaver
from langgraph.graph import END, StateGraph

from soni.core.types import DialogueState
from soni.dm.nodes.execute import execute_node
from soni.dm.nodes.understand import understand_node
from soni.runtime.context import RuntimeContext


def build_orchestrator(checkpointer: BaseCheckpointSaver | None = None):
    """Build the main orchestrator graph.

    Graph flow: understand → execute → END
    """
    builder = StateGraph(DialogueState, context_schema=RuntimeContext)

    builder.add_node("understand", understand_node)
    builder.add_node("execute", execute_node)

    builder.set_entry_point("understand")
    builder.add_edge("understand", "execute")
    builder.add_edge("execute", END)

    return builder.compile(checkpointer=checkpointer)
