"""State factory and helper functions."""

from soni.core.constants import FlowState
from soni.core.types import DialogueState


def create_empty_dialogue_state() -> DialogueState:
    """Factory function for empty dialogue state."""
    return {
        "user_message": None,
        "last_response": "",
        "messages": [],
        "flow_stack": [],
        "flow_slots": {},
        "flow_state": FlowState.IDLE,
        "waiting_for_slot": None,
        "waiting_for_slot_type": None,
        "commands": [],
        "response": None,
        "action_result": None,
        "_branch_target": None,
        "turn_count": 0,
        "metadata": {},
    }


def is_waiting_input(state: DialogueState) -> bool:
    """Check if dialogue is waiting for user input.

    DEPRECATED: Now using LangGraph interrupt() instead of manual state.
    This function is kept temporarily for Phase 2, will be removed in Phase 3.
    Always returns False since collect nodes now use interrupt().
    """
    return False  # No longer using manual waiting_input stately)


def get_current_flow_id(state: DialogueState) -> str | None:
    """Get the ID of the current active flow (top of stack)."""
    stack = state.get("flow_stack")
    if not stack:
        return None
    return stack[-1]["flow_id"]
