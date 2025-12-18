"""Action registry for storing action handlers.

Supports both global registration (via decorator) and scoped registration
(via instance methods) for flexibility in different contexts.

Thread-safe for concurrent registration in multi-worker environments.
"""

import logging
import threading
from collections.abc import Awaitable, Callable
from typing import Any

logger = logging.getLogger(__name__)

# Define ActionFunc type
ActionFunc = Callable[..., dict[str, Any] | Awaitable[dict[str, Any]]]


class ActionRegistry:
    """Thread-safe registry for action handlers.

    Supports both global (class-level) and local (instance-level) registration.
    Global registration is thread-safe using a lock.

    Design:
    - Global actions (via @ActionRegistry.register decorator): Available to all instances
    - Local actions (via instance.register_local): Scoped to specific instance
    - Thread-safe operations for concurrent registration

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
    _global_lock: threading.Lock = threading.Lock()

    def __init__(self) -> None:
        """Initialize registry with empty local actions.

        Instance-level actions take precedence over global actions.
        """
        # Each instance gets its own copy for local registrations
        self._actions: dict[str, ActionFunc] = {}
        self._local_lock: threading.Lock = threading.Lock()

    def register_local(self, name: str, func: ActionFunc) -> None:
        """Register an action local to this instance only (thread-safe).

        Use for testing or config-specific actions that shouldn't pollute global state.
        Local actions take precedence over global actions.

        Args:
            name: Unique name for the action
            func: Action function to register
        """
        with self._local_lock:
            if name in self._actions:
                logger.warning(
                    f"Overwriting existing local action '{name}'. "
                    f"Previous: {self._actions[name].__name__}, "
                    f"New: {func.__name__}"
                )
            self._actions[name] = func
            logger.debug(f"Registered local action: {name}")

    def get(self, name: str) -> ActionFunc | None:
        """Get action by name (thread-safe).

        Checks local actions first, then global actions.

        Args:
            name: Action name to look up

        Returns:
            Action function if found, None otherwise
        """
        # Local actions don't need global lock (instance-specific)
        with self._local_lock:
            if name in self._actions:
                return self._actions[name]

        # Global actions need lock for read safety
        with self._global_lock:
            return self._global_actions.get(name)

    def list_actions(self) -> dict[str, list[str]]:
        """List all available actions (thread-safe).

        Returns:
            Dictionary with 'global' and 'local' keys containing action names
        """
        with self._local_lock:
            local_names = list(self._actions.keys())

        with self._global_lock:
            global_names = list(self._global_actions.keys())

        return {
            "global": global_names,
            "local": local_names,
        }

    def list(self) -> list[str]:
        """List all registered actions (local + global).

        Backwards compatibility method.
        """
        actions = self.list_actions()
        all_names = set(actions["global"]) | set(actions["local"])
        return sorted(all_names)

    def has(self, name: str) -> bool:
        """Check if action is registered (thread-safe)."""
        with self._local_lock:
            if name in self._actions:
                return True

        with self._global_lock:
            return name in self._global_actions

    @classmethod
    def register(cls, name: str) -> Callable[[ActionFunc], ActionFunc]:
        """Decorator to register an action globally (thread-safe).

        Global actions are available to all ActionRegistry instances.
        Use this for production action handlers.

        Args:
            name: Unique name for the action

        Returns:
            Decorator function
        """

        def decorator(func: ActionFunc) -> ActionFunc:
            with cls._global_lock:
                if name in cls._global_actions:
                    logger.warning(
                        f"Overwriting existing global action '{name}'. "
                        f"Previous: {cls._global_actions[name].__name__}, "
                        f"New: {func.__name__}"
                    )
                cls._global_actions[name] = func
                logger.debug(f"Registered global action: {name}")
            return func

        return decorator

    @classmethod
    def clear_global(cls) -> None:
        """Clear all global actions (thread-safe).

        Warning: This affects all instances. Use with caution.
        """
        with cls._global_lock:
            count = len(cls._global_actions)
            cls._global_actions.clear()
            logger.info(f"Cleared {count} global actions")

    def clear_local(self) -> None:
        """Clear instance-local actions (thread-safe)."""
        with self._local_lock:
            count = len(self._actions)
            self._actions.clear()
            logger.debug(f"Cleared {count} local actions")

    # Backwards compatibility alias
    clear = clear_global
