"""Flight booking domain configuration and example data.

This module defines the flight booking domain used for generating
training examples across all conversational patterns.
"""

import dspy

from soni.dataset.base import ConversationContext, DomainConfig

# Domain configuration
FLIGHT_BOOKING = DomainConfig(
    name="flight_booking",
    description="Book flights between cities with departure and return dates",
    available_flows=[
        "book_flight",
        "search_flights",
        "check_booking",
        "modify_booking",
        "cancel_booking",
    ],
    available_actions=[
        "search_flights",
        "book_flight",
        "modify_booking",
        "cancel_booking",
        "send_confirmation",
    ],
    flow_descriptions={
        "book_flight": "Book flights between cities with departure and return dates",
        "search_flights": "Search for available flights and compare prices",
        "check_booking": "Check the status of an existing booking",
        "modify_booking": "Modify an existing flight booking",
        "cancel_booking": "Cancel a flight booking",
    },
    slots={
        "origin": "city",
        "destination": "city",
        "departure_date": "date",
        "return_date": "date",
        "passengers": "number",
        "cabin_class": "string",
    },
    slot_prompts={
        "origin": "Which city are you departing from?",
        "destination": "Where would you like to fly to?",
        "departure_date": "When would you like to depart?",
        "return_date": "When would you like to return?",
        "passengers": "How many passengers will be traveling?",
        "cabin_class": "Which cabin class would you prefer? (economy, business, or first class)",
    },
)

# Example data for generating varied examples
CITIES = [
    "Madrid",
    "Barcelona",
    "Paris",
    "London",
    "New York",
    "Los Angeles",
    "Tokyo",
    "Rome",
    "Berlin",
    "Amsterdam",
]

DATES_RELATIVE = [
    "tomorrow",
    "Tomorrow",  # Variant with capital
    "next Monday",
    "Next Monday",  # Variant with capital
    "next Friday",
    "Next Friday",  # Used in test
    "next week",
    "Next week",  # Variant with capital
    "in two weeks",
    "next month",
    "the day after tomorrow",
    "in 3 days",
    "this Friday",
    "This Friday",
]

DATES_SPECIFIC = [
    "December 15th",
    "January 10th",
    "March 25th",
    "June 1st",
]

CABIN_CLASSES = [
    "economy",
    "business",
    "first class",
]

# Common passenger counts
PASSENGER_COUNTS = [1, 2, 3, 4]

# Utterance variations for different intents
BOOKING_UTTERANCES = [
    "I want to book a flight",
    "Book a flight",
    "I need to book a ticket",
    "Can you help me book a flight",
    "I'd like to make a flight reservation",
]

SEARCH_UTTERANCES = [
    "Search for flights",
    "Find flights",
    "Show me flights",
    "Can you search for available flights",
    "I want to see flight options",
]

CANCELLATION_UTTERANCES = [
    "Cancel",
    "Never mind",
    "Forget it",
    "I changed my mind",
    "Stop",
    "Cancel everything",
    "Actually, cancel this",
    "Actually, cancel",
    "Cancel this",
    "I want to cancel",
    "I'd like to cancel",
    "Please cancel",
]

CONFIRMATION_POSITIVE = [
    "Yes",
    "Correct",
    "That's right",
    "Yes, that looks good",
    "Confirmed",
    "Yeah",
]

CONFIRMATION_NEGATIVE = [
    # Simple negation - should be message_type=CONFIRMATION, confirmation_value=False
    "No",
    "That's wrong",
    "No, that's not right",
    "Incorrect",
    "Nope",
    "No way",
    "That's incorrect",
]

# IMPORTANT: These should generate message_type=MODIFICATION, not CONFIRMATION
# The user is denying AND requesting a change in the same message
CONFIRMATION_WITH_MODIFICATION = [
    # (user_message, target_slot) tuples
    ("No, change the destination", "destination"),
    ("No, change the origin", "origin"),
    ("No, I want to change the date", "departure_date"),
    ("No, let me change the destination", "destination"),
    ("No, I need to modify the origin", "origin"),
    ("Change the destination please", "destination"),
    ("Actually, change the date", "departure_date"),
]

CONFIRMATION_UNCLEAR = [
    "hmm, I'm not sure",
    "maybe",
    "hmm",
    "I don't know",
    "I'm not sure",
    "Let me think",
    "Not really sure",
    "I guess so",
    "Perhaps",
    "Kind of",
    # Additional ambiguous responses
    "Maybe",  # Capital variant
    "I'm thinking",
    "Can you repeat that?",
    "What were the details again?",
    "um...",
    "uh...",
    "well...",
]


def create_empty_flight_context() -> ConversationContext:
    """Create context for new flight booking conversation (no history).

    Returns:
        ConversationContext with empty history and no filled slots
    """
    return ConversationContext(
        history=dspy.History(messages=[]),
        current_slots={},
        current_flow="none",
        expected_slots=["origin", "destination", "departure_date"],
    )


def create_context_after_origin(origin: str = "Madrid") -> ConversationContext:
    """Create context after user provided origin.

    Args:
        origin: Origin city (default: "Madrid")

    Returns:
        ConversationContext with origin filled, asking for destination
    """
    return ConversationContext(
        history=dspy.History(
            messages=[
                {
                    "user_message": "I want to book a flight",
                    "result": {
                        "command": "book_flight",
                        "message_type": "interruption",
                    },
                },
                {
                    "user_message": f"From {origin}",
                    "result": {
                        "command": "book_flight",
                        "message_type": "slot_value",
                        "slots": [{"name": "origin", "value": origin}],
                    },
                },
            ]
        ),
        current_slots={"origin": origin},
        current_flow="book_flight",
        expected_slots=["destination", "departure_date"],
    )


def create_context_after_origin_destination(
    origin: str = "Madrid",
    destination: str = "Barcelona",
) -> ConversationContext:
    """Create context after user provided origin and destination.

    Args:
        origin: Origin city (default: "Madrid")
        destination: Destination city (default: "Barcelona")

    Returns:
        ConversationContext with origin and destination filled
    """
    return ConversationContext(
        history=dspy.History(
            messages=[
                {
                    "user_message": "I want to book a flight",
                    "result": {"command": "book_flight", "message_type": "interruption"},
                },
                {
                    "user_message": f"From {origin} to {destination}",
                    "result": {
                        "command": "book_flight",
                        "message_type": "slot_value",
                        "slots": [
                            {"name": "origin", "value": origin},
                            {"name": "destination", "value": destination},
                        ],
                    },
                },
            ]
        ),
        current_slots={"origin": origin, "destination": destination},
        current_flow="book_flight",
        expected_slots=["departure_date"],
    )


def create_context_before_confirmation(
    origin: str = "Madrid",
    destination: str = "Barcelona",
    departure_date: str = "tomorrow",
) -> ConversationContext:
    """Create context right before confirmation step.

    All required slots filled, ready for confirmation.
    conversation_state is set to 'confirming' so NLU knows user is responding
    to a confirmation prompt.

    Args:
        origin: Origin city
        destination: Destination city
        departure_date: Departure date

    Returns:
        ConversationContext with all main slots filled and state='confirming'
    """
    return ConversationContext(
        history=dspy.History(
            messages=[
                {
                    "user_message": f"Book a flight from {origin} to {destination} {departure_date}",
                    "result": {
                        "command": "book_flight",
                        "message_type": "interruption",
                        "slots": [
                            {"name": "origin", "value": origin},
                            {"name": "destination", "value": destination},
                            {"name": "departure_date", "value": departure_date},
                        ],
                    },
                },
            ]
        ),
        current_slots={
            "origin": origin,
            "destination": destination,
            "departure_date": departure_date,
        },
        current_flow="book_flight",
        expected_slots=[],  # All required slots filled
        conversation_state="ready_for_confirmation",  # CRITICAL: indicates confirmation phase
    )
