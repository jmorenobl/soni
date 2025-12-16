"""Custom exception hierarchy for Soni."""


class SoniError(Exception):
    """Base exception for all Soni errors."""
    pass


class ConfigError(SoniError):
    """Configuration-related errors."""
    pass


class FlowError(SoniError):
    """Flow execution errors."""
    pass


class FlowStackError(FlowError):
    """Flow stack operations error (empty stack, etc.)."""
    pass


class ValidationError(SoniError):
    """Validation errors for slots, config, etc."""
    pass


class ActionError(SoniError):
    """Action execution errors."""
    pass


class NLUError(SoniError):
    """NLU/DU errors."""
    pass
