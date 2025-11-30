"""Tests for security guardrails"""

import pytest

from soni.core.errors import ValidationError
from soni.core.security import SecurityGuardrails


class TestSecurityGuardrails:
    """Tests for SecurityGuardrails class"""

    def test_blocked_action_rejected(self):
        """Test that blocked actions are rejected"""
        # Arrange
        guardrails = SecurityGuardrails(
            allowed_actions=["search_flights", "book_flight"],
            blocked_intents=[],
        )

        # Act
        is_valid, error = guardrails.validate_action("delete_all")

        # Assert
        assert not is_valid
        assert "not in the allowed actions list" in error

    def test_allowed_action_accepted(self):
        """Test that allowed actions are accepted"""
        # Arrange
        guardrails = SecurityGuardrails(
            allowed_actions=["search_flights", "book_flight"],
            blocked_intents=[],
        )

        # Act
        is_valid, error = guardrails.validate_action("search_flights")

        # Assert
        assert is_valid
        assert error == ""

    def test_all_actions_allowed_when_list_empty(self):
        """Test that all actions are allowed when allowed_actions is empty"""
        # Arrange
        guardrails = SecurityGuardrails(
            allowed_actions=None,  # None means all allowed
            blocked_intents=[],
        )

        # Act
        is_valid, error = guardrails.validate_action("any_action")

        # Assert
        assert is_valid
        assert error == ""

    def test_blocked_intent_rejected(self):
        """Test that blocked intents are rejected"""
        # Arrange
        guardrails = SecurityGuardrails(
            allowed_actions=None,
            blocked_intents=["malicious_intent", "spam_intent"],
        )

        # Act
        is_valid, error = guardrails.validate_intent("malicious_intent")

        # Assert
        assert not is_valid
        assert "blocked" in error.lower()

    def test_allowed_intent_accepted(self):
        """Test that allowed intents are accepted"""
        # Arrange
        guardrails = SecurityGuardrails(
            allowed_actions=None,
            blocked_intents=["malicious_intent"],
        )

        # Act
        is_valid, error = guardrails.validate_intent("booking_intent")

        # Assert
        assert is_valid
        assert error == ""

    def test_confidence_threshold_enforced_max(self):
        """Test that maximum confidence threshold is enforced"""
        # Arrange
        guardrails = SecurityGuardrails(
            allowed_actions=None,
            blocked_intents=[],
            max_confidence_threshold=0.95,
        )

        # Act
        is_valid, error = guardrails.validate_confidence(0.99)

        # Assert
        assert not is_valid
        assert "exceeds maximum threshold" in error

    def test_confidence_threshold_enforced_min(self):
        """Test that minimum confidence threshold is enforced"""
        # Arrange
        guardrails = SecurityGuardrails(
            allowed_actions=None,
            blocked_intents=[],
            min_confidence_threshold=0.5,
        )

        # Act
        is_valid, error = guardrails.validate_confidence(0.3)

        # Assert
        assert not is_valid
        assert "below minimum threshold" in error

    def test_valid_confidence_accepted(self):
        """Test that valid confidence values are accepted"""
        # Arrange
        guardrails = SecurityGuardrails(
            allowed_actions=None,
            blocked_intents=[],
            min_confidence_threshold=0.0,
            max_confidence_threshold=1.0,
        )

        # Act
        is_valid, error = guardrails.validate_confidence(0.8)

        # Assert
        assert is_valid
        assert error == ""

    def test_validate_action_and_intent_together(self):
        """Test validation of action, intent, and confidence together"""
        # Arrange
        guardrails = SecurityGuardrails(
            allowed_actions=["search_flights"],
            blocked_intents=["malicious_intent"],
            max_confidence_threshold=0.95,
        )

        # Act - all valid
        is_valid, error = guardrails.validate_action_and_intent(
            "search_flights", "booking_intent", 0.8
        )

        # Assert
        assert is_valid
        assert error == ""

    def test_validate_action_and_intent_fails_on_blocked_action(self):
        """Test that validation fails if action is blocked"""
        # Arrange
        guardrails = SecurityGuardrails(
            allowed_actions=["search_flights"],
            blocked_intents=[],
        )

        # Act
        is_valid, error = guardrails.validate_action_and_intent("delete_all", "booking_intent", 0.8)

        # Assert
        assert not is_valid
        assert "not in the allowed actions list" in error

    def test_validate_action_and_intent_fails_on_blocked_intent(self):
        """Test that validation fails if intent is blocked"""
        # Arrange
        guardrails = SecurityGuardrails(
            allowed_actions=None,
            blocked_intents=["malicious_intent"],
        )

        # Act
        is_valid, error = guardrails.validate_action_and_intent(
            "search_flights", "malicious_intent", 0.8
        )

        # Assert
        assert not is_valid
        assert "blocked" in error.lower()

    def test_validate_action_and_intent_fails_on_invalid_confidence(self):
        """Test that validation fails if confidence is invalid"""
        # Arrange
        guardrails = SecurityGuardrails(
            allowed_actions=None,
            blocked_intents=[],
            max_confidence_threshold=0.95,
        )

        # Act
        is_valid, error = guardrails.validate_action_and_intent(
            "search_flights", "booking_intent", 0.99
        )

        # Assert
        assert not is_valid
        assert "exceeds maximum threshold" in error

    def test_invalid_action_name_format_rejected(self):
        """Test that invalid action name formats are rejected by guardrails"""
        # Arrange
        guardrails = SecurityGuardrails(
            allowed_actions=None,
            blocked_intents=[],
        )

        # Act
        is_valid, error = guardrails.validate_action("action<script>")

        # Assert
        assert not is_valid
        assert "Invalid action name format" in error or "Invalid" in error
