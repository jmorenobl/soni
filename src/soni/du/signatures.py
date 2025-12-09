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
    """

    # Input fields with structured types
    user_message: str = dspy.InputField(desc="The user's message to analyze")
    history: dspy.History = dspy.InputField(desc="Conversation history")
    context: DialogueContext = dspy.InputField(
        desc="Dialogue state: current_flow, expected_slots (use these EXACT names), "
        "current_slots (already filled - check for corrections), current_prompted_slot, "
        "available_flows (dict mapping flow names to descriptions - use descriptions to map user intent)"
    )
    current_datetime: str = dspy.InputField(
        desc="Current datetime in ISO format for relative date resolution",
        default="",
    )

    # Output field with structured type
    result: NLUOutput = dspy.OutputField(
        desc="NLU analysis with message_type, optional command, and extracted slots"
    )
