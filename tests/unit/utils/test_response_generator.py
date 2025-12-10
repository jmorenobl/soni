"""Tests for ResponseGenerator utility."""

import pytest

from soni.utils.response_generator import ResponseGenerator


def test_uses_confirmation_slot_priority_1():
    """Test confirmation slot has highest priority."""
    state = {
        "flow_stack": [{"flow_id": "test"}],
        "flow_slots": {"test": {"confirmation": "Confirmed!"}},
        "action_result": {"message": "Should not use this"},
        "last_response": "Should not use this",
    }

    result = ResponseGenerator.generate_from_priority(state)

    assert result == "Confirmed!"


def test_uses_action_result_priority_2():
    """Test action_result.message when no confirmation slot."""
    state = {
        "flow_stack": [],
        "flow_slots": {},
        "action_result": {"message": "Action done!"},
        "last_response": "Should not use this",
    }

    result = ResponseGenerator.generate_from_priority(state)

    assert result == "Action done!"


def test_uses_existing_response_priority_3():
    """Test existing last_response when no confirmation or action_result."""
    state = {
        "flow_stack": [],
        "flow_slots": {},
        "last_response": "Previous response",
    }

    result = ResponseGenerator.generate_from_priority(state)

    assert result == "Previous response"


def test_uses_default_fallback_priority_4():
    """Test default fallback when no other sources."""
    state = {
        "flow_stack": [],
        "flow_slots": {},
    }

    result = ResponseGenerator.generate_from_priority(state)

    assert result == "How can I help you?"


def test_action_result_dict_with_confirmation():
    """Test action_result with confirmation field."""
    state = {
        "flow_stack": [],
        "flow_slots": {},
        "action_result": {"confirmation": "Action confirmed!"},
    }

    result = ResponseGenerator.generate_from_priority(state)

    assert result == "Action confirmed!"


def test_action_result_non_dict():
    """Test action_result that is not a dict."""
    state = {
        "flow_stack": [],
        "flow_slots": {},
        "action_result": "Simple result",
    }

    result = ResponseGenerator.generate_from_priority(state)

    assert "Simple result" in result


# === generate_confirmation ===


def test_generate_confirmation_with_template():
    """Test generate_confirmation uses template from step_config."""
    from unittest.mock import MagicMock

    slots = {"origin": "NYC", "destination": "LAX"}
    step_config = MagicMock()
    step_config.message = "Confirm: origin={origin}, destination={destination}?"
    config = MagicMock()

    result = ResponseGenerator.generate_confirmation(slots, step_config, config)

    assert "NYC" in result
    assert "LAX" in result
    assert "Confirm:" in result


def test_generate_confirmation_no_template():
    """Test generate_confirmation uses default when no template."""
    from unittest.mock import MagicMock

    slots = {"origin": "NYC", "destination": "LAX"}
    step_config = None
    config = MagicMock()
    config.slots = {}

    result = ResponseGenerator.generate_confirmation(slots, step_config, config)

    assert "Let me confirm" in result
    assert "NYC" in result
    assert "LAX" in result
    assert "Is this correct?" in result


def test_generate_confirmation_with_display_names():
    """Test generate_confirmation uses display names from config."""
    from unittest.mock import MagicMock

    slots = {"origin": "NYC", "destination": "LAX"}
    step_config = None
    config = MagicMock()
    config.slots = {
        "origin": {"display_name": "Departure City"},
        "destination": {"display_name": "Arrival City"},
    }

    result = ResponseGenerator.generate_confirmation(slots, step_config, config)

    assert "Departure City" in result
    assert "Arrival City" in result
    assert "NYC" in result
    assert "LAX" in result


def test_generate_confirmation_empty_slots():
    """Test generate_confirmation with empty slots."""
    from unittest.mock import MagicMock

    slots = {}
    step_config = None
    config = MagicMock()
    config.slots = {}

    result = ResponseGenerator.generate_confirmation(slots, step_config, config)

    assert "Let me confirm" in result
    assert "Is this correct?" in result


def test_generate_confirmation_step_config_no_message():
    """Test generate_confirmation when step_config has no message."""
    from unittest.mock import MagicMock

    slots = {"origin": "NYC"}
    step_config = MagicMock()
    del step_config.message  # No message attribute
    config = MagicMock()
    config.slots = {}

    result = ResponseGenerator.generate_confirmation(slots, step_config, config)

    assert "Let me confirm" in result
    assert "NYC" in result


# === generate_digression ===


def test_generate_digression_with_command():
    """Test generate_digression with command."""
    result = ResponseGenerator.generate_digression("what_time")

    assert "what_time" in result
    assert "asking about" in result or "question" in result.lower()


def test_generate_digression_empty_command():
    """Test generate_digression with empty command."""
    result = ResponseGenerator.generate_digression("")

    assert "question" in result.lower() or "help" in result.lower()
    assert isinstance(result, str)
    assert len(result) > 0


def test_generate_digression_none_command():
    """Test generate_digression with None command."""
    result = ResponseGenerator.generate_digression(None)

    assert "question" in result.lower() or "help" in result.lower()
    assert isinstance(result, str)
    assert len(result) > 0
