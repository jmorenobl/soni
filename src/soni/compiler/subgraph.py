"""Subgraph builder - compiles FlowConfig to StateGraph."""

from langgraph.graph import END, START, StateGraph

from soni.compiler.factory import get_factory_for_step
from soni.core.config import FlowConfig, StepConfig
from soni.core.types import DialogueState, RuntimeContext


class SubgraphBuilder:
    """Builds a StateGraph from a FlowConfig."""

    def build(self, flow_config: FlowConfig) -> StateGraph:
        """Build a StateGraph from flow configuration."""
        # Define context schema at graph level for DI
        builder = StateGraph(DialogueState, context_schema=RuntimeContext)
        steps = flow_config.steps_or_process

        if not steps:
            return self._build_empty_graph(builder)

        # Create nodes
        step_names = []
        for step in steps:
            name = step.step
            step_names.append(name)

            factory = get_factory_for_step(step.type)
            node_fn = factory.create(step)
            builder.add_node(name, node_fn)

        # Create edges
        self._add_edges(builder, steps, step_names)

        return builder

    def _build_empty_graph(self, builder: StateGraph) -> StateGraph:
        """Handle empty flow case."""
        builder.add_edge(START, END)
        return builder

    def _add_edges(
        self,
        builder: StateGraph,
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

            # Default sequential edge
            # We must use conditional logic to stop if flow paused (waiting_input)

            def create_router(target_node):
                def router(state: DialogueState):
                    # Check if we should pause execution
                    if state.get("flow_state") == "waiting_input":
                        return END
                    return target_node

                return router

            target = next_step if next_step else END

            # If jump_to is present, it overrides next_step
            if step.jump_to:
                if step.jump_to in step_set:
                    target = step.jump_to
                else:
                    target = END

            builder.add_conditional_edges(name, create_router(target))
