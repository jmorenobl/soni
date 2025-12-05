"""Domain-specific exceptions for Soni Framework."""

from typing import Any


class SoniError(Exception):
    """Base exception for all Soni errors."""

    def __init__(self, message: str, **context: Any) -> None:
        """Initialize SoniError.

        Args:
            message: Error message.
            **context: Optional context key-value pairs.
        """
        super().__init__(message)
        self.message = message
        self.context = context

    def __str__(self) -> str:
        """Return string representation of error."""
        if self.context:
            ctx_str = ", ".join(f"{k}={v}" for k, v in self.context.items())
            return f"{self.message} ({ctx_str})"
        return self.message


class NLUError(SoniError):
    """Error during Natural Language Understanding."""

    pass


class ValidationError(SoniError):
    """Error during validation."""

    pass


class ActionNotFoundError(SoniError):
    """Action not found in registry."""

    pass


class CompilationError(SoniError):
    """Error during YAML compilation."""

    pass


class ConfigurationError(SoniError):
    """Error in configuration loading or validation"""

    pass


class PersistenceError(SoniError):
    """Error during state persistence."""

    pass


class FlowStackLimitError(SoniError):
    """Flow stack depth limit exceeded."""

    pass
