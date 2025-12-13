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

    CRITICAL: Mapping user messages to flows when current_flow="none":
    - When current_flow="none" and available_flows is not empty, you MUST check if the user message
      matches any flow description semantically
    - Match user intent to flow descriptions: "I want to book a flight" matches "Book a flight from origin to destination"
    - If there's a semantic match, classify as INTERRUPTION and set command to the matching flow name
    - Flow names are the keys in available_flows (e.g., "book_flight", "cancel_booking")
    - Do NOT use CONTINUATION when user clearly wants to start a flow from available_flows

    Examples of correct mapping:
    - User: "I want to book a flight" + available_flows={"book_flight": "Book a flight from origin to destination"}
      → INTERRUPTION, command="book_flight"
    - User: "Book a hotel" + available_flows={"book_hotel": "Book a hotel room"}
      → INTERRUPTION, command="book_hotel"
    - User: "I need to cancel" + available_flows={"cancel_booking": "Cancel an existing booking"}
      → INTERRUPTION, command="cancel_booking"

    Classify message type and extract information based on context and available flows/actions.

    Key distinctions:

    DIGRESSION vs CLARIFICATION:
    - DIGRESSION: General question not about current step (e.g., "What destinations do you fly to?")
    - CLARIFICATION: Question about why current step needs information (e.g., "Why do you need my email?")

    MODIFICATION vs SLOT_VALUE:
    - MODIFICATION: User explicitly requests to change existing slot (e.g., "Can I change destination to London?")
      * Slot already in current_slots
      * User uses request phrases: "change", "modify", "update", "can I change"
    - SLOT_VALUE: User provides value directly (e.g., "London" when asked for destination)
      * Direct answer to current prompt
      * No request language, just provides value

    CANCELLATION vs INTERRUPTION:
    - CANCELLATION: User abandons current flow, no new flow in available_flows
    - INTERRUPTION: User wants to start a flow that exists in available_flows
      * When current_flow="none" and user mentions a flow from available_flows → INTERRUPTION
      * When current_flow exists and user wants to switch to different flow → INTERRUPTION
      * Set command to the flow name from available_flows (e.g., "book_flight")
      * Examples: "I want to book a flight" → INTERRUPTION, command="book_flight"
                 "Book a hotel" → INTERRUPTION, command="book_hotel" (if in available_flows)

    CONFIRMATION vs CORRECTION vs MODIFICATION (when conversation_state="confirming" or "ready_for_confirmation"):
    - CONFIRMATION: Generic yes/no response to confirmation prompt
      * When conversation_state="confirming" or "ready_for_confirmation", simple yes/no responses are CONFIRMATION
      * "Yes", "No", "That's correct", "That's not right" → CONFIRMATION
      * Set confirmation_value=True/False based on response
      * Do NOT use CORRECTION unless user provides a specific corrected value
    - CORRECTION: User specifies which value is wrong AND provides correct value
      * "No, I meant Barcelona" (mentions specific value + provides correction) → CORRECTION
      * "The date should be December 20th" (provides corrected value) → CORRECTION
      * "No" alone → CONFIRMATION (not CORRECTION, no value provided)
    - MODIFICATION: User says "no" AND requests to change a slot (with or without new value)
      * "No, change the destination" → MODIFICATION (user wants to change, asks for new value)
      * "No, change the date to tomorrow" → MODIFICATION with slot value
      * "No, I want to change the origin" → MODIFICATION
      * KEY: If user says "no" + asks to "change/modify/update" something → MODIFICATION, NOT CONFIRMATION!

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
