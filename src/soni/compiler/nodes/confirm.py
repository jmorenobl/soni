"""ConfirmNodeFactory - generates confirmation nodes."""

from typing import Any

from langchain_core.messages import AIMessage
from langchain_core.runnables import RunnableConfig

from soni.compiler.nodes.base import NodeFunction
from soni.core.config import StepConfig
from soni.core.types import DialogueState


class ConfirmNodeFactory:
    """Factory for confirm step nodes."""

    def create(self, step: StepConfig) -> NodeFunction:
        """Create a node that requests confirmation."""
        if not step.slot:
            raise ValueError(f"Step {step.step} of type 'confirm' missing required field 'slot'")

        slot_name = step.slot
        prompt = step.message or f"Please confirm {slot_name} (yes/no)"

        async def confirm_node(
            state: DialogueState,
            config: RunnableConfig,
        ) -> dict[str, Any]:
            context = config["configurable"]["runtime_context"]
            flow_manager = context.flow_manager
            # Check if confirmation slot is filled
            value = flow_manager.get_slot(state, slot_name)

            if value is not None:
                return {"flow_state": "active"}

            return {
                "flow_state": "waiting_input",
                "waiting_for_slot": slot_name,
                "messages": [AIMessage(content=prompt)],
                "last_response": prompt,
            }

        confirm_node.__name__ = f"confirm_{step.step}"
        return confirm_node
