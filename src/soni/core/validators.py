"""State validation for Soni Framework."""

from soni.core.errors import ValidationError
from soni.core.types import DialogueState

# Valid state transitions (see state machine diagram)
# Note: "collecting" state has been deprecated in favor of "waiting_for_slot"
VALID_TRANSITIONS: dict[str, list[str]] = {
    "idle": ["understanding"],
    "understanding": ["waiting_for_slot", "validating_slot", "executing_action", "error", "idle"],
    "waiting_for_slot": ["understanding", "validating_slot"],
    "validating_slot": ["waiting_for_slot", "ready_for_action", "ready_for_confirmation", "error"],
    "ready_for_action": ["executing_action"],
    "ready_for_confirmation": ["confirming"],
    "confirming": ["ready_for_action", "understanding"],
    "executing_action": ["generating_response", "ready_for_action", "error"],
    "generating_response": ["idle", "understanding"],
    "completed": ["generating_response"],
    "error": ["idle", "understanding"],
}


def validate_transition(
    current_state: str,
    next_state: str,
) -> None:
    """
    Validate state transition is allowed.

    Args:
        current_state: Current conversation state
        next_state: Target conversation state

    Raises:
        ValidationError: If transition is not valid
    """
    valid_next_states = VALID_TRANSITIONS.get(current_state, [])

    if next_state not in valid_next_states:
        raise ValidationError(
            f"Invalid state transition: {current_state} → {next_state}",
            current=current_state,
            next=next_state,
            valid_transitions=valid_next_states,
        )


def validate_state_consistency(state: DialogueState) -> None:
    """
    Validate state internal consistency.

    Args:
        state: Dialogue state to validate

    Raises:
        ValidationError: If state is inconsistent
    """
    # Check flow_stack consistency
    active_flow_ids = {ctx["flow_id"] for ctx in state["flow_stack"]}
    slot_flow_ids = set(state["flow_slots"].keys())

    # All active flows must have slots
    missing_slots = active_flow_ids - slot_flow_ids
    if missing_slots:
        raise ValidationError(
            "Active flows missing slot storage",
            missing=list(missing_slots),
        )

    # Check waiting_for_slot requires active flow
    if state["waiting_for_slot"] and not state["flow_stack"]:
        raise ValidationError(
            "Cannot wait for slot without active flow",
            slot=state["waiting_for_slot"],
        )

    # Check conversation_state consistency
    if state["conversation_state"] == "waiting_for_slot":
        if not state["waiting_for_slot"]:
            raise ValidationError("State is waiting_for_slot but waiting_for_slot is None")
