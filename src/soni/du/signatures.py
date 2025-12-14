"""DSPy signatures for Dialogue Understanding.

For detailed developer documentation of data structures used in these signatures,
see DATA_STRUCTURES.md in this directory.

Note: Signature class docstrings are sent to the LLM and must be self-contained.
      DATA_STRUCTURES.md is for developer reference only.
"""

import dspy

from soni.du.models import DialogueContext, NLUOutput


class DialogueUnderstanding(dspy.Signature):
    """Analyze user messages in dialogue context to determine intent and extract slot values.

    Classify the user's message into one of the following types based on context:
    - SLOT_VALUE: User provides a value for an expected slot
    - CONFIRMATION: User confirms or denies (yes/no response to confirmation prompt)
    - CORRECTION: User corrects a previously provided slot value
    - MODIFICATION: User requests to change a slot value
    - INTERRUPTION: User wants to start/switch to a flow in available_flows
    - CANCELLATION: User abandons the current flow
    - DIGRESSION: General question not related to any available flow
    - CLARIFICATION: User asks for clarification about the current request
    - CONTINUATION: User continues without clear intent

    Key rules:
    1. Match user message semantically to available_flows descriptions, not just exact words
    2. If message matches a flow, use INTERRUPTION with that flow as command
    3. Use DIGRESSION only when message doesn't match ANY available flow
    4. Extract slot values mentioned in the message with appropriate action type

    Extract slots with actions: provide (new), correct (reactive fix), modify (proactive change).
    """

    # Input fields with structured types
    user_message: str = dspy.InputField(desc="User's input message to analyze")
    history: dspy.History = dspy.InputField(
        desc="Conversation history (list of {role, content} messages)"
    )
    context: DialogueContext = dspy.InputField(
        desc="Current dialogue state including flow, slots, and conversation phase"
    )
    current_datetime: str = dspy.InputField(
        desc="Current datetime (ISO format) for temporal expressions",
        default="",
    )

    # Output field with structured type
    result: NLUOutput = dspy.OutputField(
        desc="Classified message with type, intent, slots, and confidence"
    )
