"""Tests for DSPy result validation."""

from unittest.mock import Mock

import pytest
from pydantic import BaseModel, ValidationError
from soni.du.base import safe_extract_result, validate_dspy_result
from soni.du.models import NLUOutput
from soni.du.slot_extractor import SlotExtractionResult


class SimpleModel(BaseModel):
    """Simple model for testing."""

    name: str
    value: int


class TestValidateDspyResult:
    """Test validate_dspy_result function."""

    def test_returns_instance_if_already_correct_type(self):
        """Should return as-is if already expected type."""
        expected = SimpleModel(name="test", value=42)

        result = validate_dspy_result(expected, SimpleModel)

        assert result is expected

    def test_validates_dict_input(self):
        """Should validate dict and convert to model."""
        data = {"name": "test", "value": 42}

        result = validate_dspy_result(data, SimpleModel)

        assert isinstance(result, SimpleModel)
        assert result.name == "test"
        assert result.value == 42

    def test_raises_on_none(self):
        """Should raise TypeError on None input."""
        with pytest.raises(TypeError) as exc_info:
            validate_dspy_result(None, SimpleModel)

        assert "None" in str(exc_info.value)

    def test_raises_on_invalid_dict(self):
        """Should raise ValidationError on invalid dict."""
        data = {"name": "test"}  # Missing required 'value'

        with pytest.raises(ValidationError):
            validate_dspy_result(data, SimpleModel)

    def test_extracts_from_store_attribute(self):
        """Should extract from _store if present (DSPy pattern)."""
        mock_result = Mock()
        mock_result._store = {"name": "from_store", "value": 100}

        result = validate_dspy_result(mock_result, SimpleModel)

        assert result.name == "from_store"
        assert result.value == 100

    def test_extracts_from_model_dump(self):
        """Should use model_dump if available."""
        mock_result = Mock()
        mock_result.model_dump = Mock(return_value={"name": "dumped", "value": 200})
        # Remove _store to force model_dump path
        del mock_result._store

        result = validate_dspy_result(mock_result, SimpleModel)

        assert result.name == "dumped"

    def test_raises_on_incompatible_type(self):
        """Should raise TypeError on incompatible input."""
        with pytest.raises(TypeError):
            validate_dspy_result("not a valid input", SimpleModel)


class TestSafeExtractResult:
    """Test safe_extract_result with fallback."""

    def test_returns_validated_result_on_success(self):
        """Should return validated result when valid."""
        data = {"name": "test", "value": 42}

        result = safe_extract_result(
            data,
            SimpleModel,
            default_factory=lambda: SimpleModel(name="default", value=0),
        )

        assert result.name == "test"
        assert result.value == 42

    def test_returns_default_on_none(self):
        """Should return default when result is None."""
        result = safe_extract_result(
            None,
            SimpleModel,
            default_factory=lambda: SimpleModel(name="default", value=0),
        )

        assert result.name == "default"
        assert result.value == 0

    def test_returns_default_on_validation_error(self):
        """Should return default when validation fails."""
        invalid_data = {"name": 123}  # Wrong type

        result = safe_extract_result(
            invalid_data,
            SimpleModel,
            default_factory=lambda: SimpleModel(name="fallback", value=-1),
        )

        assert result.name == "fallback"
        assert result.value == -1


class TestNLUOutputValidation:
    """Test validation with actual NLU types."""

    def test_validates_nlu_output_dict(self):
        """Should validate NLUOutput from dict."""
        data = {
            "commands": [],
            "confidence": 0.95,
        }

        result = validate_dspy_result(data, NLUOutput)

        assert isinstance(result, NLUOutput)
        assert result.confidence == 0.95

    def test_nlu_output_with_commands(self):
        """Should handle NLUOutput with command data."""
        data = {
            "commands": [{"type": "start_flow", "flow_name": "test_flow"}],
            "confidence": 0.9,
        }

        result = validate_dspy_result(data, NLUOutput)

        assert len(result.commands) == 1


class TestSlotExtractionValidation:
    """Test validation with SlotExtractionResult."""

    def test_validates_slot_extraction_result(self):
        """Should validate SlotExtractionResult."""
        data = {"extracted_slots": [{"slot": "city", "value": "Paris", "confidence": 0.9}]}

        result = validate_dspy_result(data, SlotExtractionResult)

        assert len(result.extracted_slots) == 1
        assert result.extracted_slots[0]["slot"] == "city"
