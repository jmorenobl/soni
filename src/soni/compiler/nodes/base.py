"""Base protocol for node factories."""

from collections.abc import Awaitable, Callable
from typing import Any, Protocol

from langgraph.types import Command

from soni.core.config import StepConfig

# Node function signature: async def node(state: DialogueState, config: RunnableConfig) -> dict[str, Any] | Command
# We use ... to indicate varying arguments if strictly typing Runtime is hard without circular imports
NodeFunction = Callable[..., Awaitable[dict[str, Any] | Command]]


class NodeFactory(Protocol):
    """Protocol for step type node factories."""

    def create(
        self,
        step: StepConfig,
        all_steps: list[StepConfig] | None = None,
        step_index: int | None = None,
    ) -> NodeFunction:
        """Create a node function for the given step config.

        Args:
            step: The step configuration.
            all_steps: All steps in the flow (for context-aware factories).
            step_index: Index of this step in the flow (for context-aware factories).
        """
        ...
