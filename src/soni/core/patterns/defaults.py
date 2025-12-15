"""Default patterns registration."""

from soni.core.patterns.cancellation import CancellationPattern
from soni.core.patterns.chitchat import ChitChatPattern
from soni.core.patterns.clarification import ClarificationPattern
from soni.core.patterns.confirmation import ConfirmationPattern
from soni.core.patterns.correction import CorrectionPattern
from soni.core.patterns.registry import PatternRegistry


def register_default_patterns() -> None:
    """Register all built-in patterns."""
    PatternRegistry.register(CorrectionPattern())
    PatternRegistry.register(ClarificationPattern())
    PatternRegistry.register(CancellationPattern())
    PatternRegistry.register(ConfirmationPattern())
    PatternRegistry.register(ChitChatPattern())
