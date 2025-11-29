"""Domain-specific exceptions for Soni Framework"""

from typing import Any, Optional


class SoniError(Exception):
    """Base exception for all Soni Framework errors"""

    def __init__(self, message: str, context: Optional[dict] = None):
        super().__init__(message)
        self.message = message
        self.context = context or {}

    def __str__(self) -> str:
        if self.context:
            context_str = ", ".join(f"{k}={v}" for k, v in self.context.items())
            return f"{self.message} ({context_str})"
        return self.message


class NLUError(SoniError):
    """Error during Natural Language Understanding"""

    pass


class ValidationError(SoniError):
    """Error during slot/entity validation"""

    def __init__(self, message: str, field: Optional[str] = None, value: Any = None, context: Optional[dict] = None):
        super().__init__(message, context)
        self.field = field
        self.value = value


class ActionNotFoundError(SoniError):
    """Error when an action is not found"""

    def __init__(self, action_name: str, context: Optional[dict] = None):
        message = f"Action '{action_name}' not found"
        super().__init__(message, context)
        self.action_name = action_name


class CompilationError(SoniError):
    """Error during YAML to graph compilation"""

    def __init__(self, message: str, yaml_path: Optional[str] = None, line: Optional[int] = None, context: Optional[dict] = None):
        super().__init__(message, context)
        self.yaml_path = yaml_path
        self.line = line


class ConfigurationError(SoniError):
    """Error in configuration loading or validation"""

    pass


class PersistenceError(SoniError):
    """Error during state persistence"""

    pass

