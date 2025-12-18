"""Pattern Handlers - SOLID-compliant conversation pattern processing.

Each handler follows the PatternHandler protocol and handles a single command type.
This design follows:
- SRP: Each handler has one responsibility
- OCP: Add new patterns by creating new handlers, not modifying existing code
- DIP: Handlers depend on abstractions (protocol), not concrete implementations
"""

import logging
from typing import Any, Protocol

from langchain_core.messages import AIMessage

from soni.core.commands import (
    CancelFlow,
    CorrectSlot,
    HumanHandoff,
    RequestClarification,
)
from soni.core.config import PatternBehaviorsConfig
from soni.core.types import DialogueState, RuntimeContext

logger = logging.getLogger(__name__)


class PatternHandler(Protocol):
    """Protocol for pattern handlers.

    Each handler processes a specific command type and returns
    state updates and optional response messages.
    """

    async def handle(
        self,
        cmd: Any,
        state: DialogueState,
        context: RuntimeContext,
    ) -> tuple[dict[str, Any], list[AIMessage]]:
        """Handle a command and return state updates and messages.

        Args:
            cmd: The command to handle
            state: Current dialogue state
            context: Runtime context with config and managers

        Returns:
            Tuple of (state_updates dict, list of response messages)
        """
        ...


def get_pattern_config(context: RuntimeContext) -> PatternBehaviorsConfig | None:
    """Safely get pattern configuration from context.

    DRY: Centralizes the config access pattern used throughout.
    """
    if hasattr(context.config, "settings") and hasattr(context.config.settings, "patterns"):
        patterns = context.config.settings.patterns
        if isinstance(patterns, PatternBehaviorsConfig):
            return patterns
    return None


class CorrectionHandler:
    """Handles CorrectSlot commands."""

    async def handle(
        self,
        cmd: CorrectSlot,
        state: DialogueState,
        context: RuntimeContext,
    ) -> tuple[dict[str, Any], list[AIMessage]]:
        logger.info(f"Handling CorrectSlot: {cmd.slot}={cmd.new_value}")

        # Update slot
        await context.flow_manager.set_slot(state, cmd.slot, cmd.new_value)

        # Generate response from config
        patterns = get_pattern_config(context)
        template = (
            patterns.correction.response_template if patterns else "Updated {slot} to {new_value}."
        )
        response_text = template.format(slot=cmd.slot, value=cmd.new_value, new_value=cmd.new_value)

        return {}, [AIMessage(content=response_text)]


class CancellationHandler:
    """Handles CancelFlow commands."""

    async def handle(
        self,
        cmd: CancelFlow,
        state: DialogueState,
        context: RuntimeContext,
    ) -> tuple[dict[str, Any], list[AIMessage]]:
        logger.info("Handling CancelFlow")

        patterns = get_pattern_config(context)
        response_text = (
            patterns.cancellation.response_message if patterns else "Okay, I've cancelled that."
        )
        require_confirm = patterns.cancellation.require_confirmation if patterns else False

        if require_confirm:
            # TODO: Push confirmation sub-flow
            pass

        # Pop the current flow
        active_ctx = context.flow_manager.get_active_context(state)
        if active_ctx:
            await context.flow_manager.pop_flow(state)

        return {"should_reset_flow_state": True}, [AIMessage(content=response_text)]


class ClarificationHandler:
    """Handles RequestClarification commands."""

    async def handle(
        self,
        cmd: RequestClarification,
        state: DialogueState,
        context: RuntimeContext,
    ) -> tuple[dict[str, Any], list[AIMessage]]:
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
        return {}, [AIMessage(content=explanation)]


class HumanHandoffHandler:
    """Handles HumanHandoff commands."""

    async def handle(
        self,
        cmd: HumanHandoff,
        state: DialogueState,
        context: RuntimeContext,
    ) -> tuple[dict[str, Any], list[AIMessage]]:
        logger.info("Handling HumanHandoff")

        patterns = get_pattern_config(context)
        message = patterns.human_handoff.message if patterns else "Transferring you to an agent..."

        return {"should_reset_flow_state": True}, [AIMessage(content=message)]


# Registry of handlers by command type
# OCP: Add new handlers here without modifying understand_node
PATTERN_HANDLERS: dict[type, PatternHandler] = {
    CorrectSlot: CorrectionHandler(),
    CancelFlow: CancellationHandler(),
    RequestClarification: ClarificationHandler(),
    HumanHandoff: HumanHandoffHandler(),
}


async def dispatch_pattern_command(
    cmd: Any,
    state: DialogueState,
    context: RuntimeContext,
) -> tuple[dict[str, Any], list[AIMessage]] | None:
    """Dispatch a command to its appropriate handler.

    Returns None if no handler exists for this command type.
    """
    handler = PATTERN_HANDLERS.get(type(cmd))
    if handler:
        return await handler.handle(cmd, state, context)
    return None
