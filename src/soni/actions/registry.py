"""Action registry for storing action handlers."""

from collections.abc import Awaitable, Callable
from typing import Any

# Define ActionFunc type
ActionFunc = Callable[..., Awaitable[dict[str, Any]]]


class ActionRegistry:
    """Registry for action handlers."""

    def __init__(self):
        self._actions: dict[str, ActionFunc] = {}

    def register(self, name: str) -> Callable[[ActionFunc], ActionFunc]:
        """Decorator to register an action."""

        def decorator(func: ActionFunc) -> ActionFunc:
            self._actions[name] = func
            return func

        return decorator

    def get(self, name: str) -> ActionFunc | None:
        """Get an action by name."""
        return self._actions.get(name)

    def list(self) -> list[str]:
        """List all registered actions."""
        return list(self._actions.keys())
