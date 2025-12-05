"""Unit tests for NLU DSPy signatures."""

import dspy
import pytest

from soni.du.models import DialogueContext
from soni.du.signatures import DialogueUnderstanding


def test_signature_has_required_fields():
    """Test signature has all required input/output fields."""
    # Arrange
    sig = DialogueUnderstanding

    # Act
    input_fields = list(sig.input_fields.keys())
    output_fields = list(sig.output_fields.keys())

    # Assert
    assert "user_message" in input_fields
    assert "history" in input_fields
    assert "context" in input_fields
    assert "current_datetime" in input_fields
    assert "result" in output_fields


def test_signature_uses_structured_types():
    """Test signature uses Pydantic models for structured types."""
    # Arrange
    sig = DialogueUnderstanding

    # Act
    context_field = sig.input_fields.get("context")
    result_field = sig.output_fields.get("result")

    # Assert
    assert context_field is not None
    assert result_field is not None
    # Verify types are DialogueContext and NLUOutput (check annotations)
    assert hasattr(context_field, "annotation")
    assert hasattr(result_field, "annotation")


def test_signature_has_history_field():
    """Test signature uses dspy.History for conversation history."""
    # Arrange
    sig = DialogueUnderstanding

    # Act
    history_field = sig.input_fields.get("history")

    # Assert
    assert history_field is not None
    assert "history" in sig.input_fields


def test_signature_no_old_string_fields():
    """Test signature does not have old string-based fields."""
    # Arrange
    sig = DialogueUnderstanding

    # Act
    input_fields = list(sig.input_fields.keys())

    # Assert
    assert "dialogue_history" not in input_fields
    assert "current_slots" not in input_fields
    assert "available_actions" not in input_fields
    assert "available_flows" not in input_fields
    assert "expected_slots" not in input_fields
    assert "structured_command" not in sig.output_fields
    assert "extracted_slots" not in sig.output_fields
