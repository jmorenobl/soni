"""State factory functions."""

from soni.core.types import DialogueState


def create_empty_state() -> DialogueState:
    """Create an empty dialogue state."""
    return {
        "user_message": None,
        "messages": [],  # Messages are always additive (add_messages reducer)
        "response": None,
        "flow_stack": None,  # MUST be None to avoid clobbering persistence
        "flow_slots": None,  # MUST be None
        "commands": None,  # Commands are transient but safer as None
        "_pending_task": None,
        "_executed_steps": None,
        "_branch_target": None,
        "_pending_responses": [],  # Additive reducer, safe to start empty
        "_flow_changed": None,
        "_loop_flag": None,
    }
