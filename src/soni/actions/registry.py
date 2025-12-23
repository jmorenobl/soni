"""Action registry for custom handlers (M5)."""

from collections.abc import Awaitable, Callable
from typing import Any

# Type alias for action handlers
ActionHandler = Callable[[dict[str, Any]], Awaitable[dict[str, Any]]]


class ActionRegistry:
    """Registry for action handlers.

    Allows registration of async functions that receive slots and return results.
    Results are mapped to slots via `map_outputs` in ActionStepConfig.

    Usage:
        registry = ActionRegistry()

        async def get_balance(slots):
            return {"balance": 1234.56}

        registry.register("get_balance", get_balance)
        result = await registry.execute("get_balance", {"user_id": "123"})
    """

    _default_instance: "ActionRegistry | None" = None

    def __init__(self) -> None:
        self._handlers: dict[str, ActionHandler] = {}

    @classmethod
    def get_default(cls) -> "ActionRegistry":
        """Get the default global registry instance."""
        if cls._default_instance is None:
            cls._default_instance = cls()
        return cls._default_instance

    def register_handler(self, name: str, handler: ActionHandler) -> None:
        """Register an action handler (instance method)."""
        self._handlers[name] = handler

    @classmethod
    def register(cls, name: str) -> Callable[[ActionHandler], ActionHandler]:
        """Decorator to register an action handler.

        Supports both:
        @registry.register("name")  (if called on instance via bound method)
        @ActionRegistry.register("name") (if called on class, uses default instance)
        """

        def decorator(handler: ActionHandler) -> ActionHandler:
            # Check if we are in instance context or class context
            # Actually, confusing.
            # If called as ActionRegistry.register("name"), cls is ActionRegistry.
            # If called as registry.register("name"), cls is still ActionRegistry if it was defined as @classmethod!
            # BUT if defined as @classmethod, 'self' is the class.

            # Use default instance
            cls.get_default().register_handler(name, handler)
            return handler

        return decorator

    async def execute(self, name: str, slots: dict[str, Any]) -> dict[str, Any]:
        """Execute action with current slots.

        Args:
            name: Registered action name
            slots: Current slot values from flow

        Returns:
            Dict of results to be mapped to slots

        Raises:
            ValueError: If action is not registered
        """
        import asyncio
        import inspect

        if name not in self._handlers:
            raise ValueError(f"Unknown action: {name}")

        handler = self._handlers[name]
        is_async = asyncio.iscoroutinefunction(handler)

        # Smart execution: handle legacy vs modern signatures
        try:
            sig = inspect.signature(handler)
        except ValueError:
            # Cannot inspect (e.g. built-in), try passing slots directly
            result = handler(slots)
            return await result if is_async else result

        params = sig.parameters

        # Determine arguments based on signature
        if not params:
            # Case 1: No arguments (e.g. get_greeting)
            result = handler()
        else:
            first_param_name = next(iter(params))
            first_param = params[first_param_name]
            if len(params) == 1 and (first_param_name == "slots" or first_param.annotation is dict):
                # Case 2: Explicit 'slots' dict argument (Modern)
                result = handler(slots)
            else:
                # Case 3: Match slots to arguments (Legacy / Direct Unpacking)
                kwargs = {k: v for k, v in slots.items() if k in params}
                result = handler(**kwargs)

        # Await if async, return directly if sync
        return await result if is_async else result

    def __contains__(self, name: str) -> bool:
        """Check if action is registered."""
        return name in self._handlers
