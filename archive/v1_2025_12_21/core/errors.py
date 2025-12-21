"""Custom exception hierarchy for Soni.

Follows best practices:
- Specific exceptions for each error type
- All inherit from SoniError for catch-all handling
- Includes context in messages
"""


class SoniError(Exception):
    """Base exception for all Soni errors."""


class ConfigError(SoniError):
    """Configuration-related errors."""


class FlowError(SoniError):
    """Flow execution errors."""


class FlowStackError(FlowError):
    """Flow stack operations error (empty stack, etc.)."""


class ValidationError(SoniError):
    """Validation errors for slots, config, etc."""


class ActionError(SoniError):
    """Action execution errors."""


class NLUError(SoniError):
    """NLU/DU errors."""


class StateError(SoniError):
    """State access or mutation errors."""


class GraphBuildError(SoniError):
    """Graph compilation errors."""


class SlotError(ValidationError):
    """Slot-specific validation errors."""
