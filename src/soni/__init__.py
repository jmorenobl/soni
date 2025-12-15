"""Soni Framework - Open Source Conversational AI Framework.

Soni is a modern framework for building task-oriented dialogue systems
with automatic prompt optimization using DSPy and LangGraph.

Quick start:
    from soni import ConversationalFramework
    
    framework = ConversationalFramework()
    framework.load_flows("examples/flight_booking/soni.yaml")
    framework.compile()
    
    response = framework.run("Book a flight to Paris")
"""

__version__ = "3.0.0"
__author__ = "Soni Framework Contributors"

# High-level API
from soni.framework import ConversationalFramework

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
from soni.du.models import NLUOutput
from soni.du.modules import SoniDU

__all__ = [
    # Version info
    "__version__",
    "__author__",
    # High-level API
    "ConversationalFramework",
    # Core classes
    "DialogueState",
    "SoniDU",
    "NLUOutput",
    # Errors
    "SoniError",
    "NLUError",
    "ValidationError",
    "ActionNotFoundError",
    "CompilationError",
    "ConfigurationError",
    "PersistenceError",
]
