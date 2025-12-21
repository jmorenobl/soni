"""Subgraph builder for M1."""

from langgraph.graph import StateGraph, END

from soni.compiler.factory import get_factory_for_step
from soni.config.models import FlowConfig
from soni.core.types import DialogueState
from soni.runtime.context import RuntimeContext


def build_flow_subgraph(flow: FlowConfig):
    """Build a compiled subgraph for a flow."""
    builder = StateGraph(DialogueState, context_schema=RuntimeContext)
    
    prev_step = None
    for i, step in enumerate(flow.steps):
        factory = get_factory_for_step(step.type)
        node_fn = factory.create(step, flow.steps, i)
        builder.add_node(step.step, node_fn)
        
        if i == 0:
            builder.set_entry_point(step.step)
        
        if prev_step:
            builder.add_edge(prev_step, step.step)
        
        prev_step = step.step
    
    # Last step -> END
    if prev_step:
        builder.add_edge(prev_step, END)
    
    return builder.compile()
