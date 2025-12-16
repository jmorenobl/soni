"""Action registry for storing action handlers."""

from collections.abc import Awaitable, Callable
from typing import Any

# Define ActionFunc type
ActionFunc = Callable[..., dict[str, Any] | Awaitable[dict[str, Any]]]


class ActionRegistry:
    """Registry for action handlers."""

    # Global registry to support decorator syntax
    _global_actions: dict[str, ActionFunc] = {}

    def __init__(self):
        # Initialize with global actions
        self._actions: dict[str, ActionFunc] = self._global_actions.copy()

    @classmethod
    def register(cls, name: str) -> Callable[[ActionFunc], ActionFunc]:
        """Decorator to register an action globally."""

        def decorator(func: ActionFunc) -> ActionFunc:
            cls._global_actions[name] = func
            return func

        return decorator

    def get(self, name: str) -> ActionFunc | None:
        """Get action by name."""
        return self._actions.get(name) or self._global_actions.get(name)

    def list(self) -> list[str]:
        """List registered actions."""
        return list(set(list(self._actions.keys()) + list(self._global_actions.keys())))

    @classmethod
    def clear(cls) -> None:
        """Clear global actions (for testing)."""
        cls._global_actions.clear()
