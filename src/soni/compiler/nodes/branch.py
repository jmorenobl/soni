"""BranchNodeFactory - generates conditional branching nodes."""

from typing import Any

from langchain_core.runnables import RunnableConfig

from soni.compiler.nodes.base import NodeFunction
from soni.core.config import StepConfig
from soni.core.types import DialogueState, get_runtime_context


class BranchNodeFactory:
    """Factory for branch step nodes."""

    def create(
        self,
        step: StepConfig,
        all_steps: list[StepConfig] | None = None,
        step_index: int | None = None,
    ) -> NodeFunction:
        """Create a node that branches based on a slot value or expression."""
        if not step.cases:
            raise ValueError(f"Step {step.step} of type 'branch' missing required field 'cases'")

        # Must have either slot OR evaluate, not both
        if not step.slot and not step.evaluate:
            raise ValueError(
                f"Step {step.step} of type 'branch' must specify either 'slot' or 'evaluate'"
            )
        if step.slot and step.evaluate:
            raise ValueError(
                f"Step {step.step} of type 'branch' cannot specify both 'slot' and 'evaluate'"
            )

        slot_name = step.slot
        evaluate_expr = step.evaluate
        cases = step.cases
        step_name = step.step

        async def branch_node(
            state: DialogueState,
            config: RunnableConfig,
        ) -> dict[str, Any]:
            """Evaluate branch condition and set target for router."""
            from soni.core.expression import evaluate_condition

            context = get_runtime_context(config)
            flow_manager = context.flow_manager

            # Determine branch value
            if evaluate_expr:
                # Expression mode: evaluate boolean expression
                slots = flow_manager.get_all_slots(state)
                is_true = evaluate_condition(evaluate_expr, slots)
                str_value = "true" if is_true else "false"
            else:
                # Slot mode: get slot value
                assert slot_name is not None  # Type guard
                value = flow_manager.get_slot(state, slot_name)
                str_value = str(value) if value is not None else ""

            if str_value in cases:
                target = cases[str_value]
                # Store branch target for the router to use
                return {"_branch_target": target}

            # No match - clear any previous target to proceed to next node
            return {"_branch_target": None}

        branch_node.__name__ = f"branch_{step_name}"
        return branch_node
