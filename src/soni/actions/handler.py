"""Action handler for executing registered actions."""

import inspect
from typing import Any

from soni.actions.registry import ActionRegistry
from soni.core.errors import ActionError


class ActionHandler:
    """Handles action execution."""

    def __init__(self, registry: ActionRegistry):
        self.registry = registry

    async def execute(self, action_name: str, inputs: dict[str, Any]) -> dict[str, Any]:
        """Execute a registered action with validation.

        Args:
            action_name: Name of action to execute.
            inputs: Dictionary of arguments for the action.

        Returns:
            Result dictionary from action.

        Raises:
            ActionError: If action not found or inputs invalid.
        """
        action = self.registry.get(action_name)
        if not action:
            raise ActionError(f"Action '{action_name}' not found")

        # Validate arguments using inspection
        sig = inspect.signature(action)
        required = [
            p.name
            for p in sig.parameters.values()
            if p.default == inspect.Parameter.empty
            and p.kind in (inspect.Parameter.POSITIONAL_OR_KEYWORD, inspect.Parameter.KEYWORD_ONLY)
        ]

        # Check for missing required inputs
        missing = [param for param in required if param not in inputs]
        if missing:
            raise ActionError(f"Action '{action_name}' missing inputs: {missing}")

        # Execute
        try:
            # We filter inputs or pass kwargs?
            # If action accepts specific args, passing extra kwargs might fail unless **kwargs allowed.
            # But python call matching handles keyword args.
            # If inputs has extra keys not in signature, call will fail unless **kwargs.
            # To be safe, we might bind? Or let Python raise TypeError which we catch?
            # We catch Exception, so TypeError will be caught.
            return await action(**inputs)
        except Exception as e:
            # Wrap error
            raise ActionError(f"Action execution failed: {e}") from e
