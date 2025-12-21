from typing import Any

from langgraph.runtime import Runtime

from soni.config.models import SayStepConfig, StepConfig
from soni.core.types import DialogueState, NodeFunction
from soni.runtime.context import RuntimeContext


class SayNodeFactory:
    """Factory for say step nodes (SRP: single responsibility)."""

    def create(
        self,
        step: StepConfig,
        all_steps: list[StepConfig] | None = None,
        step_index: int | None = None,
    ) -> NodeFunction:
        """Create a node that returns a static response."""
        if not isinstance(step, SayStepConfig):
            raise ValueError(f"SayNodeFactory received wrong step type: {type(step).__name__}")

        message = step.message

        async def say_node(
            state: DialogueState,
            runtime: Runtime[RuntimeContext],
        ) -> dict[str, Any]:
            """Return the message as response."""
            # Interpolate slots
            import re

            fm = runtime.context.flow_manager

            def replace_slot(match: re.Match) -> str:
                slot_name = match.group(1)
                value = fm.get_slot(state, slot_name)
                return str(value) if value is not None else match.group(0)

            interpolated_message = re.sub(r"\{(\w+)\}", replace_slot, message)

            return {"response": interpolated_message}

        say_node.__name__ = f"say_{step.step}"
        return say_node
