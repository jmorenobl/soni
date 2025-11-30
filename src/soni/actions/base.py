"""Action handlers for Soni Framework"""

import inspect
import logging
from typing import Any

from soni.actions.registry import ActionRegistry
from soni.core.config import SoniConfig
from soni.core.errors import ActionNotFoundError, ValidationError
from soni.core.security import SecurityGuardrails, validate_action_name

logger = logging.getLogger(__name__)


class ActionHandler:
    """
    Handles execution of external action handlers.

    This class executes Python functions registered via ActionRegistry.
    Actions must be registered using @ActionRegistry.register() decorator.
    This implements zero-leakage architecture: no Python paths in YAML.
    """

    def __init__(self, config: SoniConfig):
        """
        Initialize the action handler.

        Args:
            config: Soni configuration containing action definitions
        """
        self.config = config
        # Initialize security guardrails from config
        security_config = config.settings.security
        self.guardrails: SecurityGuardrails | None = (
            SecurityGuardrails(
                allowed_actions=security_config.allowed_actions
                if security_config.allowed_actions
                else None,
                blocked_intents=security_config.blocked_intents
                if security_config.blocked_intents
                else None,
                max_confidence_threshold=security_config.max_confidence_threshold,
                min_confidence_threshold=security_config.min_confidence_threshold,
            )
            if security_config.enable_guardrails
            else None
        )

    async def execute(self, action_name: str, slots: dict[str, Any]) -> dict[str, Any]:
        """
        Execute an action handler.

        Args:
            action_name: Name of the action to execute
            slots: Dictionary of slot values to pass as inputs

        Returns:
            Dictionary with action outputs

        Raises:
            ValidationError: If action name is invalid
            ValidationError: If action is blocked by guardrails
            ActionNotFoundError: If action is not found in config
            ActionNotFoundError: If handler cannot be loaded
            RuntimeError: If handler execution fails
        """
        # Validate action name format (prevent injection)
        try:
            validate_action_name(action_name)
        except ValidationError:
            logger.warning(f"Invalid action name format: {action_name}")
            raise

        # Check security guardrails if enabled
        if self.guardrails:
            is_valid, error = self.guardrails.validate_action(action_name)
            if not is_valid:
                logger.warning(f"Action '{action_name}' blocked by guardrails: {error}")
                raise ValidationError(f"Action execution blocked: {error}")

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
