"""Test factories for creating test objects."""
from typing import Any


def make_dialogue_state(**overrides: Any) -> dict:
    """Create a DialogueState with defaults, allowing overrides."""
    defaults = {
        "messages": [],
        "flow_stack": [],
        "flow_slots": {},
        "turn_count": 0,
        "user_message": None,
    }
    return {**defaults, **overrides}


def make_flow_context(**overrides: Any) -> dict:
    """Create a FlowContext with defaults, allowing overrides."""
    import uuid
    defaults = {
        "flow_id": str(uuid.uuid4()),
        "flow_name": "test_flow",
        "step_index": 0,
        "flow_state": "active",
        "started_at": 0.0,
    }
    return {**defaults, **overrides}
