"""Conversation patterns package."""

from soni.core.patterns.base import ConversationPattern
from soni.core.patterns.cancellation import CancellationPattern
from soni.core.patterns.clarification import ClarificationPattern
from soni.core.patterns.confirmation import ConfirmationPattern
from soni.core.patterns.correction import CorrectionPattern
from soni.core.patterns.defaults import register_default_patterns
from soni.core.patterns.registry import PatternRegistry

__all__ = [
    "ConversationPattern",
    "PatternRegistry",
    "register_default_patterns",
    "CorrectionPattern",
    "ClarificationPattern",
    "CancellationPattern",
    "ConfirmationPattern",
]
