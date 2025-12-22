"""Hotel booking domain configuration and example data."""

import dspy

from soni.dataset.base import ConversationContext, DomainConfig, DomainExampleData

# Example data constants
CITIES = ["Madrid", "Barcelona", "Paris", "London", "New York", "Tokyo", "Rome"]
ROOM_TYPES = ["single", "double", "suite", "deluxe"]
GUEST_COUNTS = ["1", "2", "3", "4"]

# Build DomainExampleData
_EXAMPLE_DATA = DomainExampleData(
    slot_values={
        "location": CITIES,
        "checkin_date": ["tomorrow", "next Monday", "December 15th"],
        "checkout_date": ["next Friday", "December 20th", "in a week"],
        "guests": GUEST_COUNTS,
        "room_type": ROOM_TYPES,
    },
    trigger_intents={
        "book_hotel": [
            "I want to book a hotel",
            "Book a hotel room",
            "I need a hotel reservation",
            "Can you help me book a hotel",
        ],
    },
    confirmation_positive=["Yes", "Correct", "That's right", "Confirmed", "Yeah", "Perfect"],
    confirmation_negative=["No", "That's wrong", "No, that's not right", "Incorrect", "Nope"],
    confirmation_unclear=["hmm, I'm not sure", "maybe", "I don't know", "Let me think", "um..."],
    # Multi-slot extraction examples for SlotExtractor optimization
    slot_extraction_cases=[
        # Location + Dates
        (
            "Hotel in Paris from December 15th to December 20th",
            [
                {"slot": "location", "value": "Paris"},
                {"slot": "checkin_date", "value": "December 15th"},
                {"slot": "checkout_date", "value": "December 20th"},
            ],
        ),
        (
            "Book a room in London tomorrow",
            [
                {"slot": "location", "value": "London"},
                {"slot": "checkin_date", "value": "tomorrow"},
            ],
        ),
        # Location + Room Type + Guests
        (
            "Suite for 2 guests in Tokyo",
            [
                {"slot": "room_type", "value": "suite"},
                {"slot": "guests", "value": "2"},
                {"slot": "location", "value": "Tokyo"},
            ],
        ),
        (
            "Double room in Barcelona next Monday",
            [
                {"slot": "room_type", "value": "double"},
                {"slot": "location", "value": "Barcelona"},
                {"slot": "checkin_date", "value": "next Monday"},
            ],
        ),
        # Negative examples
        ("I need a hotel reservation", []),
        ("Show me available hotels", []),
    ],
)

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
    flow_descriptions={
        "book_hotel": "Book hotel rooms in different cities",
        "search_hotels": "Search for available hotels and compare options",
        "check_reservation": "Check the status of an existing reservation",
        "modify_reservation": "Modify an existing hotel reservation",
        "cancel_reservation": "Cancel a hotel reservation",
    },
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
    example_data=_EXAMPLE_DATA,
)

# Legacy exports for backward-compatibility
BOOKING_UTTERANCES = _EXAMPLE_DATA.trigger_intents.get("book_hotel", [])
CONFIRMATION_POSITIVE = _EXAMPLE_DATA.confirmation_positive
CONFIRMATION_NEGATIVE = _EXAMPLE_DATA.confirmation_negative
CONFIRMATION_UNCLEAR = _EXAMPLE_DATA.confirmation_unclear

CANCELLATION_UTTERANCES = ["Cancel", "Never mind", "Forget it", "I changed my mind", "Stop"]

# Invalid responses for testing NLU rejection/clarification
INVALID_RESPONSES = {
    "location": ["pizza", "123", "asdf", "the moon", "happiness"],
    "checkin_date": ["purple", "never", "banana", "very soon"],
    "checkout_date": ["pizza", "tomorrow's yesterday", "blue"],
    "guests": ["many", "some", "a few", "blue"],
    "room_type": ["flying", "underwater", "123"],
}


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
