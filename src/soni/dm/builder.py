"""Orchestrator builder for M1."""

from langgraph.graph import StateGraph, END

from soni.dm.nodes.execute import execute_node
from soni.core.types import DialogueState
from soni.runtime.context import RuntimeContext


def build_orchestrator():
    """Build the main orchestrator graph."""
    builder = StateGraph(DialogueState, context_schema=RuntimeContext)
    
    builder.add_node("execute", execute_node)
    builder.set_entry_point("execute")
    builder.add_edge("execute", END)
    
    return builder.compile()
