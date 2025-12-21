"""BranchNodeFactory - generates conditional branching nodes."""

from typing import Any

from langgraph.runtime import Runtime
from soni.compiler.nodes.base import NodeFunction
from soni.compiler.nodes.utils import require_field
from soni.core.errors import ValidationError
from soni.core.types import DialogueState, RuntimeContext

from soni.config.steps import BranchStepConfig, StepConfig


class BranchNodeFactory:
    """Factory for branch step nodes."""

    def create(
        self,
        step: StepConfig,
        all_steps: list[StepConfig] | None = None,
        step_index: int | None = None,
    ) -> NodeFunction:
        """Create a node that branches based on a slot value or expression."""
        if not isinstance(step, BranchStepConfig):
            raise ValueError(f"BranchNodeFactory received wrong step type: {type(step).__name__}")

        # Pydantic validates cases is present
        require_field(step, "cases")

        # Manually validate slot vs evaluate XOR logic
        if not step.slot and not step.evaluate:
            raise ValidationError(
                f"Step {step.step} of type 'branch' must specify either 'slot' or 'evaluate'"
            )
        if step.slot and step.evaluate:
            raise ValidationError(
                f"Step {step.step} of type 'branch' cannot specify both 'slot' and 'evaluate'"
            )

        slot_name = step.slot
        evaluate_expr = step.evaluate
        cases = step.cases
        step_name = step.step

        # Note: next_step calculation removed - we now use _branch_target for all routing

        async def branch_node(
            state: DialogueState,
            runtime: Runtime[RuntimeContext],
        ) -> dict[str, Any]:
            """Evaluate branch condition and set _branch_target for router."""
            from soni.core.expression import evaluate_condition

            context = runtime.context
            flow_manager = context.flow_manager

            # Determine branch value
            if evaluate_expr:
                # Expression mode: evaluate boolean expression
                slots = flow_manager.get_all_slots(state)
                is_true = evaluate_condition(evaluate_expr, slots)
                str_value = "true" if is_true else "false"
            else:
                # Slot mode: get slot value
                assert slot_name is not None  # Type guard based on XOR check above
                value = flow_manager.get_slot(state, slot_name)
                str_value = str(value) if value is not None else ""

            if str_value in cases:
                target = cases[str_value]
                # Use _branch_target for conditional_edges (Command doesn't work)
                return {"_branch_target": target}

            # No match - proceed to next step normally (let router handle)
            # Return empty dict to signal no state change, router will route to default
            return {}

        branch_node.__name__ = f"branch_{step_name}"
        return branch_node
