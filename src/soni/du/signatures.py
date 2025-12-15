"""DSPy signatures for Dialogue Understanding (v2.0 Command-Driven).

This signature replaces the legacy MessageType classification with explicit
Command generation. The LLM is responsible for mapping user intent + context
directly to an executable Command sequence.
"""

import dspy

from soni.du.models import DialogueContext, NLUOutput


class DialogueUnderstanding(dspy.Signature):
    """Analyze user messages in dialogue context and generate executable commands.

    You are the "Understanding Layer" of a deterministic dialogue system.
    Your job is to translate the User's Message into a list of explicit Commands
    based on the current Context.

    AVAILABLE COMMANDS:
    - StartFlow(flow_name, slots): User wants to start a specific flow (e.g. "book flight").
    - SetSlot(slot_name, value): User provides a value for a slot.
    - CorrectSlot(slot_name, new_value): User corrects a previously set slot.
    - CancelFlow(reason): User wants to stop the current flow.
    - Clarify(topic): User doesn't understand and asks a question about the prompt.
    - AffirmConfirmation(): User says "yes" to a confirmation prompt.
    - DenyConfirmation(slot_to_change): User says "no" to a confirmation prompt.
    - HumanHandoff(reason): User asks for a human agent.
    - OutOfScope(topic): User asks something the bot cannot handle.
    - ChitChat(response_hint): Casual conversation.

    RULES:
    1. If a user provides a value for a slot in 'expected_slots', generate SetSlot.
    2. If a user corrects a value, generate CorrectSlot (check 'current_slots').
    3. If a user asks to start a task in 'available_flows', generate StartFlow.
    4. If 'conversation_state' is 'confirming':
       - "Yes/Correct" -> AffirmConfirmation
       - "No/Wrong" -> DenyConfirmation
    5. Be explicit. Generate the exact commands needed to handle the user's request.
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
    result: NLUOutput = dspy.OutputField(desc="List of executable Commands and raw entities")
