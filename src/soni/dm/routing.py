"""Routing logic for dialogue flows"""

from typing import Any

from soni.core.state import DialogueState


def should_continue(state: DialogueState | dict[str, Any]) -> str:
    """
    Determine next step after understanding.

    Args:
        state: Current dialogue state

    Returns:
        Next node name

    Note:
        This is a placeholder for future routing logic.
        Currently, flows are linear and routing is handled by DAG edges.
    """
    if isinstance(state, dict):
        state = DialogueState.from_dict(state)

    # For linear flows, routing is handled by sequential edges
    # This function is reserved for future conditional routing
    return "continue"


def route_by_intent(state: DialogueState | dict[str, Any]) -> str:
    """
    Route to flow based on intent.

    Args:
        state: Current dialogue state

    Returns:
        Flow name to route to

    Note:
        This is a placeholder for future intent-based routing.
    """
    if isinstance(state, dict):
        state = DialogueState.from_dict(state)

    # Placeholder for future intent-based routing
    # For now, flows are explicitly called
    return "fallback"
