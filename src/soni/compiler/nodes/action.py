"""ActionNodeFactory - generates action execution nodes."""

from typing import Any

from langchain_core.runnables import RunnableConfig

from soni.compiler.nodes.base import NodeFunction
from soni.compiler.nodes.utils import require_field
from soni.config.steps import ActionStepConfig, StepConfig
from soni.core.types import DialogueState, get_runtime_context
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
            config: RunnableConfig,
        ) -> dict[str, Any]:
            """Execute the action."""
            context = get_runtime_context(config)
            action_handler = context.action_handler
            flow_manager = context.flow_manager

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

            # Ensure flow_slots in updates
            if "flow_slots" not in updates:
                updates["flow_slots"] = state.get("flow_slots")

            return updates

        action_node.__name__ = f"action_{step.step}"
        return action_node
