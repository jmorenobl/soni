"""Subgraph builder - compiles FlowConfig to StateGraph."""

from typing import Any

from langchain_core.runnables import RunnableConfig
from langgraph.graph import END, START, StateGraph

from soni.compiler.factory import get_factory_for_step
from soni.core.config import FlowConfig, StepConfig
from soni.core.constants import NodeName
from soni.core.types import DialogueState, RuntimeContext

# Constant for special node name
END_FLOW_NODE = NodeName.END_FLOW


async def end_flow_node(
    state: DialogueState,
    config: RunnableConfig,
) -> dict[str, Any]:
    """Node that pops the completed flow from the stack.

    This is automatically added as the final node before END
    in every flow subgraph to ensure proper stack cleanup.
    """
    # context: RuntimeContext = config["configurable"]["runtime_context"]
    # flow_manager was used for pop, now handled by resume_node
    # flow_manager = context.flow_manager

    # Do NOT pop the flow here.
    # Stack management is now handled by the Orchestrator's resume_node.
    # We just mark the state as idle/completed for this level if needed,
    # or simply return. The Orchestrator will see the subgraph finished.
    # For now, we return nothing or just metadata update.

    return {
        # "flow_state": "completed" # optional?
    }


class SubgraphBuilder:
    """Builds a StateGraph from a FlowConfig."""

    def build(self, flow_config: FlowConfig) -> StateGraph[Any, Any]:
        """Build a StateGraph from flow configuration."""
        # Define context schema at graph level for DI
        builder: StateGraph[Any, Any] = StateGraph(DialogueState, context_schema=RuntimeContext)
        steps = flow_config.steps_or_process

        if not steps:
            return self._build_empty_graph(builder)

        # Create nodes for each step
        step_names = []
        for step in steps:
            name = step.step
            step_names.append(name)

            factory = get_factory_for_step(step.type)
            node_fn = factory.create(step)
            builder.add_node(name, node_fn)

        # Add the __end_flow__ node for proper stack cleanup
        builder.add_node(END_FLOW_NODE, end_flow_node)

        # Create edges
        self._add_edges(builder, steps, step_names)

        return builder

    def _build_empty_graph(self, builder: StateGraph[Any, Any]) -> StateGraph[Any, Any]:
        """Handle empty flow case."""
        # Even empty flows need end_flow_node to pop from stack
        builder.add_node(END_FLOW_NODE, end_flow_node)
        builder.add_edge(START, END_FLOW_NODE)
        builder.add_edge(END_FLOW_NODE, END)
        return builder

    def _add_edges(
        self,
        builder: StateGraph[Any, Any],
        steps: list[StepConfig],
        step_names: list[str],
    ) -> None:
        """Add edges between nodes."""
        step_set = set(step_names)

        if not step_names:
            return

        # START -> first step
        builder.add_edge(START, step_names[0])

        for i, step in enumerate(steps):
            name = step_names[i]
            # Determine next step in sequence
            next_step = step_names[i + 1] if i < len(steps) - 1 else None

            # Default: go to next step, or to __end_flow__ if last step
            target = next_step if next_step else END_FLOW_NODE

            # If jump_to is present, it overrides next_step
            if step.jump_to:
                if step.jump_to in step_set:
                    target = step.jump_to
                else:
                    # Jump to unknown step means end flow
                    target = END_FLOW_NODE

            def create_router(target_node: str, step: StepConfig):
                """Create router that handles pausing, branching, and normal flow."""

                def router(state: DialogueState) -> str:
                    # Check if we should pause execution
                    if state.get("flow_state") == "waiting_input":
                        return str(END)

                    # For branch steps, check for target override
                    if step.type == "branch":
                        branch_target = state.get("_branch_target")
                        if branch_target:
                            return str(branch_target)

                    return target_node

                return router

            builder.add_conditional_edges(name, create_router(target, step))

        # __end_flow__ -> END
        builder.add_edge(END_FLOW_NODE, END)
