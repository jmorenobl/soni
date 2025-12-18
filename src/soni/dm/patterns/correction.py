"""Handler for CorrectSlot pattern."""

import logging
from typing import Any

from langchain_core.messages import AIMessage

from soni.core.commands import CorrectSlot
from soni.core.types import DialogueState, RuntimeContext
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
    ) -> tuple[dict[str, Any], list[AIMessage]]:
        """Handle slot correction."""
        logger.info(f"Handling CorrectSlot: {cmd.slot}={cmd.new_value}")

        # Update slot and get delta
        delta = context.flow_manager.set_slot(state, cmd.slot, cmd.new_value)

        # Build updates from delta
        updates: dict[str, Any] = {}
        merge_delta(updates, delta)

        # Generate response from config
        patterns = get_pattern_config(context)
        template = (
            patterns.correction.response_template if patterns else "Updated {slot} to {new_value}."
        )
        response_text = template.format(slot=cmd.slot, value=cmd.new_value, new_value=cmd.new_value)

        return updates, [AIMessage(content=response_text)]
