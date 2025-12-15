"""Orchestrator Graph for Soni v3.0.

This module implements the proper subgraph architecture:

    Main Orchestrator:
        START → understand → select_flow → [flow_subgraphs] → respond → END
    
    Flow Subgraphs (compiled from YAML):
        book_flight:  step1 → step2 → step3 → ...
        cancel_order: step1 → step2 → ...

Each flow is compiled to its own StateGraph and added as a subgraph.
"""

import logging
from typing import Any

from langgraph.checkpoint.memory import InMemorySaver
from langgraph.graph import END, START, StateGraph

from soni.core.config import SoniConfig
from soni.core.constants import FlowState, NodeName
from soni.core.types import DialogueState, RuntimeContext

logger = logging.getLogger(__name__)


class OrchestratorGraph:
    """Builds an orchestrator graph with flow subgraphs.
    
    This is the proper subgraph architecture where each flow
    is compiled to its own StateGraph and composed into a main
    orchestrator graph.
    """
    
    def __init__(
        self,
        config: SoniConfig,
        context: RuntimeContext,
    ) -> None:
        """Initialize with config and runtime context.
        
        Args:
            config: Soni configuration with flow definitions
            context: Runtime context with dependencies
        """
        self.config = config
        self.context = context
        self._flow_subgraphs: dict[str, StateGraph] = {}
    
    def compile_flows(self) -> None:
        """Compile each flow in config to a subgraph.
        
        Creates a StateGraph for each flow definition that can
        be invoked by the orchestrator.
        """
        from soni.dm.subgraph_builder import build_flow_subgraph
        
        for flow_name in self.config.flows:
            logger.info(f"Compiling flow subgraph: {flow_name}")
            subgraph = build_flow_subgraph(
                flow_name=flow_name,
                config=self.config,
                context=self.context,
            )
            self._flow_subgraphs[flow_name] = subgraph
    
    def build(self, checkpointer: Any | None = None) -> Any:
        """Build the complete orchestrator graph.
        
        Architecture:
            START → understand → execute → route_flow → [subgraphs] → respond → END
        
        Args:
            checkpointer: Optional LangGraph checkpointer
            
        Returns:
            Compiled LangGraph with subgraphs
        """
        from soni.dm.nodes.understand import understand_node
        from soni.dm.nodes.execute import execute_node
        from soni.dm.nodes.respond import respond_node
        
        builder = StateGraph(DialogueState)
        context = self.context
        
        # Wrap nodes to inject context
        def wrap(node_fn):
            async def wrapped(state: DialogueState) -> dict[str, Any]:
                result = await node_fn(state, context)
                return dict(result) if result else {}
            wrapped.__name__ = node_fn.__name__
            return wrapped
        
        # Add orchestrator nodes
        builder.add_node(NodeName.UNDERSTAND, wrap(understand_node))
        builder.add_node(NodeName.EXECUTE, wrap(execute_node))
        builder.add_node(NodeName.RESPOND, wrap(respond_node))
        
        # Add each flow as a subgraph
        for flow_name, subgraph in self._flow_subgraphs.items():
            # Compile subgraph (no checkpointer for internal subgraphs)
            compiled_subgraph = subgraph.compile()
            builder.add_node(f"flow_{flow_name}", compiled_subgraph)
        
        # START → understand
        builder.add_edge(START, NodeName.UNDERSTAND)
        
        # understand → execute
        builder.add_edge(NodeName.UNDERSTAND, NodeName.EXECUTE)
        
        # execute → route to flow or respond
        def route_after_execute(state: DialogueState) -> str:
            """Route to active flow subgraph or respond."""
            flow_stack = state.get("flow_stack", [])
            flow_state = state.get("flow_state", FlowState.DONE)
            
            if flow_stack and flow_state == FlowState.RUNNING:
                active_flow = flow_stack[-1]["flow_name"]
                if f"flow_{active_flow}" in [f"flow_{f}" for f in self._flow_subgraphs]:
                    return f"flow_{active_flow}"
            
            return NodeName.RESPOND
        
        # Build routing map
        routing_map: dict[str, str] = {NodeName.RESPOND: NodeName.RESPOND}
        for flow_name in self._flow_subgraphs:
            routing_map[f"flow_{flow_name}"] = f"flow_{flow_name}"
        
        builder.add_conditional_edges(
            NodeName.EXECUTE,
            route_after_execute,
            routing_map,
        )
        
        # Each flow subgraph → respond
        for flow_name in self._flow_subgraphs:
            builder.add_edge(f"flow_{flow_name}", NodeName.RESPOND)
        
        # respond → END
        builder.add_edge(NodeName.RESPOND, END)
        
        # Compile
        if checkpointer is None:
            checkpointer = InMemorySaver()
        
        return builder.compile(checkpointer=checkpointer)


def build_orchestrator_graph(
    config: SoniConfig,
    context: RuntimeContext,
    checkpointer: Any | None = None,
) -> Any:
    """Convenience function to build orchestrator graph.
    
    Args:
        config: Soni configuration
        context: Runtime context
        checkpointer: Optional checkpointer
        
    Returns:
        Compiled orchestrator graph with flow subgraphs
    """
    orchestrator = OrchestratorGraph(config, context)
    orchestrator.compile_flows()
    return orchestrator.build(checkpointer)
