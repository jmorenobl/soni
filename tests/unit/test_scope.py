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


def test_scope_manager_cache_hit():
    """Test that cache returns same result"""
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
                ],
            },
        },
        "slots": {},
        "actions": {},
    }
    config = SoniConfig(**config_dict)
    scope_manager = ScopeManager(config)
    state = DialogueState(current_flow="book_flight")

    # Act - first call (cache miss)
    actions1 = scope_manager.get_available_actions(state)

    # Act - second call (cache hit)
    actions2 = scope_manager.get_available_actions(state)

    # Assert
    assert actions1 == actions2
    assert len(scope_manager.scoping_cache) == 1


def test_get_flow_actions_with_procedural_steps():
    """Test action extraction from procedural steps"""
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
                    {
                        "step": "confirm_booking",
                        "type": "action",
                        "call": "confirm_flight_booking",
                    },
                ],
            },
        },
        "slots": {},
        "actions": {},
    }
    config = SoniConfig(**config_dict)
    scope_manager = ScopeManager(config)
    flow_config = config.flows["book_flight"]

    # Act
    actions = scope_manager._get_flow_actions(flow_config)

    # Assert
    assert "search_available_flights" in actions
    assert "confirm_flight_booking" in actions
    assert "origin" not in actions  # Not an action, it's a collect step


def test_get_flow_actions_with_dict_format():
    """Test action extraction from dict format flow config"""
    # Arrange
    scope_manager = ScopeManager()
    flow_config = {
        "steps": [
            {"step": "collect_origin", "type": "collect", "slot": "origin"},
            {
                "step": "search_flights",
                "type": "action",
                "call": "search_available_flights",
            },
        ],
        "process": [
            {
                "step": "confirm_booking",
                "type": "action",
                "call": "confirm_flight_booking",
            },
        ],
    }

    # Act
    actions = scope_manager._get_flow_actions(flow_config)

    # Assert
    assert "search_available_flights" in actions
    assert "confirm_flight_booking" in actions


def test_get_flow_actions_with_direct_actions_list():
    """Test action extraction from direct actions list"""
    # Arrange
    scope_manager = ScopeManager()
    flow_config = {
        "actions": ["action1", "action2", "action3"],
    }

    # Act
    actions = scope_manager._get_flow_actions(flow_config)

    # Assert
    assert "action1" in actions
    assert "action2" in actions
    assert "action3" in actions


def test_extract_collect_slots():
    """Test extraction of collect slots from flow config"""
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
    flow_config = config.flows["book_flight"]

    # Act
    slots = scope_manager._extract_collect_slots(flow_config)

    # Assert
    assert "origin" in slots
    assert "destination" in slots
    assert "departure_date" in slots
    assert len(slots) == 3


def test_extract_collect_slots_dict_format():
    """Test extraction of collect slots from dict format"""
    # Arrange
    scope_manager = ScopeManager()
    flow_config = {
        "steps": [
            {"step": "collect_origin", "type": "collect", "slot": "origin"},
            {"step": "collect_destination", "type": "collect", "slot": "destination"},
        ],
    }

    # Act
    slots = scope_manager._extract_collect_slots(flow_config)

    # Assert
    assert "origin" in slots
    assert "destination" in slots
    assert len(slots) == 2


def test_get_pending_slots():
    """Test getting pending slots that need to be collected"""
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
    flow_config = config.flows["book_flight"]
    state = DialogueState(
        current_flow="book_flight",
        slots={"origin": "Madrid"},  # destination and date are pending
    )

    # Act
    pending = scope_manager._get_pending_slots(flow_config, state)

    # Assert
    assert "destination" in pending
    assert "departure_date" in pending
    assert "origin" not in pending  # Already filled


def test_get_expected_slots_with_flow_name():
    """Test getting expected slots for a specific flow"""
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

    # Act
    expected_slots = scope_manager.get_expected_slots("book_flight")

    # Assert
    assert "origin" in expected_slots
    assert "destination" in expected_slots
    assert "departure_date" in expected_slots
    assert len(expected_slots) == 3


def test_get_expected_slots_infer_from_actions():
    """Test inferring flow from available actions"""
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
    available_actions = ["start_book_flight", "help", "cancel"]

    # Act
    expected_slots = scope_manager.get_expected_slots(
        flow_name=None, available_actions=available_actions
    )

    # Assert
    assert "origin" in expected_slots
    assert "destination" in expected_slots
    assert len(expected_slots) == 2


def test_get_expected_slots_flow_not_found():
    """Test getting expected slots for non-existent flow"""
    # Arrange
    config = SoniConfig(
        version="0.1",
        settings={"models": {"nlu": {"provider": "openai", "model": "gpt-4o-mini"}}},
        flows={},
        slots={},
        actions={},
    )
    scope_manager = ScopeManager(config)

    # Act
    expected_slots = scope_manager.get_expected_slots("nonexistent_flow")

    # Assert
    assert expected_slots == []


def test_get_expected_slots_no_flow_no_actions():
    """Test getting expected slots when no flow and no actions to infer"""
    # Arrange
    config = SoniConfig(
        version="0.1",
        settings={"models": {"nlu": {"provider": "openai", "model": "gpt-4o-mini"}}},
        flows={},
        slots={},
        actions={},
    )
    scope_manager = ScopeManager(config)

    # Act
    expected_slots = scope_manager.get_expected_slots(flow_name=None, available_actions=[])

    # Assert
    assert expected_slots == []


def test_get_expected_slots_with_none_flow_name():
    """Test getting expected slots with None flow name"""
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
                ],
            },
        },
        "slots": {},
        "actions": {},
    }
    config = SoniConfig(**config_dict)
    scope_manager = ScopeManager(config)

    # Act - No actions provided, should return empty
    expected_slots = scope_manager.get_expected_slots(flow_name=None)

    # Assert
    assert expected_slots == []


def test_get_cache_key():
    """Test cache key generation"""
    # Arrange
    scope_manager = ScopeManager()
    state1 = DialogueState(current_flow="book_flight", slots={"origin": "Madrid"})
    state2 = DialogueState(current_flow="book_flight", slots={"origin": "Madrid"})
    state3 = DialogueState(current_flow="book_flight", slots={"origin": "Barcelona"})

    # Act
    key1 = scope_manager._get_cache_key(state1)
    key2 = scope_manager._get_cache_key(state2)
    key3 = scope_manager._get_cache_key(state3)

    # Assert
    assert key1 == key2  # Same state should generate same key
    assert key1 != key3  # Different slots should generate different key
    assert isinstance(key1, str)
    assert len(key1) == 32  # MD5 hash is 32 hex characters
