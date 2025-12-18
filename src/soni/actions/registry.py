"""Action registry for storing action handlers.

Supports both global registration (via decorator) and scoped registration
(via instance methods) for flexibility in different contexts.
"""

from collections.abc import Awaitable, Callable
from typing import Any

# Define ActionFunc type
ActionFunc = Callable[..., dict[str, Any] | Awaitable[dict[str, Any]]]


class ActionRegistry:
    """Registry for action handlers.

    Design:
    - Global actions (via @ActionRegistry.register decorator): Available to all instances
    - Local actions (via instance.register_local): Scoped to specific instance

    Usage:
        # Global registration (at module level, available everywhere)
        @ActionRegistry.register("book_flight")
        async def book_flight_action(origin: str, destination: str) -> dict[str, Any]:
            ...

        # Scoped registration (for testing or config-specific actions)
        registry = ActionRegistry()
        registry.register_local("test_action", my_test_func)
    """

    # Global registry to support decorator syntax
    _global_actions: dict[str, ActionFunc] = {}

    def __init__(self) -> None:
        """Initialize registry with copy of global actions."""
        # Each instance gets its own copy for local registrations
        self._actions: dict[str, ActionFunc] = {}

    def register_local(self, name: str, func: ActionFunc) -> None:
        """Register an action local to this instance only.

        Use for testing or config-specific actions that shouldn't pollute global state.
        """
        self._actions[name] = func

    def get(self, name: str) -> ActionFunc | None:
        """Get action by name (local takes precedence over global)."""
        return self._actions.get(name) or self._global_actions.get(name)

    def list(self) -> list[str]:
        """List all registered actions (local + global)."""
        all_names = set(self._actions.keys()) | set(self._global_actions.keys())
        return sorted(all_names)

    def has(self, name: str) -> bool:
        """Check if action is registered."""
        return name in self._actions or name in self._global_actions

    @classmethod
    def register(cls, name: str) -> Callable[[ActionFunc], ActionFunc]:
        """Decorator to register an action globally.

        Global actions are available to all ActionRegistry instances.
        Use this for production action handlers.
        """

        def decorator(func: ActionFunc) -> ActionFunc:
            cls._global_actions[name] = func
            return func

        return decorator

    @classmethod
    def clear_global(cls) -> None:
        """Clear global actions (for testing)."""
        cls._global_actions.clear()

    def clear_local(self) -> None:
        """Clear local actions only."""
        self._actions.clear()

    # Backwards compatibility alias
    clear = clear_global
