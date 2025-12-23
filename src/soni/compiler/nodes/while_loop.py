"""WhileNodeFactory for M3 - loop guard nodes.

While loops are guard nodes that:
1. Evaluate a condition using slot values
2. If TRUE: route to first step in `do` block
3. If FALSE: route to exit target

The SubgraphBuilder handles the loop-back edge from last `do` step to guard.
"""

from typing import Any

from langgraph.runtime import Runtime

from soni.config.models import StepConfig, WhileStepConfig
from soni.core.expression import evaluate_expression
from soni.core.types import DialogueState, NodeFunction
from soni.runtime.context import RuntimeContext


class WhileNodeFactory:
    """Factory for while loop guard nodes (SRP: loop condition evaluation only)."""

    def create(
        self,
        step: StepConfig,
        all_steps: list[StepConfig] | None = None,
        step_index: int | None = None,
    ) -> NodeFunction:
        """Create a while loop guard node.

        Args:
            step: WhileStepConfig with condition, do list, and optional exit_to.
            all_steps: All steps in the flow (for exit_to calculation).
            step_index: Index of this step in the flow.

        Returns:
            Async node function that evaluates condition and sets _branch_target.
        """
        if not isinstance(step, WhileStepConfig):
            raise ValueError(f"WhileNodeFactory received wrong step type: {type(step).__name__}")

        condition = step.condition
        do_step_names = step.get_do_step_names()
        loop_body_start = do_step_names[0]  # First step in do block

        # Calculate exit target if not specified
        exit_to = step.exit_to
        if not exit_to and all_steps and step_index is not None:
            do_step_names_set = set(do_step_names)
            # Find first step after while that's NOT in the do block
            for i in range(step_index + 1, len(all_steps)):
                candidate = all_steps[i]
                if candidate.step not in do_step_names_set:
                    exit_to = candidate.step
                    break

        async def while_node(
            state: DialogueState,
            runtime: Runtime[RuntimeContext],
        ) -> dict[str, Any]:
            """Evaluate condition and route to loop body or exit."""
            fm = runtime.context.flow_manager
            slots = fm.get_all_slots(state)

            # Evaluate loop condition
            is_true = evaluate_expression(condition, slots)

            if is_true:
                # Continue looping - route to first step in do block
                return {"_branch_target": loop_body_start, "_pending_task": None}

            # Exit loop - route to exit target or signal END
            if exit_to:
                return {"_branch_target": exit_to, "_pending_task": None}

            # No exit_to means flow ends after loop
            return {"_branch_target": None, "_pending_task": None}

        while_node.__name__ = f"while_{step.step}"
        return while_node
