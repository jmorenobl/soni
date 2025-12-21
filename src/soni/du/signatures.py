"""DSPy signatures for Dialogue Understanding.

Uses Pydantic types for structured I/O and rich descriptions to guide the LLM.
Based on the proven pattern from the current codebase.
"""

import dspy
from soni.du.models import DialogueContext, NLUOutput


class ExtractCommands(dspy.Signature):
    """Analyze user messages in dialogue context and generate executable commands.

    You are the "Understanding Layer" of a deterministic dialogue system.
    Your job is to translate the User's Message into a list of Commands.

    The available commands are provided in `context.available_commands`.
    Each command has:
    - command_type: The identifier to use
    - description: What it does
    - required_fields: Fields you must populate
    - example: Example user message

    RULES:
    1. ONLY use commands from context.available_commands
    2. If user provides a value and 'expected_slot' is set, generate set_slot
    3. If user corrects a value, check 'current_slots' and generate correct_slot
    4. If user asks to start a task, match against 'available_flows'
    5. If 'conversation_state' is 'confirming':
       - "Yes/Correct" -> affirm
       - "No/Wrong" -> deny (include slot_name if they specify what to change)
    6. Be explicit. Generate exactly the commands needed.
    """

    # Input fields with rich descriptions and Pydantic types
    user_message: str = dspy.InputField(desc="User's input message to analyze")
    context: DialogueContext = dspy.InputField(
        desc="Complete dialogue context including available_flows, available_commands, current_slots, expected_slot"
    )
    history: dspy.History = dspy.InputField(
        desc="Recent conversation history (list of {role, content} messages)"
    )

    # Output field with Pydantic type for structured validation
    result: NLUOutput = dspy.OutputField(desc="Extracted commands and reasoning")
