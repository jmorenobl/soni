"""Shared fixtures for Soni tests."""

import pytest


@pytest.fixture
def empty_dialogue_state():
    """Create an empty dialogue state for testing."""
    from soni.core.state import create_empty_dialogue_state

    return create_empty_dialogue_state()
