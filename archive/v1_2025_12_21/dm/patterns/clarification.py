"""Handler for RequestClarification pattern."""

import logging

from langchain_core.messages import AIMessage
from soni.core.commands import RequestClarification
from soni.core.types import DialogueState, RuntimeContext
from soni.dm.nodes.command_registry import CommandResult
from soni.dm.patterns.base import get_pattern_config

logger = logging.getLogger(__name__)


class ClarificationHandler:
    """Handles RequestClarification commands."""

    async def handle(
        self,
        cmd: RequestClarification,
        state: DialogueState,
        context: RuntimeContext,
    ) -> CommandResult:
        """Handle clarification request."""
        logger.info(f"Handling RequestClarification: {cmd.topic}")

        expected_slot = state.get("waiting_for_slot")
        topic = cmd.topic or expected_slot
        explanation = "I need this information to proceed."

        # Try to find slot description
        if topic:
            slot_cfg = context.config.slots.get(topic)
            if slot_cfg and slot_cfg.description:
                explanation = slot_cfg.description

        # Apply config template
        patterns = get_pattern_config(context)
        if patterns:
            template = patterns.clarification.response_template
            if "{explanation}" in template:
                explanation = template.format(explanation=explanation)
            else:
                explanation = template

        # Do NOT reset flow state - remain waiting for input
        return CommandResult(
            messages=[AIMessage(content=explanation)]
            # No state updates for clarification
        )
