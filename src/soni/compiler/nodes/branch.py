"""BranchNodeFactory for M3 - conditional routing."""

from typing import Any

from langgraph.runtime import Runtime

from soni.config.models import BranchStepConfig, StepConfig
from soni.core.expression import evaluate_expression, matches
from soni.core.types import DialogueState, NodeFunction
from soni.runtime.context import RuntimeContext


class BranchNodeFactory:
    """Factory for branch step nodes (SRP: routing only)."""

    def create(
        self,
        step: StepConfig,
        all_steps: list[StepConfig] | None = None,
        step_index: int | None = None,
    ) -> NodeFunction:
        """Create a branch node function.

        Args:
            step: BranchStepConfig with slot or evaluate, and cases dict.
            all_steps: All steps in the flow (unused).
            step_index: Index of this step (unused).

        Returns:
            Async node function that sets _branch_target.

        Raises:
            ValueError: If neither slot nor evaluate is specified.
        """
        if not isinstance(step, BranchStepConfig):
            raise ValueError(f"BranchNodeFactory received wrong step type: {type(step).__name__}")

        slot_name = step.slot
        expression = step.evaluate
        cases = step.cases

        if not slot_name and not expression:
            raise ValueError(f"Branch step '{step.step}' must specify 'slot' or 'evaluate'")

        async def branch_node(
            state: DialogueState,
            runtime: Runtime[RuntimeContext],
        ) -> dict[str, Any]:
            """Route based on slot value or expression."""
            fm = runtime.context.flow_manager
            current_slots = fm.get_all_slots(state)

            # Determine value to match
            if expression:
                # Expression mode: evaluate to boolean
                is_true = evaluate_expression(expression, current_slots)
                value: Any = is_true
            else:
                # Slot mode: get slot value (slot_name is guaranteed by validation above)
                assert slot_name is not None
                value = fm.get_slot(state, slot_name)

            # Find matching case
            target = cases.get("default")

            for case_pattern, case_target in cases.items():
                if case_pattern == "default":
                    continue

                if matches(value, case_pattern):
                    target = case_target
                    break

            # Clear any previous branch target if no match
            return {"_branch_target": target, "_pending_task": None}

        branch_node.__name__ = f"branch_{step.step}"
        return branch_node
