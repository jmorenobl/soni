"""Subgraph builder - compiles FlowConfig to StateGraph.

Handles:
- Sequential step execution with conditional routing
- While loop back-edges and exit handling
- Branch routing with _branch_target
"""

from copy import deepcopy
from typing import Any

from langgraph.graph import END, START, StateGraph
from soni.config.steps import BranchStepConfig, StepConfig, WhileStepConfig

from soni.compiler.factory import get_factory_for_step
from soni.config.models import FlowConfig
from soni.core.constants import NodeName
from soni.core.errors import GraphBuildError
from soni.core.types import DialogueState, RuntimeContext

# Constant for special node name
END_FLOW_NODE = NodeName.END_FLOW


async def end_flow_node(
    state: DialogueState,
) -> dict[str, Any]:
    """Node that marks flow completion.

    Stack management is handled by the Orchestrator's resume_node.
    """
    # Clear transient state to avoid pollution
    return {"_branch_target": None}


class SubgraphBuilder:
    """Builds a StateGraph from a FlowConfig.

    Key features:
    - Creates nodes for each step
    - Handles while loop semantics (back-edges, exit handling)
    - interrupt() is called directly by collect/confirm nodes
    """

    def build(self, flow_config: FlowConfig) -> StateGraph[Any, Any]:
        """Build a StateGraph from flow configuration."""
        builder: StateGraph[Any, Any] = StateGraph(DialogueState, context_schema=RuntimeContext)
        steps = flow_config.steps

        if not steps:
            return self._build_empty_graph(builder)

        # TRANSFORMATION: Convert while loops to branch + jump_to before building nodes
        steps, name_mappings = self._transform_while_loops(steps)

        # Translate jump_to references using name mappings (from while transformation)
        if name_mappings:
            self._translate_jumps(steps, name_mappings)

        # Create nodes for all steps (now no while nodes, they're transformed to branch)
        step_names = []
        for i, step in enumerate(steps):
            name = step.step
            step_names.append(name)

            factory = get_factory_for_step(step.type)
            node_fn = factory.create(step, all_steps=steps, step_index=i)
            builder.add_node(name, node_fn)

        # Add end_flow node
        builder.add_node(END_FLOW_NODE, end_flow_node)

        # Create simple sequential edges
        self._add_simple_edges(builder, steps, step_names)

        return builder

    def _build_empty_graph(self, builder: StateGraph[Any, Any]) -> StateGraph[Any, Any]:
        """Handle empty flow case."""
        builder.add_node(END_FLOW_NODE, end_flow_node)
        builder.add_edge(START, END_FLOW_NODE)
        builder.add_edge(END_FLOW_NODE, END)
        return builder

    def _transform_while_loops(
        self, steps: list[StepConfig]
    ) -> tuple[list[StepConfig], dict[str, str]]:
        """Transform while loops into branch + jump_to pattern.

        Creates deep copies of steps to avoid mutating input configuration.
        This ensures thread-safe compilation of the same config.
        """
        # Deep copy all steps to avoid mutating input
        # Critical for thread safety when compiling same config concurrently
        mutable_steps = [deepcopy(step) for step in steps]

        transformed_steps = []
        name_mappings: dict[str, str] = {}

        for step in mutable_steps:
            if isinstance(step, WhileStepConfig):
                # Transform while to branch guard - pass mutable_steps so it can modify loop body
                guard_step, mapping = self._compile_while(step, mutable_steps)
                transformed_steps.append(guard_step)
                name_mappings.update(mapping)
            else:
                transformed_steps.append(step)

        return transformed_steps, name_mappings

    def _compile_while(
        self, step: WhileStepConfig, all_steps: list[StepConfig]
    ) -> tuple[StepConfig, dict[str, str]]:
        """Compile a while step into a branch guard step.

        Returns:
            - Guard step (branch that evaluates condition)
            - Name mapping {original_name: guard_name}
        """
        original_name = step.step
        guard_name = f"{original_name}_guard"

        # Pydantic already validates that condition and do are present
        # but check for empty list
        if not step.do:
            raise GraphBuildError(
                f"While step '{original_name}' missing required field 'do'. "
                f"While loops must have a 'do' block with steps to execute."
            )

        if not step.condition:
            raise GraphBuildError(
                f"While step '{original_name}' missing required field 'condition'. "
                f"While loops must have a condition to evaluate."
            )

        # Find exit target
        exit_target = step.exit_to
        if not exit_target:
            # Auto-calculate: first step after all do: steps
            do_step_names = set(step.do)
            try:
                step_index = next(i for i, s in enumerate(all_steps) if s.step == original_name)
            except StopIteration as err:
                raise GraphBuildError(f"Step {original_name} not found in step list") from err

            for i in range(step_index + 1, len(all_steps)):
                if all_steps[i].step not in do_step_names:
                    exit_target = all_steps[i].step
                    break

            if not exit_target:
                exit_target = END_FLOW_NODE

        # Create branch guard step
        guard_step = BranchStepConfig(
            step=guard_name,
            type="branch",
            evaluate=step.condition,  # Now correctly accessible
            cases={
                "true": step.do[0],  # First step in loop body
                "false": exit_target,  # Exit when condition is false
            },
        )

        # Auto-add jump_to on last step of do: block
        last_step_name = step.do[-1]
        try:
            last_step = next(s for s in all_steps if s.step == last_step_name)
            # Note: We can only modify jump_to if the step type allows it.
            # BaseStepConfig defines jump_to, so it should be fine.
            if not last_step.jump_to:
                last_step.jump_to = guard_name
        except StopIteration:
            # Last step might define a jump to something else effectively ending the block or
            # the step list might be structured differently. Warning or error?
            pass

        return guard_step, {original_name: guard_name}

    def _translate_jumps(self, steps: list[StepConfig], name_mappings: dict[str, str]) -> None:
        """Translate jump_to and branch cases using name mappings.

        This ensures:
        - jump_to: my_loop -> jump_to: my_loop_guard
        - User doesn't need to know about _guard suffix
        """
        for step in steps:
            # Translate jump_to
            target = step.jump_to
            if target and target in name_mappings:
                step.jump_to = name_mappings[target]

            # Translate branch cases
            if isinstance(step, BranchStepConfig):
                step.cases = {
                    key: name_mappings.get(target, target) for key, target in step.cases.items()
                }

    def _add_simple_edges(
        self,
        builder: StateGraph[Any, Any],
        steps: list[StepConfig],
        step_names: list[str],
    ) -> None:
        """Add simple sequential edges with routing support."""
        step_set = set(step_names)
        # Include special nodes in valid targets
        valid_targets = step_set | {END_FLOW_NODE}

        if not step_names:
            return

        # START -> first step
        builder.add_edge(START, step_names[0])

        for i, step in enumerate(steps):
            name = step_names[i]
            next_step = step_names[i + 1] if i < len(steps) - 1 else None

            # Determine default target
            if step.jump_to:
                target = step.jump_to if step.jump_to in valid_targets else END_FLOW_NODE
            else:
                target = next_step if next_step else END_FLOW_NODE

            # Create router for conditional edges
            router = self._create_router(target, valid_targets)
            builder.add_conditional_edges(name, router)

        # __end_flow__ -> END
        builder.add_edge(END_FLOW_NODE, END)

    def _create_router(
        self,
        default_target: str,
        valid_targets: set[str],
    ):
        """Create router that handles branching and input requests.

        The router checks:
        1. _need_input - if True, route to END to stop subgraph and signal orchestrator
        2. _branch_target - explicit routing from branch/digression nodes
        3. default_target - sequential flow

        Note: _branch_target is cleared by the target node after consumption.
        """

        def router(state: DialogueState) -> str:
            """Route to next step based on state."""
            # Priority 0: Need input flag - stop subgraph execution
            if state.get("_need_input"):
                return END

            # Priority 1: Explicit branch target (from branch/digression)
            branch_target = state.get("_branch_target")
            if branch_target and branch_target in valid_targets:
                return str(branch_target)

            return default_target

        return router
