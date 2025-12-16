"""CollectNodeFactory - generates collect step nodes."""

from typing import Any

from langchain_core.messages import AIMessage
from langchain_core.runnables import RunnableConfig

from soni.compiler.nodes.base import NodeFunction
from soni.core.config import StepConfig
from soni.core.types import DialogueState, get_runtime_context


class CollectNodeFactory:
    """Factory for collect step nodes."""

    def create(self, step: StepConfig) -> NodeFunction:
        """Create a node that collects a slot value."""
        # Validate config
        if not step.slot:
            raise ValueError(f"Step {step.step} of type 'collect' missing required field 'slot'")

        slot_name = step.slot
        prompt = step.message or f"Please provide {slot_name}"

        async def collect_node(
            state: DialogueState,
            config: RunnableConfig,
        ) -> dict[str, Any]:
            context = get_runtime_context(config)
            flow_manager = context.flow_manager

            value = flow_manager.get_slot(state, slot_name)

            if value is not None:
                return {"flow_state": "active"}

            return {
                "flow_state": "waiting_input",
                "waiting_for_slot": slot_name,
                "messages": [AIMessage(content=prompt)],
                "last_response": prompt,
            }

        collect_node.__name__ = f"collect_{step.step}"
        return collect_node
