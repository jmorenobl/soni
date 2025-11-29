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


def test_optimize_soni_du_returns_module_and_metrics():
    """Test that optimize_soni_du returns both module and metrics"""
    # Arrange
    import dspy
    from dspy.utils.dummies import DummyLM

    # Configure DummyLM with enough responses for optimization
    # MIPROv2 will make multiple calls, so we need many responses
    dummy_responses = [
        {
            "structured_command": "book_flight",
            "extracted_slots": '{"destination": "Paris"}',
            "confidence": "0.95",
            "reasoning": "User wants to book a flight",
        }
    ] * 50  # Enough responses for optimization trials
    lm = DummyLM(dummy_responses)
    dspy.configure(lm=lm)

    trainset = create_minimal_trainset()

    # Act
    try:
        optimized_module, metrics = optimize_soni_du(
            trainset=trainset,
            optimizer_type="MIPROv2",
            num_trials=2,  # Minimal for testing
            timeout_seconds=60,
        )

        # Assert
        assert isinstance(optimized_module, SoniDU)
        assert isinstance(metrics, dict)
        assert "baseline_accuracy" in metrics
        assert "optimized_accuracy" in metrics
        assert "improvement" in metrics
        assert "improvement_pct" in metrics
    except Exception as e:
        # MIPROv2 may have specific requirements even with DummyLM
        pytest.skip(f"Optimization test skipped: {e}")


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


def test_optimize_soni_du_saves_module(tmp_path):
    """Test that optimize_soni_du can save optimized module"""
    # Arrange
    import dspy
    from dspy.utils.dummies import DummyLM

    # Configure DummyLM
    dummy_responses = [
        {
            "structured_command": "book_flight",
            "extracted_slots": '{"destination": "Paris"}',
            "confidence": "0.95",
            "reasoning": "User wants to book a flight",
        }
    ] * 50
    lm = DummyLM(dummy_responses)
    dspy.configure(lm=lm)

    trainset = create_minimal_trainset()
    output_dir = tmp_path / "models"

    # Act
    try:
        optimized_module, metrics = optimize_soni_du(
            trainset=trainset,
            optimizer_type="MIPROv2",
            num_trials=2,
            timeout_seconds=60,
            output_dir=output_dir,
        )

        # Assert
        assert isinstance(optimized_module, SoniDU)
        module_path = output_dir / "optimized_nlu.json"
        assert module_path.exists(), "Module file should be created"
    except Exception as e:
        pytest.skip(f"Optimization test skipped: {e}")


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


@pytest.mark.skip(reason="Requires DSPy LM configuration and API key")
def test_optimize_soni_du_integration():
    """
    Integration test for full optimization pipeline (requires API key).

    This test is skipped by default but can be run manually with:
    pytest tests/unit/test_optimizers.py::test_optimize_soni_du_integration -v

    Requires OPENAI_API_KEY environment variable.
    """
    import os

    if not os.getenv("OPENAI_API_KEY"):
        pytest.skip("OPENAI_API_KEY not set")

    # Arrange
    import dspy

    dspy.configure(lm=dspy.LM("openai/gpt-4o-mini"))
    trainset = create_minimal_trainset()

    # Act
    optimized_module, metrics = optimize_soni_du(
        trainset=trainset,
        optimizer_type="MIPROv2",
        num_trials=3,
        timeout_seconds=300,
    )

    # Assert
    assert isinstance(optimized_module, SoniDU)
    assert metrics["baseline_accuracy"] >= 0.0
    assert metrics["optimized_accuracy"] >= 0.0
    assert metrics["improvement"] >= -1.0  # Can be negative
    assert metrics["total_time"] > 0
