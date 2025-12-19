"""CollectNodeFactory - generates collect step nodes."""

from typing import Any

from langchain_core.messages import AIMessage
from langgraph.runtime import Runtime

from soni.compiler.nodes.base import NodeFunction
from soni.compiler.nodes.utils import require_field
from soni.config.steps import CollectStepConfig, StepConfig
from soni.core.constants import SlotWaitType
from soni.core.types import DialogueState, RuntimeContext


class CollectNodeFactory:
    """Factory for collect step nodes."""

    def create(
        self,
        step: StepConfig,
        all_steps: list[StepConfig] | None = None,
        step_index: int | None = None,
    ) -> NodeFunction:
        """Create a node that collects a slot value."""
        if not isinstance(step, CollectStepConfig):
            raise ValueError(f"CollectNodeFactory received wrong step type: {type(step).__name__}")

        slot_name = require_field(step, "slot", str)
        prompt = step.message or f"Please provide {slot_name}"

        async def collect_node(
            state: DialogueState,
            runtime: Runtime[RuntimeContext],
        ) -> dict[str, Any]:
            context = runtime.context
            flow_manager = context.flow_manager

            value = flow_manager.get_slot(state, slot_name)

            if value is not None:
                return {"flow_state": "active"}

            return {
                "flow_state": "waiting_input",
                "waiting_for_slot": slot_name,
                "waiting_for_slot_type": SlotWaitType.COLLECTION,
                "messages": [AIMessage(content=prompt)],
                "last_response": prompt,
            }

        collect_node.__name__ = f"collect_{step.step}"
        return collect_node
