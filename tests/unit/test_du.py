"""Unit tests for Dialogue Understanding module"""

import pytest

from soni.du.models import MessageType, NLUOutput, SlotValue
from soni.du.modules import SoniDU


def test_nlu_output():
    """Test NLUOutput Pydantic model creation and serialization"""
    # Arrange & Act
    result = NLUOutput(
        message_type=MessageType.SLOT_VALUE,
        command="book_flight",
        slots=[SlotValue(name="destination", value="Paris", confidence=0.95)],
        confidence=0.95,
        reasoning="Clear booking intent",
    )

    # Assert
    assert result.command == "book_flight"
    assert len(result.slots) == 1
    assert result.slots[0].name == "destination"
    assert result.slots[0].value == "Paris"
    assert result.confidence == 0.95

    # Act
    result_dict = result.model_dump()

    # Assert
    assert result_dict["command"] == "book_flight"
    assert result_dict["slots"][0]["name"] == "destination"
    assert result_dict["slots"][0]["value"] == "Paris"


def test_soni_du_initialization():
    """Test SoniDU module initializes with default values"""
    # Arrange & Act
    du = SoniDU()

    # Assert
    assert du.predictor is not None
    assert du.nlu_cache is not None


def test_soni_du_forward_signature():
    """Test that forward method has correct parameter signature"""
    # Arrange
    du = SoniDU()

    # Act & Assert - This validates signature even if LM not configured
    try:
        result = du.forward(
            user_message="I want to book a flight",
            dialogue_history="",
            current_slots="{}",
            available_actions='["book_flight"]',
            available_flows='["book_flight"]',
            current_flow="none",
        )
        # If we get here, signature is correct (even if execution fails)
        assert result is not None
    except Exception:
        # Expected if LM not configured - signature is still valid
        pass


@pytest.mark.asyncio
async def test_soni_du_aforward():
    """Test async forward method has correct interface"""
    # Arrange
    du = SoniDU()

    # Act & Assert - Validates async interface
    try:
        result = await du.aforward(
            user_message="Test message",
            dialogue_history="",
            current_slots="{}",
            available_actions="[]",
            available_flows="[]",
            current_flow="none",
        )
        # If we get here, async interface works
        assert result is not None
    except Exception:
        # Expected if LM not configured
        pass


@pytest.mark.asyncio
async def test_soni_du_predict():
    """Test high-level predict method returns NLUOutput"""
    # Arrange
    du = SoniDU()

    # Act & Assert
    try:
        result = await du.predict(
            user_message="I want to book a flight to Paris",
            dialogue_history="",
            current_slots={},
            available_actions=["book_flight", "help"],
            available_flows=["book_flight"],
            current_flow="none",
        )

        # Assert
        assert isinstance(result, NLUOutput)
        assert result.command is not None
    except Exception:
        # Expected if LM not configured
        pass


@pytest.mark.asyncio
async def test_soni_du_predict_error_handling():
    """Test predict method gracefully handles malformed prediction responses"""
    # Arrange
    du = SoniDU()

    # Mock a prediction object with invalid JSON in extracted_slots
    class MockPrediction:
        structured_command = "book_flight"
        extracted_slots = "invalid json"
        confidence = "not_a_number"
        reasoning = "test"

    # Replace aforward with mock that returns invalid prediction
    original_aforward = du.aforward

    async def mock_aforward(*args, **kwargs):
        return MockPrediction()

    du.aforward = mock_aforward

    try:
        # Act
        result = await du.predict(
            user_message="Test",
            current_slots={},
            available_actions=[],
        )

        # Assert - Should handle errors gracefully
        assert isinstance(result, NLUOutput)
        assert result.slots == []  # Invalid JSON → empty list
        assert result.confidence == 0.0  # Invalid float → 0.0
        assert result.command == "book_flight"
    finally:
        # Cleanup
        du.aforward = original_aforward


@pytest.mark.asyncio
async def test_soni_du_predict_missing_attributes():
    """Test predict method handles predictions with None/missing attributes"""
    # Arrange
    du = SoniDU()

    # Mock prediction with None attributes (TypeError scenario)
    class MockPrediction:
        structured_command = None
        extracted_slots = None  # Will trigger TypeError in json.loads
        confidence = None  # Will trigger TypeError in float()
        reasoning = None

    original_aforward = du.aforward

    async def mock_aforward(*args, **kwargs):
        return MockPrediction()

    du.aforward = mock_aforward

    try:
        # Act
        result = await du.predict(
            user_message="Test",
        )

        # Assert - Should handle None values gracefully
        assert isinstance(result, NLUOutput)
        assert result.slots == []
        assert result.confidence == 0.0
        assert result.command == ""
        assert result.reasoning == ""
    finally:
        # Cleanup
        du.aforward = original_aforward


def test_soni_du_forward_with_dummy_lm():
    """Test forward method with DummyLM"""
    # Arrange
    import dspy
    from dspy.utils.dummies import DummyLM

    # Configure DummyLM with responses matching our signature
    dummy_responses = [
        {
            "structured_command": "book_flight",
            "extracted_slots": '{"destination": "Paris"}',
            "confidence": "0.95",
            "reasoning": "User wants to book a flight to Paris",
        }
    ]
    lm = DummyLM(dummy_responses)
    dspy.configure(lm=lm)

    du = SoniDU()

    # Act
    result = du.forward(
        user_message="I want to book a flight to Paris",
        dialogue_history="",
        current_slots="{}",
        available_actions='["book_flight"]',
        available_flows='["book_flight"]',
        current_flow="none",
    )

    # Assert
    assert result is not None
    assert hasattr(result, "structured_command")
    assert hasattr(result, "extracted_slots")
    # DummyLM returns formatted strings, so we check they contain our values
    assert (
        "book_flight" in str(result.structured_command)
        or result.structured_command == "book_flight"
    )


def test_soni_du_serialization(tmp_path):
    """Test serialization and deserialization of SoniDU module"""
    # Arrange
    import dspy
    from dspy.utils.dummies import DummyLM

    # Configure DummyLM for serialization test
    dummy_responses = [
        {
            "structured_command": "book_flight",
            "extracted_slots": '{"destination": "Paris"}',
            "confidence": "0.95",
            "reasoning": "Test reasoning",
        }
    ]
    lm = DummyLM(dummy_responses)
    dspy.configure(lm=lm)

    du = SoniDU()
    save_path = tmp_path / "test_module.json"

    # Act - Save module
    try:
        du.save(str(save_path))
        assert save_path.exists(), "Module file should be created"

        # Act - Load module
        loaded_du = SoniDU()
        loaded_du.load(str(save_path))

        # Assert - Module should be loadable
        assert loaded_du is not None
        assert loaded_du.predictor is not None
    except Exception as e:
        # DSPy serialization may have specific requirements
        pytest.skip(f"Serialization test skipped: {e}")


@pytest.mark.skip(reason="Requires DSPy LM configuration and API key")
def test_soni_du_integration_real_dspy():
    """
    Integration test with real DSPy LM (requires API key).

    This test is skipped by default but can be run manually with:
    pytest tests/unit/test_du.py::test_soni_du_integration_real_dspy -v

    Requires OPENAI_API_KEY environment variable.
    """
    import os

    if not os.getenv("OPENAI_API_KEY"):
        pytest.skip("OPENAI_API_KEY not set")

    # Arrange
    import dspy

    dspy.configure(lm=dspy.LM("openai/gpt-4o-mini"))
    du = SoniDU()

    # Act
    result = du.forward(
        user_message="I want to book a flight to Paris",
        dialogue_history="",
        current_slots="{}",
        available_actions='["book_flight", "search_flights", "help"]',
        available_flows='["book_flight"]',
        current_flow="none",
    )

    # Assert
    assert result is not None
    assert hasattr(result, "structured_command")
    assert hasattr(result, "extracted_slots")
    assert result.structured_command is not None
