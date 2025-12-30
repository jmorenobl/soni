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
    """Handles StartFlow commands with duplicate flow prevention.

    Validates that:
    - The flow_name is a valid string
    - The flow exists in config (if config provided)
    - The same flow is not already active (prevents duplicate stacking)
    """

    def __init__(self, config: Any | None = None) -> None:
        self._config = config

    def can_handle(self, command: dict[str, Any]) -> bool:
        return command.get("type") == "start_flow"

    async def handle(
        self,
        command: dict[str, Any],
        state: "DialogueState",
        flow_manager: "FlowManager",
    ) -> FlowDelta:
        flow_name = command.get("flow_name")
        if not isinstance(flow_name, str):
            return FlowDelta()

        # Validate flow exists in config (if config provided)
        if self._config and flow_name not in self._config.flows:
            return FlowDelta()

        # Skip if same flow already active (prevent duplicate stacking)
        current_ctx = flow_manager.get_active_context(state)
        if current_ctx and current_ctx["flow_name"] == flow_name:
            return FlowDelta()

        _, delta = flow_manager.push_flow(state, flow_name)
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
