"""Core constants and enums."""

from enum import Enum


class FlowContextState(str, Enum):
    """State of a flow in the stack."""

    active = "active"
    interrupted = "interrupted"
    completed = "completed"


class NodeName(str, Enum):
    """Standard node names."""

    EXECUTE = "execute"
    RESPOND = "respond"
