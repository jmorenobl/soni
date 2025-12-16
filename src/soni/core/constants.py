"""Constants for Soni framework.

Centralizes magic strings to prevent typos and enable IDE autocomplete.
"""

from enum import StrEnum


class FlowState(StrEnum):
    """Possible states for the dialogue flow."""

    IDLE = "idle"
    ACTIVE = "active"
    WAITING_INPUT = "waiting_input"
    DONE = "done"
    ERROR = "error"


class FlowContextState(StrEnum):
    """Possible states for a flow context on the stack."""

    ACTIVE = "active"
    COMPLETED = "completed"
    CANCELLED = "cancelled"


class CommandType(StrEnum):
    """NLU command types."""

    START_FLOW = "start_flow"
    SET_SLOT = "set_slot"
    AFFIRM = "affirm"
    DENY = "deny"
    CANCEL_FLOW = "cancel_flow"
    COMPLETE_FLOW = "complete_flow"
    CORRECT_SLOT = "correct_slot"
    CLEAR_SLOT = "clear_slot"
    CLARIFY = "clarify"
    CHITCHAT = "chitchat"
    HANDOFF = "handoff"


class NodeName(StrEnum):
    """Special node names in the graph."""

    UNDERSTAND = "understand"
    EXECUTE = "execute"
    RESPOND = "respond"
    END_FLOW = "__end_flow__"
