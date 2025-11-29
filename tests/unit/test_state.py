"""Unit tests for DialogueState"""

from soni.core.state import DialogueState


def test_dialogue_state_creation():
    """Test creating a DialogueState"""
    state = DialogueState()
    assert state.current_flow == "none"
    assert state.turn_count == 0
    assert len(state.messages) == 0
    assert len(state.slots) == 0


def test_dialogue_state_with_data():
    """Test DialogueState with initial data"""
    state = DialogueState(
        current_flow="book_flight",
        slots={"destination": "Paris"},
        turn_count=1,
    )
    assert state.current_flow == "book_flight"
    assert state.slots["destination"] == "Paris"
    assert state.turn_count == 1


def test_add_message():
    """Test adding messages to state"""
    state = DialogueState()
    state.add_message("user", "Hello")
    state.add_message("assistant", "Hi there!")

    assert len(state.messages) == 2
    assert state.messages[0]["role"] == "user"
    assert state.messages[0]["content"] == "Hello"


def test_get_user_messages():
    """Test getting user messages"""
    state = DialogueState()
    state.add_message("user", "Message 1")
    state.add_message("assistant", "Response 1")
    state.add_message("user", "Message 2")

    user_messages = state.get_user_messages()
    assert len(user_messages) == 2
    assert user_messages[0] == "Message 1"
    assert user_messages[1] == "Message 2"


def test_get_assistant_messages():
    """Test getting assistant messages"""
    state = DialogueState()
    state.add_message("user", "Hello")
    state.add_message("assistant", "Hi there!")
    state.add_message("user", "How are you?")
    state.add_message("assistant", "I'm doing well!")

    assistant_messages = state.get_assistant_messages()
    assert len(assistant_messages) == 2
    assert assistant_messages[0] == "Hi there!"
    assert assistant_messages[1] == "I'm doing well!"


def test_slot_operations():
    """Test slot get/set/has operations"""
    state = DialogueState()

    # Test setting and getting
    state.set_slot("destination", "Paris")
    assert state.get_slot("destination") == "Paris"
    assert state.has_slot("destination") is True

    # Test default value
    assert state.get_slot("origin", "Unknown") == "Unknown"
    assert state.has_slot("origin") is False

    # Test clearing
    state.clear_slots()
    assert len(state.slots) == 0
    assert state.has_slot("destination") is False


def test_increment_turn():
    """Test turn counter increment"""
    state = DialogueState()
    assert state.turn_count == 0

    state.increment_turn()
    assert state.turn_count == 1

    state.increment_turn()
    assert state.turn_count == 2


def test_add_trace():
    """Test adding trace events"""
    state = DialogueState()
    state.add_trace("nlu", {"intent": "book_flight"})
    state.add_trace("action", {"action": "search_flights"})

    assert len(state.trace) == 2
    assert state.trace[0]["event"] == "nlu"
    assert state.trace[0]["data"]["intent"] == "book_flight"


def test_serialization():
    """Test state serialization to/from dict and JSON"""
    state = DialogueState(
        current_flow="book_flight",
        slots={"destination": "Paris", "date": "tomorrow"},
        turn_count=2,
    )
    state.add_message("user", "I want to book a flight")

    # Test to_dict
    state_dict = state.to_dict()
    assert state_dict["current_flow"] == "book_flight"
    assert state_dict["slots"]["destination"] == "Paris"
    assert state_dict["turn_count"] == 2

    # Test from_dict
    new_state = DialogueState.from_dict(state_dict)
    assert new_state.current_flow == state.current_flow
    assert new_state.slots == state.slots
    assert new_state.turn_count == state.turn_count

    # Test to_json and from_json
    json_str = state.to_json()
    assert isinstance(json_str, str)

    restored_state = DialogueState.from_json(json_str)
    assert restored_state.current_flow == state.current_flow
    assert restored_state.slots == state.slots
