"""Flight booking domain configuration and example data.

This module defines the flight booking domain used for generating
training examples across all conversational patterns.
"""

import dspy

from soni.dataset.base import ConversationContext, DomainConfig, DomainExampleData

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
    "Tomorrow",
    "next Monday",
    "Next Monday",
    "next Friday",
    "Next Friday",
    "next week",
    "Next week",
    "in two weeks",
    "next month",
    "the day after tomorrow",
    "in 3 days",
    "this Friday",
    "This Friday",
]

DATES_SPECIFIC = ["December 15th", "January 10th", "March 25th", "June 1st"]

CABIN_CLASSES = ["economy", "business", "first class"]

PASSENGER_COUNTS = ["1", "2", "3", "4"]

# Build DomainExampleData
_EXAMPLE_DATA = DomainExampleData(
    slot_values={
        "origin": CITIES,
        "destination": CITIES,
        "departure_date": DATES_RELATIVE + DATES_SPECIFIC,
        "return_date": DATES_RELATIVE + DATES_SPECIFIC,
        "passengers": PASSENGER_COUNTS,
        "cabin_class": CABIN_CLASSES,
    },
    utterance_templates={
        "slot_value": [
            "{value}",
            "It's {value}",
            "{value}, please",
        ],
        "correction": [
            "Actually, {new_value}",
            "No, {new_value}",
            "I meant {new_value}",
        ],
    },
    trigger_intents={
        "book_flight": [
            "I want to book a flight",
            "Book a flight",
            "I need to book a ticket",
            "Can you help me book a flight",
            "I'd like to make a flight reservation",
        ],
        "search_flights": [
            "Search for flights",
            "Find flights",
            "Show me flights",
            "Can you search for available flights",
            "I want to see flight options",
        ],
    },
    confirmation_positive=[
        "Yes",
        "Correct",
        "That's right",
        "Yes, that looks good",
        "Confirmed",
        "Yeah",
    ],
    confirmation_negative=[
        "No",
        "That's wrong",
        "No, that's not right",
        "Incorrect",
        "Nope",
        "No way",
    ],
    confirmation_unclear=[
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
        "Maybe",
        "I'm thinking",
        "Can you repeat that?",
        "um...",
        "uh...",
        "well...",
    ],
    # Multi-slot extraction examples for SlotExtractor optimization
    slot_extraction_cases=[
        # Origin + Destination
        (
            "From Madrid to Paris",
            [
                {"slot": "origin", "value": "Madrid"},
                {"slot": "destination", "value": "Paris"},
            ],
        ),
        (
            "New York to London",
            [
                {"slot": "origin", "value": "New York"},
                {"slot": "destination", "value": "London"},
            ],
        ),
        # Origin + Destination + Date
        (
            "Fly from Barcelona to Rome tomorrow",
            [
                {"slot": "origin", "value": "Barcelona"},
                {"slot": "destination", "value": "Rome"},
                {"slot": "departure_date", "value": "tomorrow"},
            ],
        ),
        (
            "Book a flight to Tokyo on December 15th",
            [
                {"slot": "destination", "value": "Tokyo"},
                {"slot": "departure_date", "value": "December 15th"},
            ],
        ),
        # Origin + Destination + Passengers + Class
        (
            "2 business class tickets from Berlin to Amsterdam",
            [
                {"slot": "passengers", "value": "2"},
                {"slot": "cabin_class", "value": "business"},
                {"slot": "origin", "value": "Berlin"},
                {"slot": "destination", "value": "Amsterdam"},
            ],
        ),
        # Negative examples
        ("I want to book a flight", []),
        ("Search for flights", []),
        ("What are the options?", []),
    ],
)

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
    example_data=_EXAMPLE_DATA,
)

# Legacy exports for backward-compatibility (deprecated - use example_data instead)
BOOKING_UTTERANCES = _EXAMPLE_DATA.trigger_intents.get("book_flight", [])
SEARCH_UTTERANCES = _EXAMPLE_DATA.trigger_intents.get("search_flights", [])
CONFIRMATION_POSITIVE = _EXAMPLE_DATA.confirmation_positive
CONFIRMATION_NEGATIVE = _EXAMPLE_DATA.confirmation_negative
CONFIRMATION_UNCLEAR = _EXAMPLE_DATA.confirmation_unclear

# Cancellation utterances (shared across domains)
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

# IMPORTANT: These should generate message_type=MODIFICATION, not CONFIRMATION
CONFIRMATION_WITH_MODIFICATION = [
    ("No, change the destination", "destination"),
    ("No, change the origin", "origin"),
    ("No, I want to change the date", "departure_date"),
    ("No, let me change the destination", "destination"),
    ("No, I need to modify the origin", "origin"),
    ("Change the destination please", "destination"),
    ("Actually, change the date", "departure_date"),
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
