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
            return {"response": message}
        
        say_node.__name__ = f"say_{step.step}"
        return say_node
