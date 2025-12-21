"""Restaurant reservation domain configuration and example data."""

import dspy
from soni.dataset.base import ConversationContext, DomainConfig, DomainExampleData

# Example data constants
CITIES = ["Madrid", "Barcelona", "Paris", "London", "New York", "Tokyo"]
CUISINES = ["Italian", "Japanese", "Spanish", "French", "Chinese", "Mexican"]
TIMES = ["7:00 PM", "8:00 PM", "7:30 PM", "9:00 PM"]
PARTY_SIZES = ["2", "4", "6", "8"]

# Build DomainExampleData
_EXAMPLE_DATA = DomainExampleData(
    slot_values={
        "location": CITIES,
        "date": ["tomorrow", "next Friday", "Saturday", "tonight"],
        "time": TIMES,
        "party_size": PARTY_SIZES,
        "cuisine": CUISINES,
    },
    trigger_intents={
        "book_table": [
            "I want to make a reservation",
            "Book a table",
            "I need a restaurant reservation",
            "Can you help me book a table",
        ],
    },
    confirmation_positive=["Yes", "Correct", "That's right", "Confirmed", "Yeah", "Perfect"],
    confirmation_negative=["No", "That's wrong", "Incorrect", "Nope"],
    confirmation_unclear=["hmm, I'm not sure", "maybe", "I don't know", "Let me think", "um..."],
    # Multi-slot extraction examples for SlotExtractor optimization
    slot_extraction_cases=[
        # Location + Date + Time
        (
            "Table in Madrid tomorrow at 8:00 PM",
            [
                {"slot": "location", "value": "Madrid"},
                {"slot": "date", "value": "tomorrow"},
                {"slot": "time", "value": "8:00 PM"},
            ],
        ),
        (
            "Reservation for Saturday night at 7:30 PM",
            [
                {"slot": "date", "value": "Saturday"},
                {"slot": "time", "value": "7:30 PM"},
            ],
        ),
        # Location + Party Size + Cuisine
        (
            "Italian restaurant for 4 people in Paris",
            [
                {"slot": "cuisine", "value": "Italian"},
                {"slot": "party_size", "value": "4"},
                {"slot": "location", "value": "Paris"},
            ],
        ),
        (
            "Japanese dinner for 2 in Tokyo at 9:00 PM",
            [
                {"slot": "cuisine", "value": "Japanese"},
                {"slot": "party_size", "value": "2"},
                {"slot": "location", "value": "Tokyo"},
                {"slot": "time", "value": "9:00 PM"},
            ],
        ),
        # Negative examples
        ("I want to make a reservation", []),
        ("Find me a restaurant", []),
    ],
)

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
    flow_descriptions={
        "book_table": "Make restaurant reservations",
        "search_restaurants": "Search for restaurants by cuisine and location",
        "check_reservation": "Check the status of an existing restaurant reservation",
        "modify_reservation": "Modify an existing restaurant reservation",
        "cancel_reservation": "Cancel a restaurant reservation",
    },
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
    example_data=_EXAMPLE_DATA,
)

# Legacy exports for backward-compatibility
BOOKING_UTTERANCES = _EXAMPLE_DATA.trigger_intents.get("book_table", [])
CONFIRMATION_POSITIVE = _EXAMPLE_DATA.confirmation_positive
CONFIRMATION_NEGATIVE = _EXAMPLE_DATA.confirmation_negative
CONFIRMATION_UNCLEAR = _EXAMPLE_DATA.confirmation_unclear

CANCELLATION_UTTERANCES = ["Cancel", "Never mind", "Forget it", "I changed my mind", "Stop"]

# Invalid responses for testing
INVALID_RESPONSES = {
    "location": ["pizza", "123", "asdf", "the moon", "happiness"],
    "date": ["purple", "never", "banana", "asdf", "blue"],
    "time": ["purple", "yesterday", "never", "pizza"],
    "party_size": ["some", "a few", "blue", "pizza", "many"],
    "cuisine": ["123", "asdf", "purple", "flying"],
}


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
