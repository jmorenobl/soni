"""Base protocol and utilities for node factories."""

from typing import Protocol

from langchain_core.messages import AnyMessage

from soni.config.models import StepConfig
from soni.core.types import DialogueState, NodeFunction
from soni.runtime.context import RuntimeContext


class NodeFactory(Protocol):
    """Protocol for step type node factories (OCP: Open for extension)."""

    def create(
        self,
        step: StepConfig,
        all_steps: list[StepConfig] | None = None,
        step_index: int | None = None,
    ) -> NodeFunction:
        """Create a node function for the given step config."""
        ...


def build_conversation_context(state: DialogueState, max_messages: int = 5) -> str:
    """Build conversation context from recent messages.

    Args:
        state: Current dialogue state
        max_messages: Maximum number of recent messages to include

    Returns:
        Formatted conversation context string
    """
    messages: list[AnyMessage] = state.get("messages", [])[-max_messages:]
    context_parts = []
    for msg in messages:
        role = getattr(msg, "type", "unknown")
        content = getattr(msg, "content", str(msg))
        context_parts.append(f"{role}: {content}")
    return "\n".join(context_parts)


async def rephrase_if_enabled(
    message: str,
    state: DialogueState,
    context: RuntimeContext,
    rephrase_step: bool,
) -> str:
    """Rephrase message if rephrasing is enabled.

    Args:
        message: Original template message
        state: Current dialogue state
        context: Runtime context with rephraser
        rephrase_step: Whether this step allows rephrasing

    Returns:
        Rephrased message if enabled, original otherwise

    Note:
        DSPy's Module.acall() returns Any even though ResponseRephraser.aforward()
        returns str. We use str() to satisfy mypy and ensure type safety.
    """
    rephraser = context.rephraser
    if not rephraser or not rephrase_step:
        return message

    try:
        conversation_context = build_conversation_context(state)
        # ResponseRephraser.aforward() returns str, but DSPy's acall() is typed as -> Any
        return await rephraser.acall(template=message, context=conversation_context)  # type: ignore[no-any-return]
    except Exception:
        # On error, fall back to original message
        return message
