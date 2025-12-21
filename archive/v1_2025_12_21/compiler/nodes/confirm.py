"""ConfirmNodeFactory - generates confirmation nodes.

Implements the LangGraph pattern: interrupt at START of node.

Flow:
1. Check if slot already filled (idempotent)
2. Check NLU commands for affirm/deny (via state or resume)
3. If no commands, call interrupt() to get user input
4. On resume, commands come via interrupt() return value

Note: Due to subgraph state isolation, commands must be passed via
interrupt() return value, not state.commands.

Uses separate handlers for each concern (SRP):
- AffirmHandler: Affirmation processing
- DenyHandler: Denial with optional modification
- RetryHandler: Max retries logic
"""

import logging
from typing import Any

from langgraph.graph import END
from langgraph.runtime import Runtime
from langgraph.types import Command
from soni.compiler.nodes.utils import require_field
from soni.config.steps import ConfirmStepConfig, StepConfig
from soni.dm.patterns.base import get_pattern_config

from soni.core.types import DialogueState, RuntimeContext
from soni.flow.manager import merge_delta

from .base import NodeFunction
from .confirm_handlers import (
    AffirmHandler,
    ConfirmationContext,
    DenyHandler,
    RetryHandler,
    format_prompt,
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
    1. Check if already confirmed (idempotent)
    2. Check NLU commands for affirm/deny (command-based)
    3. Call interrupt() if no commands, get response via resume

    Uses separate handlers for each concern (SRP):
    - AffirmHandler: Affirmation processing
    - DenyHandler: Denial with optional modification
    - RetryHandler: Max retries logic
    """

    def __init__(self) -> None:
        self._affirm = AffirmHandler()
        self._deny = DenyHandler()
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

        slot_name = require_field(step, "slot", str)
        prompt = step.message or f"Please confirm {slot_name} (yes/no)"
        retry_key = f"__confirm_retries_{slot_name}"
        max_retries = step.max_retries

        # Capture handlers for closure
        affirm = self._affirm
        deny = self._deny
        retry = self._retry

        async def confirm_node(
            state: DialogueState,
            runtime: Runtime[RuntimeContext],
        ) -> dict[str, Any] | Command[Any]:
            context = runtime.context
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

            # 1. IDEMPOTENT: Check if confirmation slot is already filled
            value = flow_manager.get_slot(state, slot_name)
            if value is not None:
                return {}  # Already confirmed

            # Build updates dict for merging deltas
            updates: dict[str, Any] = {}

            # 2. COMMAND-BASED: Check state.commands
            commands = list(state.get("commands", []))

            # Check for affirm/deny commands
            is_affirmed, slot_to_change = _find_confirmation_command(commands)

            if is_affirmed is True:
                res = affirm.handle(ctx, state, updates)
                if res.get("_need_input"):
                    return Command(goto=END, update=res)
                return res

            if is_affirmed is False:
                res = deny.handle(ctx, state, updates, commands, slot_to_change)
                if res.get("_need_input"):
                    return Command(goto=END, update=res)
                return res

            # 3. NO COMMANDS: Need Input
            # Check retry count to determine appropriate message
            current_retries = flow_manager.get_slot(state, retry_key) or 0
            effective_max = max_retries or (
                confirmation_config.max_retries if confirmation_config else 3
            )

            if current_retries >= effective_max:
                res = retry.handle(ctx, state, updates)
                if res.get("_need_input"):
                    return Command(goto=END, update=res)
                return res

            # Get current slots for prompt formatting
            slots = flow_manager.get_all_slots(state)
            formatted_prompt = format_prompt(prompt, slots)

            # Format retry message if needed
            if current_retries > 0:
                retry_template = (
                    confirmation_config.retry_message
                    if confirmation_config
                    else "I need a clear yes or no answer. {prompt}"
                )
                formatted_prompt = retry_template.format(prompt=formatted_prompt)

            # Increment retry counter for next time
            if current_retries > 0:
                delta = flow_manager.set_slot(state, retry_key, current_retries + 1)
                if delta:
                    merge_delta(updates, delta)

            # Return _need_input with formatted prompt
            updates.update(
                {
                    "_need_input": True,
                    "_pending_prompt": {
                        "type": "confirm",
                        "slot": slot_name,
                        "prompt": formatted_prompt,
                    },
                    "waiting_for_slot": slot_name,
                    "waiting_for_slot_type": "confirmation",
                    "messages": [AIMessage(content=formatted_prompt)],
                    "last_response": formatted_prompt,
                }
            )
            return Command(goto=END, update=updates)

        confirm_node.__name__ = f"confirm_{step.step}"
        return confirm_node
