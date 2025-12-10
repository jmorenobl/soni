"""Integration tests for DSPy optimizers"""

import dspy
import pytest
from dspy.utils.dummies import DummyLM

from soni.du.modules import SoniDU
from soni.du.optimizers import optimize_soni_du


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


@pytest.mark.integration
def test_optimize_soni_du_returns_module_and_metrics():
    """Test that optimize_soni_du returns both module and metrics

    Integration test - runs with: make test-integration
    """
    # Arrange
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


@pytest.mark.integration
def test_optimize_soni_du_saves_module(tmp_path):
    """Test that optimize_soni_du can save optimized module

    Integration test - runs with: make test-integration
    """
    # Arrange
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


@pytest.mark.integration
def test_optimize_soni_du_integration(configure_dspy_for_integration, skip_without_api_key):
    """
    Integration test for full optimization pipeline with real LM.

    This test runs with integration tests: make test-integration

    Requires OPENAI_API_KEY environment variable.
    """
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
