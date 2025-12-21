"""Base protocols and helpers for pattern handlers."""

from typing import Any, Protocol

from soni.core.types import DialogueState, RuntimeContext
from soni.dm.nodes.command_registry import CommandResult

from soni.config import PatternBehaviorsConfig


class PatternHandler(Protocol):
    """Protocol for pattern handlers.

    Each handler processes a specific command type and returns
    CommandResult for consistency with command handlers.
    """

    async def handle(
        self,
        cmd: Any,
        state: DialogueState,
        context: RuntimeContext,
    ) -> CommandResult:
        """Handle a command and return CommandResult.

        Args:
            cmd: The command to handle
            state: Current dialogue state
            context: Runtime context with config and managers

        Returns:
            CommandResult with updates and response messages
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
