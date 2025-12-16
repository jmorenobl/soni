"""State factory and helper functions."""
from soni.core.types import DialogueState


def create_empty_dialogue_state() -> DialogueState:
    """Factory function for empty dialogue state."""
    return {
        "user_message": None,
        "last_response": "",
        "messages": [],
        "flow_stack": [],
        "flow_slots": {},
        "flow_state": "idle",
        "waiting_for_slot": None,
        "commands": [],
        "response": None,
        "action_result": None,
        "turn_count": 0,
        "metadata": {},
    }
