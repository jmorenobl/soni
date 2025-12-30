"""Core interaction errors."""


class SoniError(Exception):
    """Base class for all Soni errors."""

    pass


class GraphBuildError(SoniError):
    """Error raised during graph construction."""

    pass


class ConfigError(SoniError):
    """Raised when configuration is invalid."""


class FlowStackError(SoniError):
    """Raised when flow stack operations fail."""

    pass


class StateError(SoniError):
    """Raised when state operations fail."""

    pass


class ActionError(SoniError):
    """Raised when action execution fails."""

    pass


class FlowError(SoniError):
    """Raised when flow execution fails."""

    pass


class NLUError(SoniError):
    """Raised when NLU processing fails."""

    pass


class NLUParsingError(NLUError):
    """Failed to parse NLU response."""

    pass


class NLUTimeoutError(NLUError):
    """NLU request timed out."""

    pass


class NLUProviderError(NLUError):
    """Error from the underlying LLM provider."""

    pass


class SlotError(SoniError):
    """Raised when slot operations fail."""

    pass


class ValidationError(SoniError):
    """Raised when validation fails."""

    pass
