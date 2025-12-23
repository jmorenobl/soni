"""Command handlers for orchestrator (OCP: Open for Extension)."""

from abc import ABC, abstractmethod
from typing import TYPE_CHECKING, Any

from soni.core.types import DialogueState, FlowDelta

if TYPE_CHECKING:
    from soni.flow.manager import FlowManager


class CommandHandler(ABC):
    """Abstract handler for processing NLU commands."""

    @abstractmethod
    def can_handle(self, command: dict[str, Any]) -> bool:
        """Check if this handler can process the command."""
        ...

    @abstractmethod
    async def handle(
        self,
        command: dict[str, Any],
        state: "DialogueState",
        flow_manager: "FlowManager",
    ) -> FlowDelta:
        """Process the command and return state changes."""
        ...


class StartFlowHandler(CommandHandler):
    """Handles StartFlow commands."""

    def can_handle(self, command: dict[str, Any]) -> bool:
        return command.get("type") == "start_flow"

    async def handle(
        self,
        command: dict[str, Any],
        state: "DialogueState",
        flow_manager: "FlowManager",
    ) -> FlowDelta:
        _, delta = flow_manager.push_flow(state, command["flow_name"])
        return delta


class CancelFlowHandler(CommandHandler):
    """Handles CancelFlow commands."""

    def can_handle(self, command: dict[str, Any]) -> bool:
        return command.get("type") == "cancel_flow"

    async def handle(
        self,
        command: dict[str, Any],
        state: "DialogueState",
        flow_manager: "FlowManager",
    ) -> FlowDelta:
        _, delta = flow_manager.pop_flow(state)
        return delta


class SetSlotHandler(CommandHandler):
    """Handles SetSlot commands."""

    def can_handle(self, command: dict[str, Any]) -> bool:
        return command.get("type") == "set_slot"

    async def handle(
        self,
        command: dict[str, Any],
        state: "DialogueState",
        flow_manager: "FlowManager",
    ) -> FlowDelta:
        delta = flow_manager.set_slot(
            state,
            command["slot"],
            command["value"],
        )
        return delta or FlowDelta()


DEFAULT_HANDLERS: list[CommandHandler] = [
    StartFlowHandler(),
    CancelFlowHandler(),
    SetSlotHandler(),
]
