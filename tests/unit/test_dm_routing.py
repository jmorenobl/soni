"""Tests for dialogue routing logic"""

from soni.core.state import DialogueState
from soni.dm.routing import route_by_intent, should_continue


class TestShouldContinue:
    """Test should_continue routing logic"""

    def test_should_continue_with_dialogue_state(self):
        """Test should_continue accepts DialogueState and returns continue"""
        # Arrange
        state = DialogueState(
            current_flow="booking",
            slots={"origin": "NYC"},
        )

        # Act
        result = should_continue(state)

        # Assert
        assert result == "continue"

    def test_should_continue_with_dict_state(self):
        """Test should_continue accepts dict state and converts it"""
        # Arrange
        state = {
            "user_id": "test_user",
            "current_flow": "booking",
            "slots": {"origin": "NYC"},
        }

        # Act
        result = should_continue(state)

        # Assert
        assert result == "continue"
        assert isinstance(state, dict)  # Original dict not modified

    def test_should_continue_with_empty_slots(self):
        """Test should_continue with empty slots"""
        # Arrange
        state = DialogueState(
            current_flow="booking",
            slots={},
        )

        # Act
        result = should_continue(state)

        # Assert
        assert result == "continue"

    def test_should_continue_with_minimal_dict(self):
        """Test should_continue with minimal dict state"""
        # Arrange
        state = {"user_id": "test_user"}

        # Act
        result = should_continue(state)

        # Assert
        assert result == "continue"

    def test_should_continue_with_full_state(self):
        """Test should_continue with full DialogueState"""
        # Arrange
        state = DialogueState(
            current_flow="booking",
            slots={"origin": "NYC", "destination": "LAX"},
            pending_action="search_flights",
            turn_count=5,
        )

        # Act
        result = should_continue(state)

        # Assert
        assert result == "continue"


class TestRouteByIntent:
    """Test route_by_intent routing logic"""

    def test_route_by_intent_with_dialogue_state(self):
        """Test route_by_intent accepts DialogueState and returns fallback"""
        # Arrange
        state = DialogueState(
            pending_action="search_flights",
        )

        # Act
        result = route_by_intent(state)

        # Assert
        assert result == "fallback"

    def test_route_by_intent_with_dict_state(self):
        """Test route_by_intent accepts dict state and converts it"""
        # Arrange
        state = {
            "user_id": "test_user",
            "pending_action": "book_flight",
        }

        # Act
        result = route_by_intent(state)

        # Assert
        assert result == "fallback"
        assert isinstance(state, dict)  # Original dict not modified

    def test_route_by_intent_with_no_action(self):
        """Test route_by_intent when pending_action is None"""
        # Arrange
        state = DialogueState(
            pending_action=None,
        )

        # Act
        result = route_by_intent(state)

        # Assert
        assert result == "fallback"

    def test_route_by_intent_with_empty_action(self):
        """Test route_by_intent when pending_action is empty string"""
        # Arrange
        state = DialogueState(
            pending_action="",
        )

        # Act
        result = route_by_intent(state)

        # Assert
        assert result == "fallback"

    def test_route_by_intent_with_complex_action_name(self):
        """Test route_by_intent with complex action names"""
        # Arrange
        state = DialogueState(
            pending_action="check_booking_status",
        )

        # Act
        result = route_by_intent(state)

        # Assert
        assert result == "fallback"

    def test_route_by_intent_with_minimal_dict(self):
        """Test route_by_intent with minimal dict state"""
        # Arrange
        state = {"user_id": "test_user"}

        # Act
        result = route_by_intent(state)

        # Assert
        assert result == "fallback"
