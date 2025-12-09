"""DSPy signatures for Dialogue Understanding."""

import dspy

from soni.du.models import DialogueContext, NLUOutput


class DialogueUnderstanding(dspy.Signature):
    """Analyze user message in dialogue context to determine intent and extract all slot values.

    Extract ALL slot values mentioned in the message. Each slot gets an action
    (provide/correct/modify) based on whether it's new or changing an existing value.

    When available_flows contains flow descriptions, map user intent to the appropriate
    flow name based on semantic matching. For example, if available_flows contains
    {"book_flight": "Book a flight from origin to destination"}, and the user says
    "I want to book a flight", set command="book_flight".

    CRITICAL: Use context.conversation_state to determine message_type:
    - If context.conversation_state is "confirming" or "ready_for_confirmation":
      * The user is responding to a confirmation request
      * Set message_type to CONFIRMATION (not SLOT_VALUE, even if the message contains slot-like words)
      * Extract confirmation_value: True if user confirms (yes/correct/confirm/that's right/okay)
      * Extract confirmation_value: False if user denies (no/wrong/incorrect/not right/change/modify)
        ** CRITICAL: If user says "No" or "change" or "modify" during confirmation,
           set confirmation_value=False. Even if the message contains words like "change destination",
           the confirmation_value should be False. The modification request will be handled separately.
      * Extract confirmation_value: None if unclear or ambiguous
      * Set command to None (simple yes/no response, not a new intent)
      * Exception: If user is changing intent while responding (e.g., "No, I want to cancel"),
        then set command to the new intent (e.g., "cancel") and message_type to INTERRUPTION

    - If context.conversation_state is "waiting_for_slot" or context.current_prompted_slot is set:
      * The user is responding to a slot collection prompt
      * Set message_type to SLOT_VALUE and extract the slot value
      * Use context.expected_slots to identify which slot is being filled

    - Otherwise:
      * Determine message_type based on message content and context
    """

    # Input fields with structured types
    user_message: str = dspy.InputField(desc="The user's message to analyze")
    history: dspy.History = dspy.InputField(desc="Conversation history")
    context: DialogueContext = dspy.InputField(
        desc="Dialogue state: current_flow, expected_slots (use these EXACT names), "
        "current_slots (already filled - check for corrections), current_prompted_slot, "
        "conversation_state (CRITICAL: use this to determine if user is responding to confirmation), "
        "available_flows (dict mapping flow names to descriptions - use descriptions to map user intent). "
        "IMPORTANT: If conversation_state is 'confirming' or 'ready_for_confirmation', "
        "the user is responding to a confirmation request - set message_type to CONFIRMATION."
    )
    current_datetime: str = dspy.InputField(
        desc="Current datetime in ISO format for relative date resolution",
        default="",
    )

    # Output field with structured type
    result: NLUOutput = dspy.OutputField(
        desc="NLU analysis with message_type, optional command, and extracted slots"
    )
