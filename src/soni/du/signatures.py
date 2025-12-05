"""DSPy signatures for Dialogue Understanding."""

import dspy

from soni.du.models import DialogueContext, NLUOutput


class DialogueUnderstanding(dspy.Signature):
    """Analyze user message to extract intent and slot values.

    COMMAND RULES (CRITICAL):
    - To start a flow from available_flows, return command='<flow_name>' (e.g., 'book_flight')
    - The command MUST be one of context.available_flows when triggering a new flow
    - For slot values within a flow, use message_type='slot_value' and command='provide_slot'

    SLOT EXTRACTION RULES:
    1. ALWAYS extract ALL slot values mentioned in the user message.
    2. Slot names MUST be from context.expected_slots - use those EXACT names.
    3. When user says "from X to Y", extract BOTH origin=X and destination=Y.
    4. When user provides a value for context.current_prompted_slot, use that exact slot name.

    MESSAGE TYPE RULES:
    - interruption: User wants to start a NEW flow -> command must be a flow name from available_flows
    - slot_value: User provides slot information within current flow
    - digression: User asks a question without changing flow
    - cancellation: User wants to stop/cancel
    """

    # Input fields with structured types
    user_message: str = dspy.InputField(desc="The user's current message to analyze")
    history: dspy.History = dspy.InputField(
        desc="Conversation history with user messages and assistant responses"
    )
    context: DialogueContext = dspy.InputField(
        desc="Dialogue context containing: current_flow, expected_slots (USE THESE EXACT NAMES), "
        "current_prompted_slot (slot being asked for), current_slots (already filled), "
        "available_flows (flows user can trigger)"
    )
    current_datetime: str = dspy.InputField(
        desc="Current datetime in ISO format for relative date resolution",
        default="",
    )

    # Output field with structured type
    result: NLUOutput = dspy.OutputField(
        desc="NLU analysis with slots using ONLY names from context.expected_slots"
    )
