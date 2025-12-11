"""Restaurant reservation domain configuration and example data."""

import dspy

from soni.dataset.base import ConversationContext, DomainConfig

# Domain configuration
RESTAURANT = DomainConfig(
    name="restaurant",
    description="Make restaurant reservations",
    available_flows=[
        "book_table",
        "search_restaurants",
        "check_reservation",
        "modify_reservation",
        "cancel_reservation",
    ],
    available_actions=[
        "search_restaurants",
        "book_table",
        "modify_reservation",
        "cancel_reservation",
        "send_confirmation",
    ],
    slots={
        "location": "city",
        "date": "date",
        "time": "time",
        "party_size": "number",
        "cuisine": "string",
    },
    slot_prompts={
        "location": "Which city are you looking for a restaurant in?",
        "date": "What date would you like to dine?",
        "time": "What time would you prefer?",
        "party_size": "How many people will be dining?",
        "cuisine": "What type of cuisine would you like?",
    },
)

# Example data
CITIES = [
    "Madrid",
    "Barcelona",
    "Paris",
    "London",
    "New York",
    "Tokyo",
]

CUISINES = [
    "Italian",
    "Japanese",
    "Spanish",
    "French",
    "Chinese",
    "Mexican",
]

TIMES = [
    "7:00 PM",
    "8:00 PM",
    "7:30 PM",
    "9:00 PM",
]

PARTY_SIZES = [2, 4, 6, 8]

BOOKING_UTTERANCES = [
    "I want to make a reservation",
    "Book a table",
    "I need a restaurant reservation",
    "Can you help me book a table",
]


def create_empty_restaurant_context() -> ConversationContext:
    """Create context for new restaurant reservation.

    Returns:
        ConversationContext with empty history and no filled slots
    """
    return ConversationContext(
        history=dspy.History(messages=[]),
        current_slots={},
        current_flow="none",
        expected_slots=["location", "date", "time", "party_size"],
    )


def create_context_after_location(location: str = "Madrid") -> ConversationContext:
    """Create context after user provided location.

    Args:
        location: Location city (default: "Madrid")

    Returns:
        ConversationContext with location filled, asking for date/time
    """
    return ConversationContext(
        history=dspy.History(
            messages=[
                {
                    "user_message": "I want to book a table",
                    "result": {"command": "book_table", "message_type": "interruption"},
                },
                {
                    "user_message": f"In {location}",
                    "result": {
                        "command": "book_table",
                        "message_type": "slot_value",
                        "slots": [{"name": "location", "value": location}],
                    },
                },
            ]
        ),
        current_slots={"location": location},
        current_flow="book_table",
        expected_slots=["date", "time", "party_size"],
    )
