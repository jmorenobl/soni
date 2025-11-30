"""DSPy signatures for Dialogue Understanding."""

import dspy


class DialogueUnderstanding(dspy.Signature):
    """Extract user intent and entities from message with dialogue context.

    This signature defines the input-output structure for the NLU module
    that will be optimized using DSPy's MIPROv2 optimizer.
    """

    # Input fields
    user_message = dspy.InputField(desc="The user's current message")
    dialogue_history = dspy.InputField(desc="Previous conversation context as a string", default="")
    current_slots = dspy.InputField(desc="Currently filled slots as a JSON string", default="{}")
    available_actions = dspy.InputField(
        desc="List of available actions in current context as JSON array string",
        default="[]",
    )
    current_flow = dspy.InputField(desc="Current dialogue flow name", default="none")
    expected_slots = dspy.InputField(
        desc=(
            "List of expected slot names for the current flow as JSON array string. "
            "You MUST use these exact slot names when extracting entities. "
            'Example: \'["origin", "destination", "departure_date"]\''
        ),
        default="[]",
    )

    # Output fields
    structured_command = dspy.OutputField(
        desc="User's intent/command (e.g., book_flight, cancel, help, search_flights)"
    )
    extracted_slots = dspy.OutputField(
        desc=(
            "Extracted entities as a JSON string using EXACT slot names from expected_slots. "
            "Use the exact slot names provided in expected_slots, not variations. "
            'Example: {"origin": "Madrid", "destination": "Barcelona", "departure_date": "2024-03-15"}'
        )
    )
    confidence = dspy.OutputField(desc="Confidence score between 0.0 and 1.0")
    reasoning = dspy.OutputField(desc="Brief reasoning for the extraction")
