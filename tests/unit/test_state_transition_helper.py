"""Tests for state transition validation helper.

Design Reference: docs/design/04-state-machine.md:269-315
"""

import pytest

from tests.unit.conftest import assert_valid_state_transition


def test_assert_valid_state_transition_valid():
    """Test that valid transitions pass."""
    # Valid transitions
    assert_valid_state_transition("idle", "understanding")
    assert_valid_state_transition("understanding", "waiting_for_slot")
    assert_valid_state_transition("waiting_for_slot", "understanding")
    assert_valid_state_transition("validating_slot", "ready_for_confirmation")
    assert_valid_state_transition("confirming", "understanding")


def test_assert_valid_state_transition_invalid():
    """Test that invalid transitions raise AssertionError."""
    # Invalid transitions
    with pytest.raises(AssertionError, match="Invalid state transition"):
        assert_valid_state_transition("idle", "executing_action")

    with pytest.raises(AssertionError, match="Invalid state transition"):
        assert_valid_state_transition("waiting_for_slot", "executing_action")

    with pytest.raises(AssertionError, match="Invalid state transition"):
        assert_valid_state_transition("completed", "waiting_for_slot")


def test_assert_valid_state_transition_initial_state():
    """Test initial state transitions."""
    # Initial state (None) can transition to idle or understanding
    assert_valid_state_transition(None, "idle")
    assert_valid_state_transition(None, "understanding")

    # Invalid initial transitions
    with pytest.raises(AssertionError, match="Invalid initial state transition"):
        assert_valid_state_transition(None, "executing_action")


def test_assert_valid_state_transition_with_context():
    """Test that context is included in error message."""
    with pytest.raises(AssertionError, match="Test context"):
        assert_valid_state_transition("idle", "executing_action", context="Test context")
