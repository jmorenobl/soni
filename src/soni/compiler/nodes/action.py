"""ActionNodeFactory - generates action execution nodes."""

from typing import Any

from langgraph.runtime import Runtime

from soni.compiler.nodes.base import NodeFunction
from soni.compiler.nodes.utils import require_field
from soni.config.steps import ActionStepConfig, StepConfig
from soni.core.types import DialogueState, RuntimeContext
from soni.flow.manager import merge_delta


class ActionNodeFactory:
    """Factory for action step nodes."""

    def create(
        self,
        step: StepConfig,
        all_steps: list[StepConfig] | None = None,
        step_index: int | None = None,
    ) -> NodeFunction:
        """Create a node that executes an action."""
        if not isinstance(step, ActionStepConfig):
            raise ValueError(f"ActionNodeFactory received wrong step type: {type(step).__name__}")

        action_name = require_field(step, "call", str)
        output_mapping = step.map_outputs or {}

        async def action_node(
            state: DialogueState,
            runtime: Runtime[RuntimeContext],
        ) -> dict[str, Any]:
            """Execute the action."""
            context = runtime.context
            action_handler = context.action_handler
            flow_manager = context.flow_manager

            # IDEMPOTENCY CHECK
            step_id = f"step_{step_index}" if step_index is not None else step.step
            flow_id = flow_manager.get_active_flow_id(state)

            if flow_id:
                executed = state.get("_executed_steps", {}).get(flow_id, set())
                if step_id in executed:
                    return {}

            slots = flow_manager.get_all_slots(state)

            # Execute action
            result = await action_handler.execute(action_name, slots)

            # Build updates dict
            updates: dict[str, Any] = {}

            # Update state with results, applying output mapping
            if isinstance(result, dict):
                for key, value in result.items():
                    # Apply mapping if defined, otherwise use original key
                    slot_name = output_mapping.get(key, key)
                    delta = flow_manager.set_slot(state, slot_name, value)
                    merge_delta(updates, delta)
                    # Apply to state for subsequent iterations
                    if delta and delta.flow_slots is not None:
                        state["flow_slots"] = delta.flow_slots

            # MARK AS EXECUTED
            if flow_id:
                updates["_executed_steps"] = {flow_id: {step_id}}

            # NOTE: Don't add flow_slots fallback - the reducer will merge properly
            # Adding state.get("flow_slots") here would OVERWRITE slots set by
            # previous nodes in the same step (like collect_node)

            return updates

        action_node.__name__ = f"action_{step.step}"
        return action_node
