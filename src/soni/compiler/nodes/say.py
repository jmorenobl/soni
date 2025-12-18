"""SayNodeFactory - generates simple response nodes."""

from typing import Any

from langchain_core.messages import AIMessage
from langchain_core.runnables import RunnableConfig

from soni.compiler.nodes.base import NodeFunction
from soni.config.steps import SayStepConfig, StepConfig
from soni.core.types import DialogueState, get_runtime_context


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

        message_template = step.message

        async def say_node(
            state: DialogueState,
            config: RunnableConfig,
        ) -> dict[str, Any]:
            """Execute the say step."""

            context = get_runtime_context(config)
            fm = context.flow_manager
            slots = fm.get_all_slots(state)

            # Format message with slots
            try:
                content = message_template.format(**slots)
            except KeyError:
                content = message_template  # Fallback

            return {"messages": [AIMessage(content=content)], "last_response": content}

        say_node.__name__ = f"say_{step.step}"
        return say_node
