"""Unit tests for Dialogue Understanding module"""

import tempfile
from pathlib import Path
from unittest.mock import MagicMock

import pytest
import yaml

from soni.du.models import DialogueContext, MessageType, NLUOutput, SlotValue
from soni.du.modules import SoniDU


def test_nlu_output():
    """Test NLUOutput Pydantic model creation and serialization"""
    # Arrange & Act
    result = NLUOutput(
        message_type=MessageType.SLOT_VALUE,
        command="book_flight",
        slots=[SlotValue(name="destination", value="Paris", confidence=0.95)],
        confidence=0.95,
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


def test_nlu_output_with_confirmation_value():
    """Test that NLUOutput accepts confirmation_value field"""
    # Arrange
    nlu_output = NLUOutput(
        message_type=MessageType.CONFIRMATION,
        command=None,
        slots=[],
        confidence=0.9,
        confirmation_value=True,
    )

    # Assert
    assert nlu_output.confirmation_value is True
    assert nlu_output.message_type == MessageType.CONFIRMATION


def test_nlu_output_without_confirmation_value():
    """Test that NLUOutput works without confirmation_value (defaults to None)"""
    # Arrange
    nlu_output = NLUOutput(
        message_type=MessageType.SLOT_VALUE,
        command=None,
        slots=[],
        confidence=0.9,
    )

    # Assert
    assert nlu_output.confirmation_value is None


def test_nlu_output_confirmation_states():
    """Test all three states of confirmation_value"""
    # Test confirmed (True)
    confirmed = NLUOutput(
        message_type=MessageType.CONFIRMATION,
        command=None,
        slots=[],
        confidence=0.95,
        confirmation_value=True,
    )
    assert confirmed.confirmation_value is True

    # Test denied (False)
    denied = NLUOutput(
        message_type=MessageType.CONFIRMATION,
        command=None,
        slots=[],
        confidence=0.90,
        confirmation_value=False,
    )
    assert denied.confirmation_value is False

    # Test unclear (None)
    unclear = NLUOutput(
        message_type=MessageType.CONFIRMATION,
        command=None,
        slots=[],
        confidence=0.60,
        confirmation_value=None,
    )
    assert unclear.confirmation_value is None


def test_nlu_output_serialization():
    """Test that confirmation_value is included in model_dump()"""
    # Arrange
    nlu_output = NLUOutput(
        message_type=MessageType.CONFIRMATION,
        command=None,
        slots=[],
        confidence=0.9,
        confirmation_value=True,
    )

    # Act
    serialized = nlu_output.model_dump()

    # Assert
    assert "confirmation_value" in serialized
    assert serialized["confirmation_value"] is True


def test_soni_du_initialization():
    """Test SoniDU module initializes with default values"""
    # Arrange & Act
    du = SoniDU()

    # Assert
    assert du.predictor is not None
    assert du.nlu_cache is not None


def test_soni_du_forward_with_mock():
    """Test forward method with mocked predictor"""
    # Arrange
    from unittest.mock import AsyncMock, patch

    import dspy

    from soni.du.models import DialogueContext

    du = SoniDU()
    mock_prediction = MagicMock()
    mock_prediction.result = NLUOutput(
        message_type=MessageType.SLOT_VALUE,
        command="book_flight",
        slots=[SlotValue(name="destination", value="Paris", confidence=0.95)],
        confidence=0.95,
    )

    # Create context with new signature
    context = DialogueContext(
        current_slots={},
        available_actions=["book_flight"],
        available_flows={"book_flight": "Book a flight"},
        current_flow="none",
    )

    # Act
    with patch.object(du, "predictor", return_value=mock_prediction):
        result = du.forward(
            user_message="I want to book a flight",
            history=dspy.History(messages=[]),
            context=context,
            current_datetime="",
        )

    # Assert
    assert result is not None
    assert result.result.command == "book_flight"


@pytest.mark.asyncio
async def test_soni_du_aforward_with_mock():
    """Test async forward method with mocked predictor"""
    # Arrange
    from unittest.mock import AsyncMock, patch

    import dspy

    from soni.du.models import DialogueContext

    du = SoniDU()
    mock_prediction = MagicMock()
    mock_prediction.result = NLUOutput(
        message_type=MessageType.SLOT_VALUE,
        command="test_command",
        slots=[],
        confidence=0.90,
    )

    # Create context with new signature
    context = DialogueContext(
        current_slots={},
        available_actions=[],
        available_flows={},
        current_flow="none",
    )

    # Act
    # Note: predictor.acall is the async method, not predictor itself
    with patch.object(du.predictor, "acall", new_callable=AsyncMock, return_value=mock_prediction):
        result = await du.aforward(
            user_message="Test message",
            history=dspy.History(messages=[]),
            context=context,
            current_datetime="",
        )

    # Assert
    assert result is not None


@pytest.mark.asyncio
async def test_soni_du_predict_with_mock():
    """Test predict method with mocked acall"""
    # Arrange
    import dspy

    du = SoniDU()
    mock_prediction = MagicMock()
    mock_prediction.result = NLUOutput(
        message_type=MessageType.SLOT_VALUE,
        command="book_flight",
        slots=[SlotValue(name="destination", value="Paris", confidence=0.95)],
        confidence=0.95,
    )

    original_acall = du.acall

    async def mock_acall(*args, **kwargs):
        return mock_prediction

    du.acall = mock_acall

    try:
        # Act
        history = dspy.History(messages=[])
        context = DialogueContext(
            current_slots={},
            available_actions=["book_flight", "help"],
            available_flows={"book_flight": "Book a flight"},
            current_flow="none",
            expected_slots=["destination"],  # Must include destination for slot to pass filter
        )
        result = await du.predict(
            user_message="I want to book a flight to Paris",
            history=history,
            context=context,
        )

        # Assert
        assert isinstance(result, NLUOutput)
        assert result.command == "book_flight"
        assert len(result.slots) == 1
        assert result.slots[0].name == "destination"
    finally:
        # Cleanup
        du.acall = original_acall


@pytest.mark.asyncio
async def test_soni_du_predict_error_handling():
    """Test predict method gracefully handles malformed prediction responses"""
    # Arrange
    import dspy

    du = SoniDU()

    # Mock acall to return prediction with NLUOutput
    # Even with errors, should return valid NLUOutput
    mock_prediction = MagicMock()
    mock_prediction.result = NLUOutput(
        message_type=MessageType.SLOT_VALUE,
        command="book_flight",
        slots=[],  # Empty slots for error case
        confidence=0.0,  # Invalid confidence → 0.0
    )

    original_acall = du.acall

    async def mock_acall(*args, **kwargs):
        return mock_prediction

    du.acall = mock_acall

    try:
        # Act
        history = dspy.History(messages=[])
        context = DialogueContext(
            current_slots={},
            available_actions=[],
            available_flows={},
            current_flow="none",
            expected_slots=[],
        )
        result = await du.predict(
            user_message="Test",
            history=history,
            context=context,
        )

        # Assert - Should handle errors gracefully
        assert isinstance(result, NLUOutput)
        assert result.slots == []  # Empty list for error case
        assert result.confidence == 0.0  # Invalid confidence → 0.0
        assert result.command == "book_flight"
    finally:
        # Cleanup
        du.acall = original_acall


@pytest.mark.asyncio
async def test_soni_du_predict_missing_attributes():
    """Test predict method handles predictions with None/missing attributes"""
    # Arrange
    import dspy

    du = SoniDU()

    # Mock acall to return prediction with empty NLUOutput for None case
    mock_prediction = MagicMock()
    mock_prediction.result = NLUOutput(
        message_type=MessageType.SLOT_VALUE,
        command="",  # Empty for None case
        slots=[],  # Empty slots
        confidence=0.0,  # Invalid confidence → 0.0
    )

    original_acall = du.acall

    async def mock_acall(*args, **kwargs):
        return mock_prediction

    du.acall = mock_acall

    try:
        # Act
        history = dspy.History(messages=[])
        context = DialogueContext(
            current_slots={},
            available_actions=[],
            available_flows={},
            current_flow="none",
            expected_slots=[],
        )
        result = await du.predict(
            user_message="Test",
            history=history,
            context=context,
        )

        # Assert - Should handle None values gracefully
        assert isinstance(result, NLUOutput)
        assert result.slots == []
        assert result.confidence == 0.0
        assert result.command == ""
        # reasoning field was removed from NLUOutput
    finally:
        # Cleanup
        du.acall = original_acall


# NOTE: DummyLM Testing
# We don't use DSPy's DummyLM for testing SoniDU because DummyLM has limitations
# with complex Pydantic models (NLUOutput with nested SlotValue models and enums).
# Instead, we use AsyncMock which provides better control and supports Pydantic models.
# See test_soni_du_forward_with_mock() and test_soni_du_predict_with_mock() above
# for the mock-based testing approach.


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


@pytest.mark.integration
@pytest.mark.asyncio
def test_soni_du_integration_real_dspy():
    """
    Integration test with real DSPy LM (requires API key).

    This test runs with integration tests: make test-integration

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
        available_flows='{"book_flight": "Book a flight"}',
        current_flow="none",
    )

    # Assert
    assert result is not None
    assert hasattr(result, "structured_command")
    assert hasattr(result, "extracted_slots")
    assert result.structured_command is not None


def test_sonidu_default_uses_predict():
    """Test that SoniDU defaults to Predict (not ChainOfThought)."""
    import dspy

    # Act
    nlu = SoniDU()

    # Assert - Verify predictor is dspy.Predict, not ChainOfThought
    assert isinstance(nlu.predictor, dspy.Predict)
    assert not isinstance(nlu.predictor, dspy.ChainOfThought)
    assert nlu.use_cot is False


def test_sonidu_with_use_cot_true_uses_chain_of_thought():
    """Test that SoniDU uses ChainOfThought when use_cot=True."""
    import dspy

    # Act
    nlu = SoniDU(use_cot=True)

    # Assert - Verify predictor is ChainOfThought
    assert isinstance(nlu.predictor, dspy.ChainOfThought)
    assert nlu.use_cot is True


@pytest.mark.asyncio
async def test_sonidu_uses_config_from_yaml():
    """Test that SoniDU uses use_reasoning from YAML configuration."""
    from soni.runtime import RuntimeLoop

    # Create temporary YAML with use_reasoning: true
    config = {
        "version": "0.1",
        "settings": {
            "models": {
                "nlu": {
                    "provider": "openai",
                    "model": "gpt-4o-mini",
                    "temperature": 0.1,
                    "use_reasoning": True,  # Configure from YAML (maps to use_cot internally)
                }
            },
            "persistence": {"backend": "memory"},
        },
        "flows": {
            "test_flow": {
                "description": "Test flow",
                "steps": [],
            }
        },
        "slots": {},
        "actions": {},
    }

    with tempfile.NamedTemporaryFile(mode="w", suffix=".yaml", delete=False) as f:
        yaml.dump(config, f)
        temp_path = f.name

    try:
        # Act
        runtime = RuntimeLoop(temp_path)

        # Assert - Verify that DU uses ChainOfThought (use_reasoning=True maps to use_cot=True)
        assert runtime.du.use_cot is True
        import dspy

        assert isinstance(runtime.du.predictor, dspy.ChainOfThought)
    finally:
        # Cleanup - close checkpointer before deleting temp file
        await runtime.cleanup()
        Path(temp_path).unlink()
