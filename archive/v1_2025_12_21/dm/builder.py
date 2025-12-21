"""Graph construction logic."""

from langchain_core.runnables import Runnable
from langgraph.checkpoint.base import BaseCheckpointSaver
from langgraph.graph import END, START, StateGraph
from soni.compiler.subgraph import SubgraphBuilder
from soni.core.constants import NodeName
from soni.core.types import DialogueState, RuntimeContext

from soni.config import SoniConfig
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

    builder.add_node(NodeName.RESUME, resume_node)

    # Core nodes
    builder.add_node(NodeName.UNDERSTAND, understand_node)
    builder.add_node(NodeName.EXECUTE, execute_node)
    builder.add_node(NodeName.RESPOND, respond_node)

    # Flow subgraph nodes are NOT added to the main graph anymore.
    # They are invoked dynamically by execute_node.

    # Edges
    builder.add_edge(START, NodeName.UNDERSTAND)
    builder.add_edge(NodeName.UNDERSTAND, NodeName.EXECUTE)

    # Edges from flows to resume logic
    # NOT needed as subgraphs are isolated execution units invoked by execute_node

    # Conditional logic after resume
    def route_resume(state: DialogueState) -> str:
        """Route after resume node.

        If there's an active flow, loop back to execute it.
        Otherwise, go to respond to end the turn.
        """
        if state.get("flow_stack"):
            return NodeName.LOOP
        return NodeName.END

    builder.add_conditional_edges(
        NodeName.RESUME,
        route_resume,
        {
            NodeName.LOOP: NodeName.EXECUTE,  # Resume parent flow
            NodeName.END: NodeName.RESPOND,  # End turn
        },
    )

    builder.add_edge(NodeName.RESPOND, END)

    # Note: 'execute' node uses Command to route to specific flow_{name},
    # so no explicit edges from 'execute' are needed if coverage via Command is complete.
    # However, if 'execute' returns 'respond', we need that edge or allow Command routing there too.
    # Command(goto="respond") covers it.

    compiled_graph = builder.compile(checkpointer=checkpointer)
    return compiled_graph, subgraphs
