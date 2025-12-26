"""SetNodeFactory for M3 - declarative slot assignment."""

from typing import Any

from langgraph.runtime import Runtime

from soni.config.models import SetStepConfig, StepConfig
from soni.core.expression import evaluate_expression, evaluate_value
from soni.core.types import DialogueState, NodeFunction
from soni.flow.manager import apply_delta_to_dict
from soni.runtime.context import RuntimeContext


class SetNodeFactory:
    """Factory for set step nodes (SRP: slot assignment only)."""

    def create(
        self,
        step: StepConfig,
        all_steps: list[StepConfig] | None = None,
        step_index: int | None = None,
    ) -> NodeFunction:
        """Create a set node function.

        Args:
            step: SetStepConfig with slots dict and optional condition.
            all_steps: All steps in the flow (for step_id generation).
            step_index: Index of this step in the flow.

        Returns:
            Async node function that sets slot values.
        """
        if not isinstance(step, SetStepConfig):
            raise ValueError(f"SetNodeFactory received wrong step type: {type(step).__name__}")

        slots_config = step.slots
        condition = step.condition
        step_id = step.step

        async def set_node(
            state: DialogueState,
            runtime: Runtime[RuntimeContext],
        ) -> dict[str, Any]:
            """Set slot values programmatically."""
            fm = runtime.context.flow_manager
            flow_id = fm.get_active_flow_id(state)

            # Idempotency check
            if flow_id:
                executed = (state.get("_executed_steps") or {}).get(flow_id, set())
                if step_id in executed:
                    return {"_branch_target": None, "_pending_task": None}

            # Conditional execution
            if condition:
                current_slots = fm.get_all_slots(state)
                if not evaluate_expression(condition, current_slots):
                    # Mark as executed even if condition is false, clear branch target
                    result: dict[str, Any] = {"_branch_target": None, "_pending_task": None}
                    if flow_id:
                        result["_executed_steps"] = {flow_id: {step_id}}
                    return result

            # Set each slot
            updates: dict[str, Any] = {}
            current_slots = fm.get_all_slots(state)

            for slot_name, value_expr in slots_config.items():
                value = evaluate_value(value_expr, current_slots)
                delta = fm.set_slot(state, slot_name, value)
                apply_delta_to_dict(updates, delta)

                # Update current_slots for subsequent iterations
                current_slots[slot_name] = value

            # Mark as executed and clear branch target
            updates["_branch_target"] = None
            updates["_pending_task"] = None
            if flow_id:
                updates["_executed_steps"] = {flow_id: {step_id}}

            return updates

        set_node.__name__ = f"set_{step.step}"
        return set_node
