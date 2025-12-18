"""ConfirmNodeFactory - generates confirmation nodes.

Implements full confirmation flow using NLU commands:
1. First visit: Show confirmation prompt, wait for input
2. Subsequent visits: Check NLU commands for affirm/deny
3. Handle modifications and retries

Refactored to use separate handlers for each concern (SRP).
"""

import logging
from typing import Any

from langchain_core.runnables import RunnableConfig
from langgraph.types import Command

from soni.config.steps import ConfirmStepConfig, StepConfig
from soni.core.errors import ValidationError
from soni.core.types import DialogueState, get_runtime_context
from soni.dm.patterns.base import get_pattern_config

from .base import NodeFunction
from .confirm_handlers import (
    AffirmHandler,
    ConfirmationContext,
    DenyHandler,
    FirstVisitHandler,
    ModificationHandler,
    RetryHandler,
)

logger = logging.getLogger(__name__)


def _find_confirmation_command(commands: list[Any]) -> tuple[bool | None, str | None]:
    """Find affirm or deny command in NLU output.

    Args:
        commands: List of command objects or dicts from NLU.

    Returns:
        Tuple of (is_affirmed, slot_to_change).
        - (True, None) for affirm
        - (False, slot_name) for deny with optional slot to change
        - (None, None) if no confirmation command found
    """
    for cmd in commands:
        if isinstance(cmd, dict):
            cmd_type = cmd.get("type")
        else:
            cmd_type = getattr(cmd, "type", None)

        if cmd_type == "affirm_confirmation":
            return (True, None)
        if cmd_type == "deny_confirmation":
            slot_to_change = (
                cmd.get("slot_to_change")
                if isinstance(cmd, dict)
                else getattr(cmd, "slot_to_change", None)
            )
            return (False, slot_to_change)

    return (None, None)


class ConfirmNodeFactory:
    """Factory for confirm step nodes.

    Creates nodes that:
    1. Prompt for confirmation on first visit
    2. Check NLU commands for affirm/deny on subsequent visits
    3. Re-ask if no clear confirmation command (up to max_retries)

    Uses separate handlers for each concern (SRP):
    - FirstVisitHandler: Initial prompt
    - AffirmHandler: Affirmation processing
    - DenyHandler: Denial with optional modification
    - ModificationHandler: Slot modifications
    - RetryHandler: Max retries logic
    """

    def __init__(self) -> None:
        self._first_visit = FirstVisitHandler()
        self._affirm = AffirmHandler()
        self._deny = DenyHandler()
        self._modification = ModificationHandler()
        self._retry = RetryHandler()

    def create(
        self,
        step: StepConfig,
        all_steps: list[StepConfig] | None = None,
        step_index: int | None = None,
    ) -> NodeFunction:
        """Create a node that requests and processes confirmation."""
        if not isinstance(step, ConfirmStepConfig):
            raise ValueError(f"ConfirmNodeFactory received wrong step type: {type(step).__name__}")

        if not step.slot:
            raise ValidationError(
                f"Step '{step.step}' of type 'confirm' is missing required field 'slot'"
            )

        slot_name = step.slot
        prompt = step.message or f"Please confirm {slot_name} (yes/no)"
        retry_key = f"__confirm_retries_{slot_name}"
        max_retries = step.max_retries

        # Capture handlers for closure
        first_visit = self._first_visit
        affirm = self._affirm
        deny = self._deny
        modification = self._modification
        retry = self._retry

        async def confirm_node(
            state: DialogueState,
            config: RunnableConfig,
        ) -> dict[str, Any] | Command:
            context = get_runtime_context(config)
            flow_manager = context.flow_manager

            # Get pattern config
            patterns = get_pattern_config(context)
            confirmation_config = patterns.confirmation if patterns else None

            # Build confirmation context
            ctx = ConfirmationContext(
                slot_name=slot_name,
                prompt=prompt,
                retry_key=retry_key,
                flow_manager=flow_manager,
                confirmation_config=confirmation_config,
                max_retries=max_retries,
            )

            # Build updates dict for merging deltas
            updates: dict[str, Any] = {}

            # Check if confirmation slot is already filled
            value = flow_manager.get_slot(state, slot_name)
            if value is not None:
                return {"flow_state": "active"}

            # Check if we're waiting for this slot (subsequent visit)
            if state.get("waiting_for_slot") == slot_name:
                # Get NLU commands from state
                commands = state.get("commands", [])

                is_affirmed, slot_to_change = _find_confirmation_command(commands)

                if is_affirmed is True:
                    return affirm.handle(ctx, state, updates)

                if is_affirmed is False:
                    return deny.handle(ctx, state, updates, commands, slot_to_change)

                # NLU didn't produce affirm/deny - check for slot modification
                has_modification = any(c.get("type") == "set_slot" for c in commands)

                if has_modification:
                    return modification.handle(ctx, state, updates)

                # No modification - do retry logic
                return retry.handle(ctx, state, updates)

            # First visit - ask for confirmation
            return first_visit.handle(ctx, state)

        confirm_node.__name__ = f"confirm_{step.step}"
        return confirm_node
