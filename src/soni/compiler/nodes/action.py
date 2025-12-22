"""ActionNodeFactory for M5 (ADR-002 compliant)."""

from typing import Any

from langgraph.runtime import Runtime

from soni.config.models import ActionStepConfig, StepConfig
from soni.core.types import DialogueState, NodeFunction
from soni.flow.manager import merge_delta
from soni.runtime.context import RuntimeContext


class ActionNodeFactory:
    """Factory for action step nodes.

    Creates nodes that execute registered action handlers and map outputs to slots.
    Implements idempotency per ADR-002 using _executed_steps tracking.
    """

    def create(
        self,
        step: StepConfig,
        all_steps: list[StepConfig] | None = None,
        step_index: int | None = None,
    ) -> NodeFunction:
        """Create an action node function."""
        if not isinstance(step, ActionStepConfig):
            raise ValueError(f"ActionNodeFactory received wrong step type: {type(step).__name__}")

        action_name = step.call
        output_mapping = step.map_outputs or {}
        step_id = step.step

        async def action_node(
            state: DialogueState,
            runtime: Runtime[RuntimeContext],
        ) -> dict[str, Any]:
            """Execute the action and map outputs to slots."""
            fm = runtime.context.flow_manager
            action_registry = runtime.context.action_registry
            flow_id = fm.get_active_flow_id(state)

            # IDEMPOTENCY CHECK (ADR-002)
            if flow_id:
                executed = (state.get("_executed_steps") or {}).get(flow_id, set())
                if step_id in executed:
                    return {"_branch_target": None}

            # Get current slots
            slots = fm.get_all_slots(state)

            # Execute action
            result = await action_registry.execute(action_name, slots)

            # Build updates dict
            updates: dict[str, Any] = {"_branch_target": None}

            # Map outputs to slots
            if isinstance(result, dict):
                for action_key, slot_name in output_mapping.items():
                    if action_key in result:
                        delta = fm.set_slot(state, slot_name, result[action_key])
                        merge_delta(updates, delta)

            # MARK AS EXECUTED (ADR-002)
            if flow_id:
                updates["_executed_steps"] = {flow_id: {step_id}}

            return updates

        action_node.__name__ = f"action_{step.step}"
        return action_node
