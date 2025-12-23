"""Command processor for orchestrator (SRP)."""

from typing import TYPE_CHECKING, Any

from soni.core.types import DialogueState, FlowDelta, merge_deltas
from soni.dm.orchestrator.commands import CommandHandler

if TYPE_CHECKING:
    from soni.flow.manager import FlowManager


class CommandProcessor:
    """Processes NLU commands and produces FlowDelta."""

    def __init__(self, handlers: list[CommandHandler]) -> None:
        self._handlers = handlers

    async def process(
        self,
        commands: list[dict[str, Any]],
        state: "DialogueState",
        flow_manager: "FlowManager",
    ) -> FlowDelta:
        """Process all commands and return merged delta."""
        deltas: list[FlowDelta] = []

        for command in commands:
            for handler in self._handlers:
                if handler.can_handle(command):
                    delta = await handler.handle(command, state, flow_manager)
                    deltas.append(delta)
                    break

        return merge_deltas(deltas) if deltas else FlowDelta()
