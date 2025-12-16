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

            # Handle explicit jump_to (static routing)
            if step.jump_to:
                target = step.jump_to
                # If target is not in this flow, it might be END or error?
                # For now assume if not in step_set, it's END (or we could raise validation error)
                if target not in step_set:
                     target = END

                builder.add_edge(name, target)
                continue

            # Default sequential edge
            if next_step:
                builder.add_edge(name, next_step)
            else:
                builder.add_edge(name, END)
