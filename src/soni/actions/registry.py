"""Registry for action handlers"""

from collections.abc import Callable


class ActionRegistry:
    """Registry for action handlers."""

    _actions: dict[str, Callable] = {}

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
            cls._actions[name] = func
            return func

        return decorator

    @classmethod
    def get(cls, name: str) -> Callable:
        """
        Get action handler by name.

        Args:
            name: Action name

        Returns:
            Action handler function

        Raises:
            ValueError: If action is not registered
        """
        if name not in cls._actions:
            raise ValueError(
                f"Action '{name}' not registered. Available: {list(cls._actions.keys())}"
            )
        return cls._actions[name]

    @classmethod
    def list_actions(cls) -> list[str]:
        """
        List all registered action names.

        Returns:
            List of action names
        """
        return list(cls._actions.keys())

    @classmethod
    def is_registered(cls, name: str) -> bool:
        """
        Check if an action is registered.

        Args:
            name: Action name

        Returns:
            True if registered, False otherwise
        """
        return name in cls._actions

    @classmethod
    def clear(cls) -> None:
        """
        Clear all registered actions.

        Useful for testing to reset state between tests.
        """
        cls._actions.clear()

    @classmethod
    def unregister(cls, name: str) -> None:
        """
        Unregister a specific action.

        Args:
            name: Action name to unregister
        """
        cls._actions.pop(name, None)
