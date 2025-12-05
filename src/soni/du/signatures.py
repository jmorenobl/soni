"""DSPy signatures for Dialogue Understanding."""

import dspy

from soni.du.models import DialogueContext, NLUOutput


class DialogueUnderstanding(dspy.Signature):
    """Extract user intent and entities with structured types.

    Uses Pydantic models for robust type safety and validation.
    Uses dspy.History for proper conversation history management.
    """

    # Input fields with structured types
    user_message: str = dspy.InputField(desc="The user's current message")
    history: dspy.History = dspy.InputField(
        desc="Conversation history with user messages and assistant responses"
    )
    context: DialogueContext = dspy.InputField(
        desc="Current dialogue context with all relevant information"
    )
    current_datetime: str = dspy.InputField(
        desc="Current datetime in ISO format for relative date resolution",
        default="",
    )

    # Output field with structured type
    result: NLUOutput = dspy.OutputField(desc="Complete NLU analysis with type-safe structure")
