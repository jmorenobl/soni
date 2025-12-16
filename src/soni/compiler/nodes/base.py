"""Base protocol for node factories."""

from collections.abc import Awaitable, Callable
from typing import Any, Protocol

# Node function signature: async def node(state: DialogueState, config: RunnableConfig) -> dict[str, Any]
# We use ... to indicate varying arguments if strictly typing Runtime is hard without circular imports
NodeFunction = Callable[..., Awaitable[dict[str, Any]]]


class NodeFactory(Protocol):
    """Protocol for step type node factories."""

    def create(self, step: StepConfig) -> NodeFunction:
        """Create a node function for the given step config."""
        ...
