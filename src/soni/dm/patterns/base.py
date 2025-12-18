"""Base protocols and helpers for pattern handlers."""

from typing import Any, Protocol

from langchain_core.messages import AIMessage

from soni.core.config import PatternBehaviorsConfig
from soni.core.types import DialogueState, RuntimeContext


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
