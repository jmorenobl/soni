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

    def __init__(self) -> None:
        self._handlers: dict[str, ActionHandler] = {}

    def register(self, name: str, handler: ActionHandler) -> None:
        """Register an action handler."""
        self._handlers[name] = handler

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
        if name not in self._handlers:
            raise ValueError(f"Unknown action: {name}")
        return await self._handlers[name](slots)

    def __contains__(self, name: str) -> bool:
        """Check if action is registered."""
        return name in self._handlers
