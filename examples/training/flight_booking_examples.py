"""Training examples for flight booking domain using structured types."""

import dspy

from soni.du.models import DialogueContext, MessageType, NLUOutput, SlotValue


def create_flight_booking_examples() -> list[dspy.Example]:
    """Create training examples for flight booking domain.

    Returns:
        List of dspy.Example objects with structured inputs and outputs
    """
    examples = []

    # Example 1: Intent detection
    examples.append(
        dspy.Example(
            user_message="I want to book a flight",
            history=dspy.History(messages=[]),
            context=DialogueContext(
                current_slots={},
                available_actions=["book_flight", "search_flights"],
                available_flows=["book_flight"],
                current_flow="none",
                expected_slots=["origin", "destination", "departure_date"],
            ),
            current_datetime="2024-12-02T10:00:00",
            result=NLUOutput(
                message_type=MessageType.INTERRUPTION,
                command="book_flight",
                slots=[],
                confidence=0.95,
                reasoning="User explicitly states intent to book a flight",
            ),
        ).with_inputs("user_message", "history", "context", "current_datetime")
    )

    # Example 2: Slot extraction
    examples.append(
        dspy.Example(
            user_message="From Madrid to Barcelona",
            history=dspy.History(
                messages=[
                    {
                        "role": "user",
                        "content": "I want to book a flight",
                    },
                    {
                        "role": "assistant",
                        "content": "Where are you departing from?",
                    },
                ]
            ),
            context=DialogueContext(
                current_slots={},
                available_actions=["book_flight"],
                available_flows=["book_flight"],
                current_flow="book_flight",
                expected_slots=["origin", "destination", "departure_date"],
            ),
            current_datetime="2024-12-02T10:00:00",
            result=NLUOutput(
                message_type=MessageType.SLOT_VALUE,
                command="book_flight",
                slots=[
                    SlotValue(name="origin", value="Madrid", confidence=0.9),
                    SlotValue(name="destination", value="Barcelona", confidence=0.9),
                ],
                confidence=0.9,
                reasoning="User provides origin and destination when expected",
            ),
        ).with_inputs("user_message", "history", "context", "current_datetime")
    )

    # Example 3: Correction
    examples.append(
        dspy.Example(
            user_message="Actually, make it Paris instead",
            history=dspy.History(
                messages=[
                    {
                        "role": "user",
                        "content": "I want to go to Barcelona",
                    },
                    {
                        "role": "assistant",
                        "content": "Got it, Barcelona. When would you like to travel?",
                    },
                ]
            ),
            context=DialogueContext(
                current_slots={"destination": "Barcelona"},
                available_actions=["book_flight"],
                available_flows=["book_flight"],
                current_flow="book_flight",
                expected_slots=["departure_date"],
            ),
            current_datetime="2024-12-02T10:00:00",
            result=NLUOutput(
                message_type=MessageType.CORRECTION,
                command="book_flight",
                slots=[
                    SlotValue(name="destination", value="Paris", confidence=0.95),
                ],
                confidence=0.95,
                reasoning="User corrects previous destination value",
            ),
        ).with_inputs("user_message", "history", "context", "current_datetime")
    )

    # Example 4: Modification request
    examples.append(
        dspy.Example(
            user_message="Can I change the departure date?",
            history=dspy.History(
                messages=[
                    {
                        "role": "user",
                        "content": "I want to book a flight from Madrid to Paris on 2024-12-15",
                    },
                    {
                        "role": "assistant",
                        "content": "Flight booked for December 15th. Anything else?",
                    },
                ]
            ),
            context=DialogueContext(
                current_slots={
                    "origin": "Madrid",
                    "destination": "Paris",
                    "departure_date": "2024-12-15",
                },
                available_actions=["book_flight", "modify_booking"],
                available_flows=["book_flight"],
                current_flow="book_flight",
                expected_slots=["departure_date"],
            ),
            current_datetime="2024-12-02T10:00:00",
            result=NLUOutput(
                message_type=MessageType.MODIFICATION,
                command="modify_booking",
                slots=[],
                confidence=0.9,
                reasoning="User requests to modify existing booking",
            ),
        ).with_inputs("user_message", "history", "context", "current_datetime")
    )

    return examples
