"""Graph construction logic."""

from langchain_core.runnables import Runnable
from langgraph.checkpoint.base import BaseCheckpointSaver
from langgraph.graph import END, START, StateGraph

from soni.compiler.subgraph import SubgraphBuilder
from soni.core.config import SoniConfig
from soni.core.types import DialogueState, RuntimeContext
from soni.dm.nodes import execute_node, respond_node, resume_node, understand_node


def build_orchestrator(
    config: SoniConfig, checkpointer: BaseCheckpointSaver | None = None
) -> Runnable:
    """Compile flows and build the complete orchestrator graph."""

    # 1. Compile all flows to subgraphs
    compiler = SubgraphBuilder()
    subgraphs = {}

    if config.flows:
        for name, flow in config.flows.items():
            # Compile each flow config into a subgraph
            # We compile it immediately to be used as a node
            subgraphs[name] = compiler.build(flow).compile()

    # 2. Build orchestrator with compiled subgraphs
    builder = StateGraph(DialogueState, context_schema=RuntimeContext)

    builder.add_node("resume", resume_node)

    # Core nodes
    builder.add_node("understand", understand_node)
    builder.add_node("execute", execute_node)
    builder.add_node("respond", respond_node)

    # Flow subgraph nodes
    for flow_name, subgraph in subgraphs.items():
        node_name = f"flow_{flow_name}"
        builder.add_node(node_name, subgraph)

    # Edges
    builder.add_edge(START, "understand")
    builder.add_edge("understand", "execute")

    # Edges from flows to resume logic
    # When a flow finishes, it goes to resume node to pop stack
    for flow_name in subgraphs:
        node_name = f"flow_{flow_name}"
        builder.add_edge(node_name, "resume")

    # Conditional logic after resume
    def route_resume(state: DialogueState) -> str:
        """Route based on stack state."""
        # If waiting for input, stop execution (pause)
        if state.get("flow_state") == "waiting_input":
            return "end"

        # If stack has items (and not waiting), loop to execute next flow
        if state.get("flow_stack"):
            return "loop"

        return "end"

    builder.add_conditional_edges(
        "resume",
        route_resume,
        {
            "loop": "execute",  # Resume parent flow
            "end": "respond",  # Stack empty, end turn
        },
    )

    builder.add_edge("respond", END)

    # Note: 'execute' node uses Command to route to specific flow_{name},
    # so no explicit edges from 'execute' are needed if coverage via Command is complete.
    # However,    # If 'execute' returns 'respond', we need that edge or allow Command routing there too.
    # Command(goto="respond") covers it.

    return builder.compile(checkpointer=checkpointer)
