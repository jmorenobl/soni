"""Orchestrator builder for M7 (interrupt architecture).

The orchestrator uses a specific flow:
    human_input_gate → nlu → orchestrator → (loop back if pending task)

The human_input_gate handles all interrupt/resume logic using
LangGraph's interrupt() mechanism.
"""

from typing import Any

from langgraph.checkpoint.base import BaseCheckpointSaver
from langgraph.graph import END, StateGraph
from langgraph.graph.state import CompiledStateGraph

from soni.compiler.subgraph import build_flow_subgraph
from soni.config.models import SoniConfig
from soni.core.types import DialogueState
from soni.dm.nodes.human_input_gate import human_input_gate
from soni.dm.nodes.orchestrator import orchestrator_node
from soni.dm.nodes.understand import understand_node
from soni.dm.routing import route_after_orchestrator
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
) -> CompiledStateGraph[DialogueState, RuntimeContext, Any, Any]:
    """Build the main orchestrator graph with Human Input Gate.

    Graph structure:
    human_input_gate -> nlu -> orchestrator
    orchestrator --(loop)--> human_input_gate
    """
    builder: StateGraph[DialogueState, RuntimeContext] = StateGraph(
        DialogueState, context_schema=RuntimeContext
    )

    # Nodes
    builder.add_node("human_input_gate", human_input_gate)
    builder.add_node("nlu", understand_node)
    builder.add_node("orchestrator", orchestrator_node)

    # Edges
    builder.set_entry_point("human_input_gate")
    builder.add_edge("human_input_gate", "nlu")
    builder.add_edge("nlu", "orchestrator")

    # Routing
    builder.add_conditional_edges(
        "orchestrator",
        route_after_orchestrator,
        {"pending_task": "human_input_gate", "end": END},
    )

    return builder.compile(checkpointer=checkpointer)
