"""SayNodeFactory - generates simple response nodes."""

from typing import Any

from langchain_core.messages import AIMessage
from langchain_core.runnables import RunnableConfig

from soni.compiler.nodes.base import NodeFunction
from soni.core.config import StepConfig
from soni.core.types import DialogueState, get_runtime_context


class SayNodeFactory:
    """Factory for say step nodes."""

    def create(self, step: StepConfig) -> NodeFunction:
        """Create a node that returns a static response."""
        if not step.message:
            raise ValueError(f"Step {step.step} of type 'say' missing required field 'message'")

        message = step.message

        async def say_node(
            state: DialogueState,
            config: RunnableConfig,
        ) -> dict[str, Any]:
            context = get_runtime_context(config)
            fm = context.flow_manager
            slots = fm.get_all_slots(state)

            # Format message with slots
            try:
                content = message.format(**slots)
            except KeyError:
                content = message  # Fallback

            return {"messages": [AIMessage(content=content)], "last_response": content}

        say_node.__name__ = f"say_{step.step}"
        return say_node
