"""Tests for dataset validation registry."""

import dspy
import pytest

from soni.dataset.registry import validate_dataset


def test_validate_dataset_basic():
    """Should validate a list of dspy.Examples."""
    from soni.du.models import NLUOutput

    examples = [
        dspy.Example(
            user_message="Hello",
            history=[],
            context={},
            result=NLUOutput(commands=[], reasoning="test"),
        ).with_inputs("user_message", "history", "context")
    ]

    stats = validate_dataset(examples)
    assert stats["total_examples"] == 1
    assert "commands" in stats


def test_validate_empty_dataset_fails():
    """Should fail validation for empty list."""
    with pytest.raises(ValueError, match="Dataset is empty"):
        validate_dataset([])
