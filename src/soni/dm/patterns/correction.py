"""Handler for CorrectSlot pattern."""

import logging

from langchain_core.messages import AIMessage

from soni.core.commands import CorrectSlot
from soni.core.types import DialogueState, RuntimeContext
from soni.dm.nodes.command_registry import CommandResult
from soni.dm.patterns.base import get_pattern_config
from soni.flow.manager import merge_delta

logger = logging.getLogger(__name__)


class CorrectionHandler:
    """Handles CorrectSlot commands."""

    async def handle(
        self,
        cmd: CorrectSlot,
        state: DialogueState,
        context: RuntimeContext,
    ) -> CommandResult:
        """Handle slot correction."""
        logger.info(f"Handling CorrectSlot: {cmd.slot}={cmd.new_value}")

        # Update slot and get delta
        delta = context.flow_manager.set_slot(state, cmd.slot, cmd.new_value)

        # Generate response from config
        patterns = get_pattern_config(context)
        template = (
            patterns.correction.response_template if patterns else "Updated {slot} to {new_value}."
        )
        response_text = template.format(slot=cmd.slot, value=cmd.new_value, new_value=cmd.new_value)

        # Build result with delta
        result = CommandResult(messages=[AIMessage(content=response_text)])

        if delta:
            merge_delta(result.updates, delta)
            result.applied_delta = True

        return result
