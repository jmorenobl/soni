"""Handler for CancelFlow pattern."""

import logging

from langchain_core.messages import AIMessage

from soni.core.commands import CancelFlow
from soni.core.types import DialogueState, RuntimeContext
from soni.dm.nodes.command_registry import CommandResult
from soni.dm.patterns.base import get_pattern_config
from soni.flow.manager import merge_delta

logger = logging.getLogger(__name__)


class CancellationHandler:
    """Handles CancelFlow commands."""

    async def handle(
        self,
        cmd: CancelFlow,
        state: DialogueState,
        context: RuntimeContext,
    ) -> CommandResult:
        """Handle flow cancellation."""
        logger.info("Handling CancelFlow")

        patterns = get_pattern_config(context)
        response_text = (
            patterns.cancellation.response_message if patterns else "Okay, I've cancelled that."
        )
        require_confirm = patterns.cancellation.require_confirmation if patterns else False

        if require_confirm:
            # TODO: Push confirmation sub-flow
            pass

        # Pop the current flow and get delta
        result = CommandResult(
            messages=[AIMessage(content=response_text)], should_reset_flow_state=True
        )

        active_ctx = context.flow_manager.get_active_context(state)
        if active_ctx:
            _, delta = context.flow_manager.pop_flow(state)
            merge_delta(result.updates, delta)
            result.applied_delta = True

        return result
