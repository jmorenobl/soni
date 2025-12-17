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
        "commands": [],
        "response": None,
        "action_result": None,
        "_branch_target": None,
        "turn_count": 0,
        "metadata": {},
    }


def is_waiting_input(state: DialogueState) -> bool:
    """Check if the dialogue is waiting for user input."""
    # Import locally to avoid circular imports if constants imports types (it doesn't, but safely)
    # Actually constants.py doesn't import types.py
    from soni.core.constants import FlowState

    return state.get("flow_state") == FlowState.WAITING_INPUT


def get_current_flow_id(state: DialogueState) -> str | None:
    """Get the ID of the current active flow (top of stack)."""
    stack = state.get("flow_stack")
    if not stack:
        return None
    return stack[-1]["flow_id"]
