"""Thread-safe registry for action handlers"""

import logging
from collections.abc import Callable
from threading import Lock

logger = logging.getLogger(__name__)

# Estado global con lock para thread-safety
_actions: dict[str, Callable] = {}
_actions_lock = Lock()


class ActionRegistry:
    """
    Thread-safe registry for action handlers.

    All mutations are protected by a lock to ensure thread-safety
    in concurrent environments.
    """

    @classmethod
    def register(cls, name: str) -> Callable:
        """
        Register an action handler.

        Usage:
            @ActionRegistry.register("search_flights")
            async def search_available_flights(
                origin: str,
                destination: str,
            ) -> dict[str, Any]:
                return {"flights": [...]}

        Args:
            name: Semantic name for the action

        Returns:
            Decorator function
        """

        def decorator(func: Callable) -> Callable:
            with _actions_lock:  # Thread-safe mutation
                if name in _actions:
                    logger.warning(
                        f"Action '{name}' already registered, overwriting",
                        extra={"action_name": name},
                    )
                _actions[name] = func
                logger.debug(
                    f"Registered action '{name}'",
                    extra={"action_name": name},
                )
            return func

        return decorator

    @classmethod
    def get(cls, name: str) -> Callable:
        """
        Get action handler by name (thread-safe read).

        Args:
            name: Action name

        Returns:
            Action handler function

        Raises:
            ValueError: If action is not registered
        """
        with _actions_lock:  # Thread-safe read
            if name not in _actions:
                raise ValueError(
                    f"Action '{name}' not registered. Available: {list(_actions.keys())}"
                )
            return _actions[name]

    @classmethod
    def list_actions(cls) -> list[str]:
        """
        List all registered action names (thread-safe).

        Returns:
            List of action names
        """
        with _actions_lock:  # Thread-safe read
            return list(_actions.keys())

    @classmethod
    def is_registered(cls, name: str) -> bool:
        """
        Check if an action is registered (thread-safe).

        Args:
            name: Action name

        Returns:
            True if registered, False otherwise
        """
        with _actions_lock:  # Thread-safe read
            return name in _actions

    @classmethod
    def clear(cls) -> None:
        """
        Clear all registered actions (thread-safe).

        Warning: This is primarily for testing. Use with caution.
        """
        with _actions_lock:  # Thread-safe mutation
            count = len(_actions)
            _actions.clear()
            logger.debug(
                f"Cleared {count} registered action(s)",
                extra={"count": count},
            )

    @classmethod
    def unregister(cls, name: str) -> None:
        """
        Unregister a specific action (thread-safe).

        Args:
            name: Action name to unregister
        """
        with _actions_lock:  # Thread-safe mutation
            if name in _actions:
                _actions.pop(name, None)
                logger.debug(
                    f"Unregistered action '{name}'",
                    extra={"action_name": name},
                )
