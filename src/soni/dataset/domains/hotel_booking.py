"""Hotel booking domain configuration and example data."""

import dspy

from soni.dataset.base import ConversationContext, DomainConfig

# Domain configuration
HOTEL_BOOKING = DomainConfig(
    name="hotel_booking",
    description="Book hotel rooms in different cities",
    available_flows=[
        "book_hotel",
        "search_hotels",
        "check_reservation",
        "modify_reservation",
        "cancel_reservation",
    ],
    available_actions=[
        "search_hotels",
        "book_hotel",
        "modify_reservation",
        "cancel_reservation",
        "send_confirmation",
    ],
    slots={
        "location": "city",
        "checkin_date": "date",
        "checkout_date": "date",
        "guests": "number",
        "room_type": "string",
    },
    slot_prompts={
        "location": "Which city would you like to stay in?",
        "checkin_date": "When would you like to check in?",
        "checkout_date": "When would you like to check out?",
        "guests": "How many guests will be staying?",
        "room_type": "What type of room would you prefer? (single, double, suite)",
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
    "Rome",
]

ROOM_TYPES = [
    "single",
    "double",
    "suite",
    "deluxe",
]

GUEST_COUNTS = [1, 2, 3, 4]

BOOKING_UTTERANCES = [
    "I want to book a hotel",
    "Book a hotel room",
    "I need a hotel reservation",
    "Can you help me book a hotel",
]


def create_empty_hotel_context() -> ConversationContext:
    """Create context for new hotel booking conversation."""
    return ConversationContext(
        history=dspy.History(messages=[]),
        current_slots={},
        current_flow="none",
        expected_slots=["location", "checkin_date", "checkout_date"],
    )


def create_context_after_location(location: str = "Barcelona") -> ConversationContext:
    """Create context after user provided location.

    Args:
        location: Location city (default: "Barcelona")

    Returns:
        ConversationContext with location filled, asking for dates
    """
    return ConversationContext(
        history=dspy.History(
            messages=[
                {
                    "user_message": "I want to book a hotel",
                    "result": {"command": "book_hotel", "message_type": "interruption"},
                },
                {
                    "user_message": f"In {location}",
                    "result": {
                        "command": "book_hotel",
                        "message_type": "slot_value",
                        "slots": [{"name": "location", "value": location}],
                    },
                },
            ]
        ),
        current_slots={"location": location},
        current_flow="book_hotel",
        expected_slots=["checkin_date", "checkout_date"],
    )
