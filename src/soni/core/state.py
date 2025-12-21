"""State factory functions."""

from soni.core.types import DialogueState


def create_empty_state() -> DialogueState:
    """Create an empty dialogue state."""
    return {
        "user_message": None,
        "messages": [],
        "response": None,
    }
