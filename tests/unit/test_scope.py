"""Tests for ScopeManager"""

import pytest

from soni.core.config import SoniConfig
from soni.core.scope import ScopeManager
from soni.core.state import DialogueState


def test_scope_manager_initialization():
    """Test that ScopeManager initializes correctly"""
    # Arrange
    config_dict = {
        "version": "0.1",
        "settings": {
            "models": {
                "nlu": {
                    "provider": "openai",
                    "model": "gpt-4o-mini",
                    "temperature": 0.1,
                },
            },
        },
        "flows": {
            "book_flight": {
                "description": "Book a flight",
                "steps": [
                    {"step": "collect_origin", "type": "collect", "slot": "origin"},
                    {
                        "step": "search_flights",
                        "type": "action",
                        "call": "search_available_flights",
                    },
                ],
            },
        },
        "slots": {},
        "actions": {},
    }
    config = SoniConfig(**config_dict)

    # Act
    scope_manager = ScopeManager(config)

    # Assert
    assert scope_manager is not None
    assert len(scope_manager.flows) == 1
    assert "book_flight" in scope_manager.flows


def test_scope_manager_global_actions():
    """Test that global actions are always included"""
    # Arrange
    scope_manager = ScopeManager()
    state = DialogueState(current_flow="none")

    # Act
    actions = scope_manager.get_available_actions(state)

    # Assert
    assert "help" in actions
    assert "cancel" in actions
    assert "restart" in actions


def test_scope_manager_flow_actions():
    """Test that flow-specific actions are included when in a flow"""
    # Arrange
    config_dict = {
        "version": "0.1",
        "settings": {
            "models": {
                "nlu": {
                    "provider": "openai",
                    "model": "gpt-4o-mini",
                    "temperature": 0.1,
                },
            },
        },
        "flows": {
            "book_flight": {
                "description": "Book a flight",
                "steps": [
                    {
                        "step": "search_flights",
                        "type": "action",
                        "call": "search_available_flights",
                    },
                    {"step": "confirm_booking", "type": "action", "call": "confirm_flight_booking"},
                ],
            },
        },
        "slots": {},
        "actions": {},
    }
    config = SoniConfig(**config_dict)
    scope_manager = ScopeManager(config)
    state = DialogueState(current_flow="book_flight")

    # Act
    actions = scope_manager.get_available_actions(state)

    # Assert
    assert "help" in actions  # Global
    assert "search_available_flights" in actions
    assert "confirm_flight_booking" in actions


def test_scope_manager_pending_slots():
    """Test that pending slots are included as actions"""
    # Arrange
    config_dict = {
        "version": "0.1",
        "settings": {
            "models": {
                "nlu": {
                    "provider": "openai",
                    "model": "gpt-4o-mini",
                    "temperature": 0.1,
                },
            },
        },
        "flows": {
            "book_flight": {
                "description": "Book a flight",
                "steps": [
                    {"step": "collect_origin", "type": "collect", "slot": "origin"},
                    {"step": "collect_destination", "type": "collect", "slot": "destination"},
                    {"step": "collect_date", "type": "collect", "slot": "departure_date"},
                ],
            },
        },
        "slots": {},
        "actions": {},
    }
    config = SoniConfig(**config_dict)
    scope_manager = ScopeManager(config)
    state = DialogueState(
        current_flow="book_flight",
        slots={"origin": "Madrid"},  # destination and date are pending
    )

    # Act
    actions = scope_manager.get_available_actions(state)

    # Assert
    assert "provide_destination" in actions
    assert "provide_departure_date" in actions
    assert "provide_origin" not in actions  # Already filled


def test_scope_manager_no_flow():
    """Test that flow start actions are available when no flow is active"""
    # Arrange
    config_dict = {
        "version": "0.1",
        "settings": {
            "models": {
                "nlu": {
                    "provider": "openai",
                    "model": "gpt-4o-mini",
                    "temperature": 0.1,
                },
            },
        },
        "flows": {
            "book_flight": {
                "description": "Book a flight",
                "steps": [],
            },
            "modify_booking": {
                "description": "Modify booking",
                "steps": [],
            },
        },
        "slots": {},
        "actions": {},
    }
    config = SoniConfig(**config_dict)
    scope_manager = ScopeManager(config)
    state = DialogueState(current_flow="none")

    # Act
    actions = scope_manager.get_available_actions(state)

    # Assert
    assert "start_book_flight" in actions
    assert "start_modify_booking" in actions


def test_scope_manager_with_dict_state():
    """Test that get_available_actions works with dict state"""
    # Arrange
    scope_manager = ScopeManager()
    state_dict = {"current_flow": "none", "slots": {}}

    # Act
    actions = scope_manager.get_available_actions(state_dict)

    # Assert
    assert isinstance(actions, list)
    assert len(actions) > 0


def test_scope_manager_all_slots_filled():
    """Test that no provide_ actions are added when all slots are filled"""
    # Arrange
    config_dict = {
        "version": "0.1",
        "settings": {
            "models": {
                "nlu": {
                    "provider": "openai",
                    "model": "gpt-4o-mini",
                    "temperature": 0.1,
                },
            },
        },
        "flows": {
            "book_flight": {
                "description": "Book a flight",
                "steps": [
                    {"step": "collect_origin", "type": "collect", "slot": "origin"},
                    {"step": "collect_destination", "type": "collect", "slot": "destination"},
                ],
            },
        },
        "slots": {},
        "actions": {},
    }
    config = SoniConfig(**config_dict)
    scope_manager = ScopeManager(config)
    state = DialogueState(
        current_flow="book_flight",
        slots={"origin": "Madrid", "destination": "Barcelona"},  # All slots filled
    )

    # Act
    actions = scope_manager.get_available_actions(state)

    # Assert
    assert "provide_origin" not in actions
    assert "provide_destination" not in actions
    # Should still have global actions
    assert "help" in actions


def test_scope_manager_empty_flow():
    """Test that empty flow still includes global actions"""
    # Arrange
    config_dict = {
        "version": "0.1",
        "settings": {
            "models": {
                "nlu": {
                    "provider": "openai",
                    "model": "gpt-4o-mini",
                    "temperature": 0.1,
                },
            },
        },
        "flows": {
            "book_flight": {
                "description": "Book a flight",
                "steps": [],
            },
        },
        "slots": {},
        "actions": {},
    }
    config = SoniConfig(**config_dict)
    scope_manager = ScopeManager(config)
    state = DialogueState(current_flow="book_flight")

    # Act
    actions = scope_manager.get_available_actions(state)

    # Assert
    assert "help" in actions
    assert "cancel" in actions
    assert "restart" in actions
    # No flow actions since flow has no action steps
    assert "search_available_flights" not in actions
