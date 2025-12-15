"""Simplified dialogue graph for Soni v3.0.

Architecture:
    START → understand → execute → step → respond → END
                  ↑__________________|
                 (loop while flow active)

Only 4 nodes:
- understand: NLU → Commands
- execute: Commands → State updates
- step: Run current flow step
- respond: Generate response
"""

import logging
from typing import Any

from langgraph.checkpoint.memory import InMemorySaver
from langgraph.graph import END, START, StateGraph

from soni.core.constants import FlowState, NodeName
from soni.core.types import DialogueState, RuntimeContext

logger = logging.getLogger(__name__)


def build_graph(context: RuntimeContext, checkpointer: Any | None = None) -> Any:
    """Build the simplified Soni v3.0 dialogue graph.
    
    Args:
        context: Runtime context with dependencies
        checkpointer: Optional LangGraph checkpointer
        
    Returns:
        Compiled LangGraph
    """
    from soni.dm.nodes.understand import understand_node
    from soni.dm.nodes.execute import execute_node
    from soni.dm.nodes.step import step_node
    from soni.dm.nodes.respond import respond_node
    
    builder = StateGraph(DialogueState)
    
    # Wrap nodes to inject context
    def wrap(node_fn):
        async def wrapped(state: DialogueState) -> dict[str, Any]:
            result = await node_fn(state, context)
            return dict(result) if result else {}
        wrapped.__name__ = node_fn.__name__
        return wrapped
    
    # Add nodes
    builder.add_node(NodeName.UNDERSTAND, wrap(understand_node))
    builder.add_node(NodeName.EXECUTE, wrap(execute_node))
    builder.add_node(NodeName.STEP, wrap(step_node))
    builder.add_node(NodeName.RESPOND, wrap(respond_node))
    
    # Define edges
    # START → understand (always start with NLU)
    builder.add_edge(START, NodeName.UNDERSTAND)
    
    # understand → execute (process commands)
    builder.add_edge(NodeName.UNDERSTAND, NodeName.EXECUTE)
    
    # execute → step (run current step)
    builder.add_edge(NodeName.EXECUTE, NodeName.STEP)
    
    # step → conditional routing
    def route_after_step(state: DialogueState) -> str:
        """Route based on flow state."""
        flow_state = state.get("flow_state", FlowState.DONE)
        
        if flow_state == FlowState.WAITING_INPUT:
            # Need user input, generate response and end turn
            return NodeName.RESPOND
        elif flow_state == FlowState.RUNNING:
            # More steps to execute, continue
            return NodeName.STEP
        else:  # DONE
            return NodeName.RESPOND
    
    builder.add_conditional_edges(
        NodeName.STEP,
        route_after_step,
        {
            NodeName.STEP: NodeName.STEP,
            NodeName.RESPOND: NodeName.RESPOND,
        }
    )
    
    # respond → END
    builder.add_edge(NodeName.RESPOND, END)
    
    # Compile
    if checkpointer is None:
        checkpointer = InMemorySaver()
    
    return builder.compile(checkpointer=checkpointer)
