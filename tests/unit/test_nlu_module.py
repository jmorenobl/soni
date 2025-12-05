"""Unit tests for NLU SoniDU module."""

import dspy
import pytest
from dspy.utils.dummies import DummyLM

from soni.du.models import DialogueContext, MessageType, NLUOutput
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
async def test_soni_du_predict(dummy_lm):
    """Test SoniDU.predict with DummyLM."""
    # Arrange
    module = SoniDU()
    user_message = "I want to book a flight"
    history = dspy.History(messages=[])
    context = DialogueContext(
        current_slots={},
        available_actions=["book_flight"],
        available_flows=["book_flight"],
        current_flow="none",
        expected_slots=[],
    )

    # Act
    result = await module.predict(user_message, history, context)

    # Assert
    assert isinstance(result, NLUOutput)
    assert result.command == "book_flight"
    assert result.message_type == MessageType.INTERRUPTION
    assert result.confidence > 0.7


@pytest.mark.asyncio
async def test_soni_du_caching(dummy_lm):
    """Test SoniDU caches results."""
    # Arrange
    module = SoniDU()
    user_message = "test"
    history = dspy.History(messages=[])
    context = DialogueContext()

    # Act
    result1 = await module.predict(user_message, history, context)
    result2 = await module.predict(user_message, history, context)

    # Assert - Should be same object (cached)
    assert result1 is result2


def test_soni_du_forward_sync(dummy_lm):
    """Test SoniDU.forward sync method."""
    # Arrange
    module = SoniDU()
    user_message = "test"
    history = dspy.History(messages=[])
    context = DialogueContext()

    # Act
    prediction = module.forward(user_message, history, context)

    # Assert
    assert hasattr(prediction, "result")
    assert isinstance(prediction.result, NLUOutput)  # Returns NLUOutput Pydantic model


@pytest.mark.asyncio
async def test_soni_du_aforward_async(dummy_lm):
    """Test SoniDU.aforward async method."""
    # Arrange
    module = SoniDU()
    user_message = "test"
    history = dspy.History(messages=[])
    context = DialogueContext()

    # Act
    prediction = await module.aforward(user_message, history, context)

    # Assert
    assert hasattr(prediction, "result")
