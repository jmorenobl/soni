"""Command Handler Registry - Dispatches NLU commands to handlers.

Follows Open/Closed Principle: handlers are registered in module-level dict,
new handlers can be added without modifying this class.
"""

import logging
from dataclasses import dataclass, field
from typing import Any, Protocol, runtime_checkable

from langchain_core.messages import AIMessage

from soni.core.commands import (
    AffirmConfirmation,
    CancelFlow,
    ChitChat,
    ClearSlot,
    Command,
    CompleteFlow,
    CorrectSlot,
    DenyConfirmation,
    HumanHandoff,
    RequestClarification,
    SetSlot,
    StartFlow,
)
from soni.core.types import DialogueState, FlowContextState, RuntimeContext
from soni.core.validation import validate_slot_value
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
    messages: list[AIMessage] = field(default_factory=list)
    should_reset_flow_state: bool = False
    applied_delta: bool = False


@runtime_checkable
class CommandHandler(Protocol):
    """Protocol for command handlers.

    All handlers must implement this interface.
    IMPORTANT: Handlers should NOT mutate state directly.
    """

    async def handle(
        self,
        cmd: Command,
        state: DialogueState,
        context: RuntimeContext,
        expected_slot: str | None,
    ) -> CommandResult:
        """Handle a command and return result."""
        ...


# =============================================================================
# Handler Implementations
# =============================================================================


class StartFlowHandler:
    """Handles StartFlow commands."""

    async def handle(
        self,
        cmd: Command,
        state: DialogueState,
        context: RuntimeContext,
        expected_slot: str | None,
    ) -> CommandResult:
        assert isinstance(cmd, StartFlow)
        fm = context.flow_manager
        result = CommandResult()

        delta = fm.handle_intent_change(state, cmd.flow_name)
        merge_delta(result.updates, delta)
        result.applied_delta = delta is not None

        return result


class SetSlotHandler:
    """Handles SetSlot commands."""

    async def handle(
        self,
        cmd: Command,
        state: DialogueState,
        context: RuntimeContext,
        expected_slot: str | None,
    ) -> CommandResult:
        assert isinstance(cmd, SetSlot)
        fm = context.flow_manager
        result = CommandResult()

        # Validate and coerce value if slot is defined in config
        final_value = cmd.value
        if hasattr(context.config, "slots"):
            slot_config = context.config.slots.get(cmd.slot)
            if slot_config:
                try:
                    final_value = validate_slot_value(cmd.value, slot_config)
                except ValueError as e:
                    logger.warning(
                        f"Validation failed for slot '{cmd.slot}' with value '{cmd.value}': {e}"
                    )
                    # For now, we reject the update (or could set to None/invalid)
                    # We'll just return without updating
                    return result

        delta = fm.set_slot(state, cmd.slot, final_value)
        merge_delta(result.updates, delta)
        result.applied_delta = delta is not None

        # Check if this is the slot we were waiting for
        if cmd.slot == expected_slot:
            result.should_reset_flow_state = True

        return result


class ConfirmationHandler:
    """Handles AffirmConfirmation and DenyConfirmation commands."""

    async def handle(
        self,
        cmd: Command,
        state: DialogueState,
        context: RuntimeContext,
        expected_slot: str | None,
    ) -> CommandResult:
        # Confirmation commands allow flow to continue
        # The confirm node will process the actual affirm/deny logic
        return CommandResult(should_reset_flow_state=True)


class CompleteFlowHandler:
    """Handles CompleteFlow commands - marks flow as completed."""

    async def handle(
        self,
        cmd: Command,
        state: DialogueState,
        context: RuntimeContext,
        expected_slot: str | None,
    ) -> CommandResult:
        fm = context.flow_manager
        result = CommandResult()

        # Pop current flow as completed
        _popped, delta = fm.pop_flow(state, result=FlowContextState.COMPLETED)

        if delta:
            merge_delta(result.updates, delta)
            result.applied_delta = True

        return result


class ClearSlotHandler:
    """Handles ClearSlot commands - clears a slot value."""

    async def handle(
        self,
        cmd: Command,
        state: DialogueState,
        context: RuntimeContext,
        expected_slot: str | None,
    ) -> CommandResult:
        assert isinstance(cmd, ClearSlot)
        fm = context.flow_manager
        result = CommandResult()

        # Set slot to None to clear it
        delta = fm.set_slot(state, cmd.slot, None)

        if delta:
            merge_delta(result.updates, delta)
            result.applied_delta = True

        return result


class ChitChatHandler:
    """Handles ChitChat commands - non-flow conversation."""

    async def handle(
        self,
        cmd: Command,
        state: DialogueState,
        context: RuntimeContext,
        expected_slot: str | None,
    ) -> CommandResult:
        assert isinstance(cmd, ChitChat)
        # Generate response for chitchat
        response = cmd.message or "I'm here to help! What would you like to do?"

        return CommandResult(
            messages=[AIMessage(content=response)],
        )


class PatternCommandHandler:
    """Handles pattern commands (CorrectSlot, CancelFlow, etc.)."""

    async def handle(
        self,
        cmd: Command,
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


# =============================================================================
# Module-Level Handler Registry (OCP Compliant)
# =============================================================================

# Handler instances - created once at module load
_start_flow_handler = StartFlowHandler()
_set_slot_handler = SetSlotHandler()
_confirmation_handler = ConfirmationHandler()
_complete_flow_handler = CompleteFlowHandler()
_clear_slot_handler = ClearSlotHandler()
_chitchat_handler = ChitChatHandler()
_pattern_handler = PatternCommandHandler()

# Module-level handler registry - extensible without modifying class
# To add a new handler: COMMAND_HANDLERS[NewCommandType] = NewHandler()
COMMAND_HANDLERS: dict[type, CommandHandler] = {
    StartFlow: _start_flow_handler,
    SetSlot: _set_slot_handler,
    AffirmConfirmation: _confirmation_handler,
    DenyConfirmation: _confirmation_handler,
    CompleteFlow: _complete_flow_handler,
    ClearSlot: _clear_slot_handler,
    ChitChat: _chitchat_handler,
    # Pattern commands - delegated to pattern dispatcher
    CorrectSlot: _pattern_handler,
    CancelFlow: _pattern_handler,
    RequestClarification: _pattern_handler,
    HumanHandoff: _pattern_handler,
}


def register_command_handler(cmd_type: type, handler: CommandHandler) -> None:
    """Register a handler for a command type.

    Use this to add custom handlers at runtime.

    Example:
        register_command_handler(MyCustomCommand, MyHandler())
    """
    COMMAND_HANDLERS[cmd_type] = handler


# =============================================================================
# Registry Class (Simplified)
# =============================================================================


class CommandHandlerRegistry:
    """Registry for command handlers.

    Uses module-level COMMAND_HANDLERS dict for OCP compliance.
    """

    def get_handler(self, cmd: Command) -> CommandHandler | None:
        """Get handler for a command type."""
        return COMMAND_HANDLERS.get(type(cmd))

    async def dispatch(
        self,
        cmd: Command,
        state: DialogueState,
        context: RuntimeContext,
        expected_slot: str | None,
    ) -> CommandResult | None:
        """Dispatch command to appropriate handler.

        Returns:
            CommandResult if handled, None if no handler found.
        """
        handler = self.get_handler(cmd)

        if handler:
            return await handler.handle(cmd, state, context, expected_slot)

        # Log unhandled commands with warning
        cmd_type = getattr(cmd, "type", type(cmd).__name__)
        logger.warning(f"No handler registered for command type: {cmd_type}")
        return None


# Global singleton for efficiency (stateless handlers)
_global_registry: CommandHandlerRegistry | None = None


def get_command_registry() -> CommandHandlerRegistry:
    """Get the global command handler registry."""
    global _global_registry
    if _global_registry is None:
        _global_registry = CommandHandlerRegistry()
    return _global_registry
