"""Core interaction errors."""

class SoniError(Exception):
    """Base class for all Soni errors."""
    pass


class GraphBuildError(SoniError):
    """Error raised during graph construction."""
    pass


class ConfigError(SoniError):
    """Configuration validation error."""
    pass
