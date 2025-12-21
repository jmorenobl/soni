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
