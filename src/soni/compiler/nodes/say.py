"""SayNodeFactory - generates simple response nodes."""
from typing import Any

from langgraph.runtime import Runtime

from soni.compiler.nodes.base import NodeFunction
from soni.core.config import StepConfig
from soni.core.types import DialogueState, RuntimeContext


class SayNodeFactory:
    """Factory for say step nodes."""

    def create(self, step: StepConfig) -> NodeFunction:
        """Create a node that returns a static response."""
        if not step.message:
            raise ValueError(f"Step {step.step} of type 'say' missing required field 'message'")

        message = step.message

        async def say_node(
            state: DialogueState,
            runtime: Runtime[RuntimeContext],
        ) -> dict[str, Any]:
            return {"response": message}

        say_node.__name__ = f"say_{step.step}"
        return say_node
