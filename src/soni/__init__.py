"""
Soni Framework - Open Source Conversational AI Framework

Soni is a modern framework for building task-oriented dialogue systems
with automatic prompt optimization using DSPy and LangGraph.
"""

__version__ = "0.0.1"
__author__ = "Soni Framework Contributors"

# Core exports
from soni.core.errors import (
    ActionNotFoundError,
    CompilationError,
    ConfigurationError,
    NLUError,
    PersistenceError,
    SoniError,
    ValidationError,
)
from soni.core.state import DialogueState
from soni.du.modules import NLUResult, SoniDU

__all__ = [
    # Version info
    "__version__",
    "__author__",
    # Core classes
    "DialogueState",
    "SoniDU",
    "NLUResult",
    # Errors
    "SoniError",
    "NLUError",
    "ValidationError",
    "ActionNotFoundError",
    "CompilationError",
    "ConfigurationError",
    "PersistenceError",
]
