"""Unit tests for DSPy optimizers"""

import json
import tempfile
from pathlib import Path

import dspy
import pytest

from soni.du.modules import SoniDU
from soni.du.optimizers import load_optimized_module, optimize_soni_du


def create_minimal_trainset() -> list[dspy.Example]:
    """Create a minimal trainset for testing"""
    examples = [
        dspy.Example(
            user_message="I want to book a flight to Paris",
            dialogue_history="",
            current_slots="{}",
            available_actions='["book_flight", "search_flights"]',
            current_flow="none",
            structured_command="book_flight",
            extracted_slots='{"destination": "Paris"}',
            confidence="0.9",
            reasoning="Clear booking intent",
        ).with_inputs(
            "user_message",
            "dialogue_history",
            "current_slots",
            "available_actions",
            "current_flow",
        ),
        dspy.Example(
            user_message="Search for flights to London",
            dialogue_history="",
            current_slots="{}",
            available_actions='["book_flight", "search_flights"]',
            current_flow="none",
            structured_command="search_flights",
            extracted_slots='{"destination": "London"}',
            confidence="0.85",
            reasoning="Search intent",
        ).with_inputs(
            "user_message",
            "dialogue_history",
            "current_slots",
            "available_actions",
            "current_flow",
        ),
    ]
    return examples


def test_optimize_soni_du_unsupported_optimizer():
    """Test that optimize_soni_du raises ValueError for unsupported optimizer"""
    # Arrange
    trainset = create_minimal_trainset()

    # Act & Assert
    with pytest.raises(ValueError, match="Unsupported optimizer type"):
        optimize_soni_du(
            trainset=trainset,
            optimizer_type="UNKNOWN",
            num_trials=1,
        )


def test_load_optimized_module_file_not_found():
    """Test that load_optimized_module raises FileNotFoundError for missing file"""
    # Arrange
    non_existent_path = Path("/nonexistent/path/module.json")

    # Act & Assert
    with pytest.raises(FileNotFoundError):
        load_optimized_module(non_existent_path)


def test_load_optimized_module_invalid_file(tmp_path):
    """Test that load_optimized_module handles invalid files gracefully"""
    # Arrange
    invalid_file = tmp_path / "invalid.json"
    invalid_file.write_text("not valid json")

    # Act & Assert
    with pytest.raises(RuntimeError, match="Failed to load module"):
        load_optimized_module(invalid_file)
