"""ActionNodeFactory - generates action execution nodes."""
from typing import Any

from langgraph.runtime import Runtime

from soni.compiler.nodes.base import NodeFunction
from soni.core.config import StepConfig
from soni.core.types import DialogueState, RuntimeContext


class ActionNodeFactory:
    """Factory for action step nodes."""

    def create(self, step: StepConfig) -> NodeFunction:
        """Create a node that executes an action."""
        if not step.call:
             raise ValueError(f"Step {step.step} of type 'action' missing required field 'call'")

        action_name = step.call

        async def action_node(
            state: DialogueState,
            runtime: Runtime[RuntimeContext],
        ) -> dict[str, Any]:

            action_handler = runtime.context.action_handler
            # Note: We might need to pass arguments from slots here
            result = await action_handler.execute(action_name, state)

            return result or {"flow_state": "active"}

        action_node.__name__ = f"action_{step.step}"
        return action_node
