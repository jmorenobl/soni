"""Action handlers for Soni Framework"""

import importlib
import inspect
import logging
from collections.abc import Callable
from typing import Any

from soni.actions.registry import ActionRegistry
from soni.core.config import SoniConfig
from soni.core.errors import ActionNotFoundError

logger = logging.getLogger(__name__)


class ActionHandler:
    """
    Handles execution of external action handlers.

    This class loads and executes Python functions/classes
    that implement business logic for actions.
    """

    def __init__(self, config: SoniConfig):
        """
        Initialize the action handler.

        Args:
            config: Soni configuration containing action definitions
        """
        self.config = config
        self._handler_cache: dict[str, Callable] = {}

    async def execute(self, action_name: str, slots: dict[str, Any]) -> dict[str, Any]:
        """
        Execute an action handler.

        Args:
            action_name: Name of the action to execute
            slots: Dictionary of slot values to pass as inputs

        Returns:
            Dictionary with action outputs

        Raises:
            ActionNotFoundError: If action is not found in config
            ActionNotFoundError: If handler cannot be loaded
            RuntimeError: If handler execution fails
        """
        # Get action config
        if action_name not in self.config.actions:
            raise ActionNotFoundError(
                action_name=action_name,
                context={"available_actions": list(self.config.actions.keys())},
            )

        action_config = self.config.actions[action_name]

        # Get handler from ActionRegistry (zero-leakage architecture)
        # Actions must be registered using @ActionRegistry.register()
        try:
            handler = ActionRegistry.get(action_name)
            logger.debug(f"Using registered action handler: {action_name}")
        except ValueError as e:
            # No fallback - require ActionRegistry
            available = ActionRegistry.list_actions()
            raise ActionNotFoundError(
                action_name=action_name,
                context={
                    "error": (
                        f"Action '{action_name}' not found in registry. "
                        f"Available actions: {', '.join(sorted(available))}. "
                        f"Register actions using @ActionRegistry.register('{action_name}')"
                    ),
                },
            ) from e

        # Prepare inputs from slots
        inputs = {}
        for input_slot in action_config.inputs:
            if input_slot not in slots:
                raise ValueError(
                    f"Required input slot '{input_slot}' not provided for action '{action_name}'"
                )
            inputs[input_slot] = slots[input_slot]

        # Execute handler
        try:
            if inspect.iscoroutinefunction(handler):
                # Async handler
                result = await handler(**inputs)
            else:
                # Sync handler - run in executor
                import asyncio

                def run_sync() -> Any:
                    return handler(**inputs)

                loop = asyncio.get_event_loop()
                result = await loop.run_in_executor(None, run_sync)
        except (ValueError, TypeError, KeyError, AttributeError) as e:
            # Errores esperados de ejecución de acción
            logger.error(
                f"Error executing action '{action_name}': {e}",
                exc_info=True,
                extra={
                    "action_name": action_name,
                    "error_type": type(e).__name__,
                },
            )
            raise RuntimeError(
                f"Action '{action_name}' execution failed: {e}",
            ) from e
        except Exception as e:
            # Errores inesperados
            logger.error(
                f"Unexpected error executing action '{action_name}': {e}",
                exc_info=True,
                extra={
                    "action_name": action_name,
                    "error_type": type(e).__name__,
                },
            )
            raise RuntimeError(
                f"Action '{action_name}' execution failed: {e}",
            ) from e

        # Validate result format
        if not isinstance(result, dict):
            logger.warning(
                f"Action '{action_name}' returned non-dict result: {type(result)}. "
                "Converting to dict."
            )
            if hasattr(result, "__dict__"):
                result = result.__dict__
            else:
                result = {"result": result}

        # Validate outputs match expected outputs
        expected_outputs = set(action_config.outputs)
        actual_outputs = set(result.keys())

        if not expected_outputs.issubset(actual_outputs):
            missing = expected_outputs - actual_outputs
            logger.warning(
                f"Action '{action_name}' missing expected outputs: {missing}. "
                f"Expected: {expected_outputs}, Got: {actual_outputs}"
            )

        logger.info(f"Action '{action_name}' executed successfully. Outputs: {list(result.keys())}")

        return result  # type: ignore[no-any-return]

    def _load_handler(self, handler_path: str) -> Callable:
        """
        Load a handler function from Python path.

        Args:
            handler_path: Python path to handler (e.g., "handlers.flights.search")

        Returns:
            Callable handler function

        Raises:
            ActionNotFoundError: If handler cannot be loaded
        """
        # Check cache
        if handler_path in self._handler_cache:
            return self._handler_cache[handler_path]

        try:
            # Split path into module and function name
            parts = handler_path.split(".")
            if len(parts) < 2:
                raise ValueError(
                    f"Invalid handler path: {handler_path}. "
                    "Expected format: 'module.path.to.function'"
                )

            module_path = ".".join(parts[:-1])
            function_name = parts[-1]

            # Import module
            module = importlib.import_module(module_path)

            # Get function
            if not hasattr(module, function_name):
                raise AttributeError(
                    f"Module '{module_path}' does not have attribute '{function_name}'"
                )

            handler = getattr(module, function_name)

            # Validate it's callable
            if not callable(handler):
                raise TypeError(
                    f"Handler '{handler_path}' is not callable. Got type: {type(handler)}"
                )

            # Cache and return
            self._handler_cache[handler_path] = handler
            logger.info(f"Loaded handler: {handler_path}")

            return handler  # type: ignore[no-any-return]

        except ImportError as e:
            raise ActionNotFoundError(
                action_name=handler_path,
                context={"import_error": str(e)},
            ) from e
        except (AttributeError, TypeError, ValueError) as e:
            raise ActionNotFoundError(
                action_name=handler_path,
                context={"error": str(e)},
            ) from e
