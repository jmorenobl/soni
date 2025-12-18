"""Handler for HumanHandoff pattern."""

import logging

from langchain_core.messages import AIMessage

from soni.core.commands import HumanHandoff
from soni.core.types import DialogueState, RuntimeContext
from soni.dm.nodes.command_registry import CommandResult
from soni.dm.patterns.base import get_pattern_config

logger = logging.getLogger(__name__)


class HumanHandoffHandler:
    """Handles HumanHandoff commands."""

    async def handle(
        self,
        cmd: HumanHandoff,
        state: DialogueState,
        context: RuntimeContext,
    ) -> CommandResult:
        """Handle human handoff request."""
        logger.info("Handling HumanHandoff")

        patterns = get_pattern_config(context)
        response_text = (
            patterns.human_handoff.message if patterns else "Transferring you to a human agent..."
        )

        return CommandResult(messages=[AIMessage(content=response_text)])
