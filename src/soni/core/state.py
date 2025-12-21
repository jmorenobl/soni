"""State factory functions."""

from soni.core.types import DialogueState


def create_empty_state() -> DialogueState:
    """Create an empty dialogue state."""
    return {
        "user_message": None,
        "messages": [],
        "response": None,
        "flow_stack": [],
        "flow_slots": {},
        "commands": [],
        "_need_input": False,
        "_pending_prompt": None,
        "_executed_steps": {},
        "_branch_target": None,
        "_pending_responses": [],
        "_flow_changed": False,
    }
