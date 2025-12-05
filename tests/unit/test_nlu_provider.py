"""Unit tests for NLU provider."""

import dspy
import pytest
from dspy.utils.dummies import DummyLM

from soni.du.modules import SoniDU


@pytest.fixture
def dummy_lm():
    """Create DummyLM for testing."""
    lm = DummyLM(
        [
            {
                "reasoning": "User explicitly states intent",
                "result": {
                    "message_type": "interruption",
                    "command": "book_flight",
                    "slots": [],
                    "confidence": 0.95,
                    "reasoning": "User explicitly states intent",
                },
            }
        ]
    )
    dspy.configure(lm=lm)
    return lm


@pytest.mark.asyncio
async def test_dspy_nlu_provider(dummy_lm):
    """Test SoniDU with DummyLM (implements INLUProvider directly)."""
    # Arrange
    module = SoniDU()
    provider = module  # Use SoniDU directly (implements INLUProvider)

    dialogue_context = {
        "current_slots": {},
        "available_actions": ["book_flight"],
        "available_flows": ["book_flight"],
        "current_flow": "none",
        "expected_slots": [],
        "history": [],
    }

    # Act
    result = await provider.understand("book a flight", dialogue_context)

    # Assert
    assert result["command"] == "book_flight"
    assert result["message_type"] == "interruption"
    assert "confidence" in result
    assert "reasoning" in result
    assert "slots" in result


@pytest.mark.asyncio
async def test_dspy_nlu_provider_with_history(dummy_lm):
    """Test SoniDU with conversation history (implements INLUProvider directly)."""
    # Arrange
    module = SoniDU()
    provider = module  # Use SoniDU directly (implements INLUProvider)

    dialogue_context = {
        "current_slots": {"origin": "Madrid"},
        "available_actions": ["book_flight"],
        "available_flows": ["book_flight"],
        "current_flow": "book_flight",
        "expected_slots": ["destination"],
        "history": [
            {"role": "user", "content": "I want to book a flight"},
            {"role": "assistant", "content": "Where are you departing from?"},
        ],
    }

    # Act
    result = await provider.understand("Barcelona", dialogue_context)

    # Assert
    assert result["command"] == "book_flight"
    assert "slots" in result


@pytest.mark.asyncio
async def test_dspy_nlu_provider_missing_fields(dummy_lm):
    """Test SoniDU handles missing context fields (implements INLUProvider directly)."""
    # Arrange
    module = SoniDU()
    provider = module  # Use SoniDU directly (implements INLUProvider)

    dialogue_context = {}  # Empty context

    # Act
    result = await provider.understand("test", dialogue_context)

    # Assert
    assert result is not None
    assert "command" in result
    # Default values should be used
    assert result.get("message_type") is not None
