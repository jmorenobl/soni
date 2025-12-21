"""Subgraph builder for M1."""

from langgraph.graph import END, StateGraph

from soni.compiler.factory import get_factory_for_step
from soni.config.models import FlowConfig
from soni.core.types import DialogueState
from soni.runtime.context import RuntimeContext


def build_flow_subgraph(flow: FlowConfig):
    """Build a compiled subgraph for a flow."""
    builder = StateGraph(DialogueState, context_schema=RuntimeContext)

    def _create_router(target: str):
        """Create router that checks _need_input first."""

        def router(state: DialogueState) -> str:
            if state.get("_need_input"):
                return END
            return target

        return router

    prev_node_name = None

    for i, step in enumerate(flow.steps):
        factory = get_factory_for_step(step.type)
        # Assuming step_index and all_steps passed if simpler signature allowed,
        # but factory.create signature in M1/M2 is: create(step, all_steps, index)
        node_func = factory.create(step, flow.steps, i)
        node_name = node_func.__name__

        builder.add_node(node_name, node_func)

        if prev_node_name:
            # Add conditional edge from prev -> current
            builder.add_conditional_edges(
                prev_node_name,
                _create_router(node_name),
                # path_map optional if return values match node names or END
            )
        else:
            builder.set_entry_point(node_name)

        prev_node_name = node_name

    # Final node routes to END if not interrupted
    if prev_node_name:
        builder.add_conditional_edges(prev_node_name, _create_router(END))

    return builder.compile()
