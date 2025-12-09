"""Unit tests for defensive checks and cycle detection."""

import pytest

from soni.utils.cycle_detector import StateTransitionCycleDetector


# === CYCLE DETECTOR TESTS ===
def test_cycle_detector_2_step():
    """Test that cycle detector identifies A→B→A→B pattern."""
    detector = StateTransitionCycleDetector()

    # Add transitions
    assert not detector.add_transition("understand", "handle_confirmation")
    assert not detector.add_transition("handle_confirmation", "understand")
    assert not detector.add_transition("understand", "handle_confirmation")
    assert not detector.add_transition("handle_confirmation", "understand")
    assert not detector.add_transition("understand", "handle_confirmation")
    # 6th transition completes the cycle detection
    assert detector.add_transition("handle_confirmation", "understand")


def test_cycle_detector_no_false_positives():
    """Test that cycle detector doesn't trigger on normal flow."""
    detector = StateTransitionCycleDetector()

    # Normal flow: understand → validate → collect → understand
    assert not detector.add_transition("understand", "validate_slot")
    assert not detector.add_transition("validate_slot", "collect_next_slot")
    assert not detector.add_transition("collect_next_slot", "understand")
    assert not detector.add_transition("understand", "validate_slot")


def test_cycle_detector_can_be_reset():
    """Test that resetting clears history."""
    detector = StateTransitionCycleDetector()

    # Add some transitions
    detector.add_transition("A", "B")
    detector.add_transition("B", "A")
    assert len(detector.transition_history) == 2

    # Reset
    detector.reset()
    assert len(detector.transition_history) == 0


def test_cycle_detector_3_step_cycle():
    """Test that cycle detector identifies 3-step cycles."""
    detector = StateTransitionCycleDetector()

    # Add 3-step cycle: A→B→C→A→B→C→A→B→C
    transitions = [
        ("A", "B"),
        ("B", "C"),
        ("C", "A"),
        ("A", "B"),
        ("B", "C"),
        ("C", "A"),
        ("A", "B"),
        ("B", "C"),
    ]

    # First 8 transitions shouldn't trigger (need 9 for 3-step cycle)
    for i, (from_node, to_node) in enumerate(transitions):
        if i < 8:
            assert not detector.add_transition(from_node, to_node)

    # 9th transition completes the cycle
    assert detector.add_transition("C", "A")


def test_cycle_detector_max_history():
    """Test that max_history limits the history size."""
    detector = StateTransitionCycleDetector(max_history=5)

    # Add more transitions than max_history
    for i in range(10):
        detector.add_transition(f"node_{i}", f"node_{i + 1}")

    # History should be limited to max_history
    assert len(detector.transition_history) == 5
    # Should contain the most recent transitions
    assert detector.transition_history[-1] == ("node_9", "node_10")
