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
