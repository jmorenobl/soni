"""Integration tests for DSPy optimizers"""

import dspy
import pytest
from dspy.utils.dummies import DummyLM

from soni.du.modules import SoniDU
from soni.du.optimizers import optimize_soni_du


def create_minimal_trainset() -> list[dspy.Example]:
    """Create a minimal trainset for testing.

    Must have at least 4-5 examples to ensure valset is large enough
    for MIPROv2 minibatch_size after automatic train/val split.
    """
    examples = [
        # Example 1: Booking intent with destination
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
        # Example 2: Search intent
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
        # Example 3: Booking with origin and destination
        dspy.Example(
            user_message="Book a flight from NYC to LAX",
            dialogue_history="",
            current_slots="{}",
            available_actions='["book_flight", "search_flights"]',
            current_flow="none",
            structured_command="book_flight",
            extracted_slots='{"origin": "NYC", "destination": "LAX"}',
            confidence="0.95",
            reasoning="Booking with both origin and destination",
        ).with_inputs(
            "user_message",
            "dialogue_history",
            "current_slots",
            "available_actions",
            "current_flow",
        ),
        # Example 4: Search with date
        dspy.Example(
            user_message="Find flights to Miami tomorrow",
            dialogue_history="",
            current_slots="{}",
            available_actions='["book_flight", "search_flights"]',
            current_flow="none",
            structured_command="search_flights",
            extracted_slots='{"destination": "Miami", "departure_date": "tomorrow"}',
            confidence="0.88",
            reasoning="Search with date specification",
        ).with_inputs(
            "user_message",
            "dialogue_history",
            "current_slots",
            "available_actions",
            "current_flow",
        ),
        # Example 5: Booking with multiple slots
        dspy.Example(
            user_message="I need to book a flight from San Francisco to New York next Monday",
            dialogue_history="",
            current_slots="{}",
            available_actions='["book_flight", "search_flights"]',
            current_flow="none",
            structured_command="book_flight",
            extracted_slots='{"origin": "San Francisco", "destination": "New York", "departure_date": "next Monday"}',
            confidence="0.92",
            reasoning="Complete booking with all slots",
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
    # MIPROv2 will make multiple calls with different signatures, so we need varied responses
    # Format must match DialogueUnderstanding signature output for module calls
    # MIPROv2 also makes internal calls for prompt optimization that may need different formats
    dummy_responses = [
        # Response for DialogueUnderstanding signature (module predictions)
        {
            "reasoning": "User wants to book a flight",
            "result": {
                "message_type": "interruption",
                "command": "book_flight",
                "slots": [],
                "confidence": 0.95,
            },
        },
        # Response for MIPROv2 internal prompt optimization calls
        {
            "proposed_instruction": "Analyze the user message carefully and extract the intent.",
        },
    ] * 25  # Mix of both types, enough for optimization trials
    lm = DummyLM(dummy_responses)
    dspy.configure(lm=lm)

    trainset = create_minimal_trainset()

    # Act
    optimized_module, metrics = optimize_soni_du(
        trainset=trainset,
        optimizer_type="MIPROv2",
        num_trials=2,  # Minimal for testing
        timeout_seconds=60,
        minibatch_size=1,  # Small minibatch for test valset
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
    # MIPROv2 makes multiple types of calls, need varied responses
    dummy_responses = [
        # Response for DialogueUnderstanding signature
        {
            "reasoning": "User wants to book a flight",
            "result": {
                "message_type": "interruption",
                "command": "book_flight",
                "slots": [],
                "confidence": 0.95,
            },
        },
        # Response for MIPROv2 internal prompt optimization calls
        {
            "proposed_instruction": "Analyze the user message carefully and extract the intent.",
        },
    ] * 25
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
        minibatch_size=1,  # Small minibatch for test valset
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
        minibatch_size=1,  # Small minibatch for test valset
    )

    # Assert
    assert isinstance(optimized_module, SoniDU)
    assert metrics["baseline_accuracy"] >= 0.0
    assert metrics["optimized_accuracy"] >= 0.0
    assert metrics["improvement"] >= -1.0  # Can be negative
    assert metrics["total_time"] > 0
