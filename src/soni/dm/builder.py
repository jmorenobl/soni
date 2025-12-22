"""Orchestrator builder for M7 (ADR-002 compliant interrupt architecture).

The orchestrator uses a simplified flow:
    understand → execute_flow → END

The execute_flow node handles all interrupt/resume logic internally using
LangGraph's interrupt() mechanism.
"""

from typing import Any

from langgraph.checkpoint.base import BaseCheckpointSaver
from langgraph.graph import END, StateGraph
from langgraph.graph.state import CompiledStateGraph

from soni.compiler.subgraph import build_flow_subgraph
from soni.config.models import SoniConfig
from soni.core.types import DialogueState
from soni.dm.nodes.execute_flow import execute_flow_node
from soni.dm.nodes.understand import understand_node
from soni.runtime.context import RuntimeContext


def compile_all_subgraphs(config: SoniConfig) -> dict[str, CompiledStateGraph]:
    """Compile subgraphs for all flows in config.

    Returns:
        Dict mapping flow_name to compiled subgraph.
    """
    subgraphs: dict[str, Any] = {}
    for flow_name, flow_config in config.flows.items():
        subgraphs[flow_name] = build_flow_subgraph(flow_config)
    return subgraphs


def build_orchestrator(
    checkpointer: BaseCheckpointSaver | None = None,
) -> CompiledStateGraph:
    """Build the main orchestrator graph.

    Graph flow: understand → execute_flow → END

    The execute_flow node handles interrupt/resume internally (ADR-002).
    """
    builder: StateGraph[DialogueState, RuntimeContext] = StateGraph(
        DialogueState, context_schema=RuntimeContext
    )

    builder.add_node("understand", understand_node)
    builder.add_node("execute_flow", execute_flow_node)

    builder.set_entry_point("understand")
    builder.add_edge("understand", "execute_flow")
    builder.add_edge("execute_flow", END)

    return builder.compile(checkpointer=checkpointer)
