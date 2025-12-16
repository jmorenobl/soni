"""ActionNodeFactory - generates action execution nodes."""

from typing import Any

from langchain_core.runnables import RunnableConfig

from soni.compiler.nodes.base import NodeFunction
from soni.core.config import StepConfig
from soni.core.types import DialogueState, get_runtime_context


class ActionNodeFactory:
    """Factory for action step nodes."""

    def create(self, step: StepConfig) -> NodeFunction:
        """Create a node that executes an action."""
        if not step.call:
            raise ValueError(f"Step {step.step} of type 'action' missing required field 'call'")

        action_name = step.call

        async def action_node(
            state: DialogueState,
            config: RunnableConfig,
        ) -> dict[str, Any]:
            context = get_runtime_context(config)
            handler = context.action_handler
            fm = context.flow_manager

            slots = fm.get_all_slots(state)

            # 2. Execute
            # Pass all slots? Or filtered? Handler validates.
            result = await handler.execute(action_name, slots)

            # 3. Update state with results
            if isinstance(result, dict):
                for key, value in result.items():
                    await fm.set_slot(state, key, value)

            return {"flow_slots": state["flow_slots"]}

        action_node.__name__ = f"action_{step.step}"
        return action_node
