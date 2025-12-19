"""Constants for Soni framework.

Centralizes magic strings to prevent typos and enable IDE autocomplete.
"""

from enum import StrEnum


class FlowState(StrEnum):
    """Flow execution states."""

    IDLE = "idle"
    ACTIVE = "active"
    # WAITING_INPUT removed - now using LangGraph interrupt()
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


class SlotWaitType(StrEnum):
    """Type of input the system is waiting for.

    Used to determine conversation state without relying on slot naming conventions.
    """

    CONFIRMATION = "confirmation"  # Waiting for yes/no confirmation
    COLLECTION = "collection"  # Waiting for a slot value


class SlotType(StrEnum):
    """Types of slots."""

    STRING = "string"
    NUMBER = "number"
    BOOLEAN = "boolean"
    LIST = "list"
    DICT = "dict"
    ANY = "any"


class NodeName(StrEnum):
    """Special node names in the graph."""

    UNDERSTAND = "understand"
    EXECUTE = "execute"
    RESPOND = "respond"
    RESUME = "resume"
    LOOP = "loop"
    END = "end"
    END_FLOW = "__end_flow__"


def get_flow_node_name(flow_name: str) -> str:
    """Generate LangGraph node name for a flow.

    Centralizes the naming convention to avoid magic strings.

    Args:
        flow_name: Name of the flow (e.g., "book_flight")

    Returns:
        Node name for LangGraph (e.g., "flow_book_flight")
    """
    return f"flow_{flow_name}"
