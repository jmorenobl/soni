"""DSPy signatures for Dialogue Understanding."""

import dspy

from soni.du.models import DialogueContext, NLUOutput


class DialogueUnderstanding(dspy.Signature):
    """Analyze user message in dialogue context to determine intent and extract all slot values.

    Extract ALL slot values mentioned in the message. Each slot gets an action
    (provide/correct/modify) based on whether it's new or changing an existing value.
    """

    # Input fields with structured types
    user_message: str = dspy.InputField(desc="The user's message to analyze")
    history: dspy.History = dspy.InputField(desc="Conversation history")
    context: DialogueContext = dspy.InputField(
        desc="Dialogue state: current_flow, expected_slots (use these EXACT names), "
        "current_slots (already filled - check for corrections), current_prompted_slot, available_flows"
    )
    current_datetime: str = dspy.InputField(
        desc="Current datetime in ISO format for relative date resolution",
        default="",
    )

    # Output field with structured type
    result: NLUOutput = dspy.OutputField(
        desc="Analysis with message_type, command, and all extracted slots (list) with their actions"
    )
