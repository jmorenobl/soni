"""Registry for managing active Conversation Patterns."""

import logging

from soni.core.patterns.base import ConversationPattern

logger = logging.getLogger(__name__)


class PatternRegistry:
    """Registry for Conversation Patterns."""

    _patterns: dict[str, ConversationPattern] = {}

    @classmethod
    def register(cls, pattern_instance: ConversationPattern) -> None:
        """Register a pattern instance."""
        cls._patterns[pattern_instance.name] = pattern_instance
        logger.info(f"Registered conversation pattern: {pattern_instance.name}")

    @classmethod
    def get(cls, name: str) -> ConversationPattern | None:
        """Get a pattern by name."""
        return cls._patterns.get(name)

    @classmethod
    def get_all(cls) -> list[ConversationPattern]:
        """Get all registered patterns."""
        return list(cls._patterns.values())

    @classmethod
    def clear(cls) -> None:
        """Clear all patterns (useful for testing)."""
        cls._patterns.clear()
