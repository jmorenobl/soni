"""Command Handler Registry - Dispatches NLU commands to handlers.

Extracted from understand_node to follow Single Responsibility Principle.
Each command type has a dedicated handler, following OCP (Open/Closed Principle).
"""

import logging
from dataclasses import dataclass, field
from typing import Any, Protocol

from soni.core.commands import (
    AffirmConfirmation,
    CancelFlow,
    CorrectSlot,
    DenyConfirmation,
    HumanHandoff,
    RequestClarification,
    SetSlot,
    StartFlow,
)
from soni.core.types import DialogueState, RuntimeContext
from soni.flow.manager import merge_delta

logger = logging.getLogger(__name__)


@dataclass
class CommandResult:
    """Result from processing a command.

    Attributes:
        updates: State updates to merge into return dict.
        messages: Response messages to emit.
        should_reset_flow_state: Whether to reset flow state to active.
        applied_delta: Whether a FlowDelta was applied to state.
    """

    updates: dict[str, Any] = field(default_factory=dict)
    messages: list[Any] = field(default_factory=list)
    should_reset_flow_state: bool = False
    applied_delta: bool = False


class CommandHandler(Protocol):
    """Protocol for command handlers."""

    async def handle(
        self,
        cmd: Any,
        state: DialogueState,
        context: RuntimeContext,
        expected_slot: str | None,
    ) -> CommandResult:
        """Handle a command and return result."""
        ...


class StartFlowHandler:
    """Handles StartFlow commands."""

    async def handle(
        self,
        cmd: StartFlow,
        state: DialogueState,
        context: RuntimeContext,
        expected_slot: str | None,
    ) -> CommandResult:
        fm = context.flow_manager
        result = CommandResult()

        delta = fm.handle_intent_change(state, cmd.flow_name)
        merge_delta(result.updates, delta)
        result.applied_delta = delta is not None

        # Apply delta to state for subsequent commands in same turn
        if delta:
            if delta.flow_stack is not None:
                state["flow_stack"] = delta.flow_stack
            if delta.flow_slots is not None:
                state["flow_slots"] = delta.flow_slots

        return result


class SetSlotHandler:
    """Handles SetSlot commands."""

    async def handle(
        self,
        cmd: SetSlot,
        state: DialogueState,
        context: RuntimeContext,
        expected_slot: str | None,
    ) -> CommandResult:
        fm = context.flow_manager
        result = CommandResult()

        delta = fm.set_slot(state, cmd.slot, cmd.value)
        merge_delta(result.updates, delta)
        result.applied_delta = delta is not None

        # Apply delta to state for subsequent commands
        if delta and delta.flow_slots is not None:
            state["flow_slots"] = delta.flow_slots

        # Check if this is the slot we were waiting for
        if cmd.slot == expected_slot:
            result.should_reset_flow_state = True

        return result


class ConfirmationHandler:
    """Handles AffirmConfirmation and DenyConfirmation commands."""

    async def handle(
        self,
        cmd: AffirmConfirmation | DenyConfirmation,
        state: DialogueState,
        context: RuntimeContext,
        expected_slot: str | None,
    ) -> CommandResult:
        # Confirmation commands allow flow to continue
        # The confirm node will process the actual affirm/deny logic
        return CommandResult(should_reset_flow_state=True)


class PatternCommandHandler:
    """Handles pattern commands (CorrectSlot, CancelFlow, etc.)."""

    async def handle(
        self,
        cmd: CorrectSlot | CancelFlow | RequestClarification | HumanHandoff,
        state: DialogueState,
        context: RuntimeContext,
        expected_slot: str | None,
    ) -> CommandResult:
        from soni.dm.patterns import dispatch_pattern_command

        result = CommandResult()

        pattern_result = await dispatch_pattern_command(cmd, state, context)
        if pattern_result:
            pattern_updates, messages = pattern_result
            result.messages.extend(messages)

            # Merge pattern updates
            for key, value in pattern_updates.items():
                if key != "should_reset_flow_state":
                    result.updates[key] = value

            if pattern_updates.get("should_reset_flow_state"):
                result.should_reset_flow_state = True

            # Check if we corrected the slot we were waiting for
            if isinstance(cmd, CorrectSlot) and cmd.slot == expected_slot:
                result.should_reset_flow_state = True

        return result


class CommandHandlerRegistry:
    """Registry for command handlers.

    Maps command types to their handlers following OCP:
    - New command types can be added by extending, not modifying existing code.
    """

    def __init__(self):
        self._handlers: dict[type, CommandHandler] = {
            StartFlow: StartFlowHandler(),
            SetSlot: SetSlotHandler(),
            AffirmConfirmation: ConfirmationHandler(),
            DenyConfirmation: ConfirmationHandler(),
            CorrectSlot: PatternCommandHandler(),
            CancelFlow: PatternCommandHandler(),
            RequestClarification: PatternCommandHandler(),
            HumanHandoff: PatternCommandHandler(),
        }

    def register(self, cmd_type: type, handler: CommandHandler) -> None:
        """Register a handler for a command type."""
        self._handlers[cmd_type] = handler

    def get_handler(self, cmd: Any) -> CommandHandler | None:
        """Get handler for a command, or None if unhandled."""
        return self._handlers.get(type(cmd))

    async def dispatch(
        self,
        cmd: Any,
        state: DialogueState,
        context: RuntimeContext,
        expected_slot: str | None,
    ) -> CommandResult | None:
        """Dispatch a command to its handler.

        Returns:
            CommandResult if handled, None if no handler exists.
        """
        handler = self.get_handler(cmd)
        if handler:
            return await handler.handle(cmd, state, context, expected_slot)

        # Log unhandled commands
        cmd_type = getattr(cmd, "type", type(cmd).__name__)
        logger.debug(f"Command type handled by routing: {cmd_type}")
        return None


# Global singleton for efficiency (stateless handlers)
_global_registry: CommandHandlerRegistry | None = None


def get_command_registry() -> CommandHandlerRegistry:
    """Get the global command handler registry."""
    global _global_registry
    if _global_registry is None:
        _global_registry = CommandHandlerRegistry()
    return _global_registry
