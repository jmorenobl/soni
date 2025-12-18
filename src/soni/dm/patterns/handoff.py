"""Handler for HumanHandoff pattern."""

import logging
from typing import Any

from langchain_core.messages import AIMessage

from soni.core.commands import HumanHandoff
from soni.core.types import DialogueState, RuntimeContext
from soni.dm.patterns.base import get_pattern_config

logger = logging.getLogger(__name__)


class HumanHandoffHandler:
    """Handles HumanHandoff commands."""

    async def handle(
        self,
        cmd: HumanHandoff,
        state: DialogueState,
        context: RuntimeContext,
    ) -> tuple[dict[str, Any], list[AIMessage]]:
        """Handle human handoff."""
        logger.info("Handling HumanHandoff")

        patterns = get_pattern_config(context)
        message = patterns.human_handoff.message if patterns else "Transferring you to an agent..."

        return {"should_reset_flow_state": True}, [AIMessage(content=message)]
