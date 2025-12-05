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

    def __init__(
        self,
        message: str,
        field: str | None = None,
        value: Any = None,
        context: dict[str, Any] | None = None,
        **kwargs: Any,
    ) -> None:
        """Initialize ValidationError.

        Args:
            message: Error message.
            field: Field name that caused the error.
            value: Value that caused the error.
            context: Additional context dictionary.
            **kwargs: Additional context key-value pairs.
        """
        # Merge context dict with kwargs
        merged_context = {**(context or {}), **kwargs}
        super().__init__(message, **merged_context)
        self.field = field
        self.value = value


class ActionNotFoundError(SoniError):
    """Action not found in registry."""

    pass


class CompilationError(SoniError):
    """Error during YAML compilation."""

    def __init__(
        self,
        message: str,
        step_index: int | None = None,
        step_name: str | None = None,
        flow_name: str | None = None,
        context: dict[str, Any] | None = None,
        **kwargs: Any,
    ) -> None:
        """Initialize CompilationError.

        Args:
            message: Error message.
            step_index: 1-based index of the step that caused the error.
            step_name: Name/ID of the step that caused the error.
            flow_name: Name of the flow being compiled.
            context: Additional context dictionary.
            **kwargs: Additional context key-value pairs.
        """
        # Merge context dict with kwargs
        merged_context = {**(context or {}), **kwargs}
        super().__init__(message, **merged_context)
        self.step_index = step_index
        self.step_name = step_name
        self.flow_name = flow_name


class ConfigurationError(SoniError):
    """Error in configuration loading or validation"""

    pass


class PersistenceError(SoniError):
    """Error during state persistence."""

    pass


class FlowStackLimitError(SoniError):
    """Flow stack depth limit exceeded."""

    pass
