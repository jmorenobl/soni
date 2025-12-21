"""SayNodeFactory - generates simple response nodes."""

from typing import Any

from langchain_core.messages import AIMessage
from langgraph.runtime import Runtime

from soni.compiler.nodes.base import NodeFunction
from soni.compiler.nodes.utils import require_field
from soni.config.steps import SayStepConfig, StepConfig
from soni.core.types import DialogueState, RuntimeContext


class SayNodeFactory:
    """Factory for say step nodes."""

    def create(
        self,
        step: StepConfig,
        all_steps: list[StepConfig] | None = None,
        step_index: int | None = None,
    ) -> NodeFunction:
        """Create a node that returns a static response."""
        if not isinstance(step, SayStepConfig):
            raise ValueError(f"SayNodeFactory received wrong step type: {type(step).__name__}")

        message_template = require_field(step, "message", str)

        async def say_node(
            state: DialogueState,
            runtime: Runtime[RuntimeContext],
        ) -> dict[str, Any]:
            """Execute the say step."""

            context = runtime.context
            fm = context.flow_manager

            # IDEMPOTENCY CHECK
            step_id = f"step_{step_index}" if step_index is not None else step.step
            flow_id = fm.get_active_flow_id(state)

            if flow_id:
                executed = state.get("_executed_steps", {}).get(flow_id, set())
                if step_id in executed:
                    return {}

            slots = fm.get_all_slots(state)

            # Format message with slots
            try:
                content = message_template.format(**slots)
            except KeyError:
                content = message_template  # Fallback

            # Append to pending responses queue (consumed by RuntimeLoop before interrupt prompt)
            pending = state.get("_pending_responses", [])

            updates = {
                "messages": [AIMessage(content=content)],
                "last_response": content,
                "_pending_responses": pending + [content],  # Queue pattern
            }

            # MARK AS EXECUTED
            if flow_id:
                updates["_executed_steps"] = {flow_id: {step_id}}

            return updates

        say_node.__name__ = f"say_{step.step}"
        return say_node
