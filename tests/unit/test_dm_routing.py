"""Unit tests for routing logic."""

import pytest

from soni.core.events import (
    EVENT_ACTION_EXECUTED,
    EVENT_SLOT_COLLECTION,
    EVENT_VALIDATION_ERROR,
)
from soni.core.state import DialogueState
from soni.dm.routing import should_continue_flow


def test_router_stops_on_slot_collection():
    """Test that router stops when slot collection is requested."""
    state = DialogueState(
        messages=[],
        current_flow="test",
        slots={},
        trace=[{"event": EVENT_SLOT_COLLECTION, "data": {"slot": "origin"}}],
    )
    assert should_continue_flow(state) == "end"


def test_router_stops_on_validation_error():
    """Test that router stops when validation error occurs."""
    state = DialogueState(
        messages=[],
        current_flow="test",
        slots={},
        trace=[{"event": EVENT_VALIDATION_ERROR, "data": {"slot": "origin"}}],
    )
    assert should_continue_flow(state) == "end"


def test_router_continues_on_action_executed():
    """Test that router continues after action execution."""
    state = DialogueState(
        messages=[],
        current_flow="test",
        slots={},
        trace=[{"event": EVENT_ACTION_EXECUTED, "data": {"action": "search"}}],
    )
    assert should_continue_flow(state) == "next"


def test_router_continues_on_empty_trace():
    """Test that router continues if trace is empty."""
    state = DialogueState(
        messages=[],
        current_flow="test",
        slots={},
        trace=[],
    )
    assert should_continue_flow(state) == "next"


def test_router_continues_on_other_events():
    """Test that router continues on other events."""
    state = DialogueState(
        messages=[],
        current_flow="test",
        slots={},
        trace=[{"event": "some_other_event", "data": {}}],
    )
    assert should_continue_flow(state) == "next"
