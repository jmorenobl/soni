"""Constants and enums for the Soni framework.

This module centralizes all string constants used throughout the framework
to provide type safety, IDE autocompletion, and prevent typo bugs.

DM-002: Eliminate Magic Strings with Enums

Usage:
    from soni.core.constants import ConversationState, NodeName, MessageType

    if state == ConversationState.CONFIRMING:
        return NodeName.HANDLE_CONFIRMATION
"""

from enum import StrEnum

# Re-export MessageType from du.models for centralized access
# This allows importing all enums from one place
from soni.du.models import MessageType

__all__ = ["ConversationState", "NodeName", "MessageType"]


class ConversationState(StrEnum):
    """Valid conversation states for the dialogue manager.

    These states track where we are in the dialogue flow lifecycle.
    Using StrEnum allows direct comparison with strings while providing
    type safety and IDE support.

    Examples:
        >>> state = ConversationState.CONFIRMING
        >>> state == "confirming"  # Works due to StrEnum
        True
        >>> state.value
        'confirming'
    """

    IDLE = "idle"
    """No active flow, waiting for user to initiate."""

    UNDERSTANDING = "understanding"
    """Processing user message through NLU."""

    WAITING_FOR_SLOT = "waiting_for_slot"
    """Waiting for user to provide a slot value."""

    READY_FOR_CONFIRMATION = "ready_for_confirmation"
    """All slots filled, ready to ask for confirmation."""

    CONFIRMING = "confirming"
    """Asked for confirmation, waiting for user response."""

    READY_FOR_ACTION = "ready_for_action"
    """Confirmation received, ready to execute action."""

    GENERATING_RESPONSE = "generating_response"
    """Generating a response message for the user."""

    COMPLETED = "completed"
    """Flow has completed successfully."""

    ERROR = "error"
    """An error occurred in the dialogue flow."""


class NodeName(StrEnum):
    """Valid node names in the dialogue graph.

    These are the routing targets used by the dialogue manager
    to determine which node to execute next in the graph.

    Examples:
        >>> target = NodeName.EXECUTE_ACTION
        >>> target == "execute_action"  # Works due to StrEnum
        True
    """

    UNDERSTAND = "understand"
    """NLU processing node."""

    VALIDATE_SLOT = "validate_slot"
    """Slot validation node."""

    COLLECT_NEXT_SLOT = "collect_next_slot"
    """Prompt for next required slot."""

    CONFIRM_ACTION = "confirm_action"
    """Display confirmation message to user."""

    EXECUTE_ACTION = "execute_action"
    """Execute the flow's action."""

    GENERATE_RESPONSE = "generate_response"
    """Generate response message."""

    HANDLE_DIGRESSION = "handle_digression"
    """Handle user digression/question."""

    HANDLE_CORRECTION = "handle_correction"
    """Handle slot value correction."""

    HANDLE_MODIFICATION = "handle_modification"
    """Handle slot value modification."""

    HANDLE_CONFIRMATION = "handle_confirmation"
    """Handle confirmation response."""

    HANDLE_INTENT_CHANGE = "handle_intent_change"
    """Handle intent/flow change."""

    HANDLE_CLARIFICATION = "handle_clarification"
    """Handle clarification request."""

    HANDLE_CANCELLATION = "handle_cancellation"
    """Handle flow cancellation."""
