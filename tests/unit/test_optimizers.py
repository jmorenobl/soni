"""Unit tests for DSPy optimizers"""

import json
import tempfile
from pathlib import Path
from unittest.mock import MagicMock, patch

import dspy
import pytest

from soni.du.modules import SoniDU
from soni.du.optimizers import (
    _evaluate_module,
    load_optimized_module,
    optimize_soni_du,
)


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


def create_trainset_with_history() -> list[dspy.Example]:
    """Create trainset with history and context (new format)."""
    from soni.du.models import DialogueContext

    examples = [
        dspy.Example(
            user_message="I want to book a flight to Paris",
            history=dspy.History(messages=[]),
            context=DialogueContext(),
            structured_command="book_flight",
            extracted_slots='{"destination": "Paris"}',
            confidence="0.9",
        ).with_inputs("user_message", "history", "context"),
        dspy.Example(
            user_message="Search for flights to London",
            history=dspy.History(messages=[]),
            context=DialogueContext(),
            structured_command="search_flights",
            extracted_slots='{"destination": "London"}',
            confidence="0.85",
        ).with_inputs("user_message", "history", "context"),
    ]
    return examples


@patch("soni.du.optimizers.dspy")
def test_optimize_soni_du_basic_flow(mock_dspy, tmp_path):
    """Test optimize_soni_du basic flow with mocked components."""
    # Arrange
    trainset = create_trainset_with_history()

    # Mock DummyLM
    mock_lm = MagicMock()
    mock_dspy.LM.return_value = mock_lm
    mock_dspy.configure.return_value = None

    # Mock MIPROv2 optimizer
    mock_optimizer = MagicMock()
    mock_optimized_module = MagicMock(spec=SoniDU)
    mock_optimizer.compile.return_value = mock_optimized_module

    with patch("soni.du.optimizers.MIPROv2", return_value=mock_optimizer):
        with patch("soni.du.optimizers._evaluate_module", side_effect=[0.5, 0.7]):
            # Act
            optimized_nlu, metrics = optimize_soni_du(
                trainset=trainset,
                optimizer_type="MIPROv2",
                num_trials=2,
                output_dir=tmp_path,
            )

            # Assert
            assert optimized_nlu == mock_optimized_module
            assert metrics["baseline_accuracy"] == 0.5
            assert metrics["optimized_accuracy"] == 0.7
            assert metrics["improvement"] == pytest.approx(0.2, abs=1e-6)  # Handle float precision
            assert metrics["num_trials"] == 2
            assert metrics["trainset_size"] == 2
            # Time metrics should exist
            assert "baseline_time" in metrics
            assert "optimization_time" in metrics
            assert "optimized_eval_time" in metrics
            assert "total_time" in metrics
            mock_optimizer.compile.assert_called_once()


@patch("soni.du.optimizers.dspy")
def test_optimize_soni_du_optimization_failure(mock_dspy):
    """Test optimize_soni_du handles optimization failures."""
    # Arrange
    trainset = create_trainset_with_history()

    mock_optimizer = MagicMock()
    mock_optimizer.compile.side_effect = RuntimeError("Optimization failed")

    with patch("soni.du.optimizers.MIPROv2", return_value=mock_optimizer):
        with patch("soni.du.optimizers._evaluate_module", return_value=0.5):
            # Act & Assert
            with pytest.raises(RuntimeError, match="Optimization failed"):
                optimize_soni_du(trainset=trainset, num_trials=1)


@patch("soni.du.optimizers.dspy")
@patch("soni.du.optimizers.time.time")
def test_optimize_soni_du_timeout_warning(mock_time, mock_dspy, tmp_path):
    """Test optimize_soni_du handles timeout."""
    # Arrange
    trainset = create_trainset_with_history()

    # Mock time.time to simulate timeout (called multiple times)
    call_count = [0]

    def time_side_effect():
        call_count[0] += 1
        # baseline_start=1, baseline_end=2, opt_start=3, opt_end=100, eval_start=101, eval_end=102
        if call_count[0] == 1:
            return 1.0  # baseline_start
        elif call_count[0] == 2:
            return 2.0  # baseline_end
        elif call_count[0] == 3:
            return 3.0  # optimization_start
        elif call_count[0] == 4:
            return 100.0  # optimization_end (99s > 50s timeout)
        elif call_count[0] == 5:
            return 101.0  # optimized_start
        else:
            return 102.0  # optimized_end

    mock_time.side_effect = time_side_effect

    mock_optimizer = MagicMock()
    mock_optimized_module = MagicMock(spec=SoniDU)
    mock_optimizer.compile.return_value = mock_optimized_module

    with patch("soni.du.optimizers.MIPROv2", return_value=mock_optimizer):
        with patch("soni.du.optimizers._evaluate_module", side_effect=[0.5, 0.7]):
            # Act
            optimized_nlu, metrics = optimize_soni_du(
                trainset=trainset,
                optimizer_type="MIPROv2",
                num_trials=1,
                timeout_seconds=50,  # Less than optimization_time (97s)
                output_dir=tmp_path,
            )

            # Assert
            assert optimized_nlu == mock_optimized_module
            assert metrics["optimization_time"] == 97.0  # 100 - 3


@patch("soni.du.optimizers.dspy")
def test_optimize_soni_du_saves_module(mock_dspy, tmp_path):
    """Test optimize_soni_du saves optimized module."""
    # Arrange
    trainset = create_trainset_with_history()

    mock_optimizer = MagicMock()
    mock_optimized_module = MagicMock(spec=SoniDU)
    mock_optimized_module.save = MagicMock()
    mock_optimizer.compile.return_value = mock_optimized_module

    with patch("soni.du.optimizers.MIPROv2", return_value=mock_optimizer):
        with patch("soni.du.optimizers._evaluate_module", side_effect=[0.5, 0.7]):
            # Act
            optimized_nlu, metrics = optimize_soni_du(
                trainset=trainset,
                optimizer_type="MIPROv2",
                num_trials=1,
                output_dir=tmp_path,
            )

            # Assert
            module_path = tmp_path / "optimized_nlu.json"
            mock_optimized_module.save.assert_called_once_with(str(module_path))


def test_evaluate_module_with_mock():
    """Test _evaluate_module with mocked module."""
    # Arrange
    trainset = create_trainset_with_history()
    # Create mock with forward() method
    mock_module = MagicMock()
    mock_forward = MagicMock()

    from soni.du.models import MessageType, NLUOutput

    mock_prediction = NLUOutput(
        message_type=MessageType.SLOT_VALUE,
        command="book_flight",
        slots=[],
        confidence=0.9,
    )
    # Configure forward() to return the prediction
    mock_forward.return_value = mock_prediction
    mock_module.forward = mock_forward

    # Configure __call__() to call forward() (DSPy pattern: module() -> __call__() -> forward())
    # Use side_effect on the mock itself so calling it as function calls forward()
    def call_forward(**kwargs):
        return mock_forward(**kwargs)

    mock_module.side_effect = call_forward

    with patch("soni.du.optimizers.intent_accuracy_metric", return_value=1.0):
        # Act
        score = _evaluate_module(mock_module, trainset)

        # Assert
        assert score == 1.0
        # Verify that forward() was called (via __call__)
        assert mock_forward.call_count == 2


def test_evaluate_module_handles_errors():
    """Test _evaluate_module handles prediction errors."""
    # Arrange
    trainset = create_trainset_with_history()
    mock_module = MagicMock(spec=SoniDU)
    mock_module.forward.side_effect = ValueError("Prediction error")

    # Act
    score = _evaluate_module(mock_module, trainset)

    # Assert
    assert score == 0.0  # Errors result in 0.0 score


def test_evaluate_module_empty_trainset():
    """Test _evaluate_module with empty trainset."""
    # Arrange
    trainset = []
    mock_module = MagicMock(spec=SoniDU)

    # Act
    score = _evaluate_module(mock_module, trainset)

    # Assert
    assert score == 0.0


def test_evaluate_module_without_history():
    """Test _evaluate_module handles examples without history."""
    # Arrange
    example = dspy.Example(
        user_message="Book a flight",
        structured_command="book_flight",
    ).with_inputs("user_message")
    trainset = [example]

    mock_module = MagicMock(spec=SoniDU)
    from soni.du.models import MessageType, NLUOutput

    mock_prediction = NLUOutput(
        message_type=MessageType.SLOT_VALUE,
        command="book_flight",
        slots=[],
        confidence=0.9,
    )
    mock_module.forward.return_value = mock_prediction

    with patch("soni.du.optimizers.intent_accuracy_metric", return_value=1.0):
        # Act
        score = _evaluate_module(mock_module, trainset)

        # Assert
        assert score == 1.0


def test_load_optimized_module_success(tmp_path):
    """Test load_optimized_module successfully loads module."""
    # Arrange
    module_file = tmp_path / "optimized_nlu.json"
    module_file.write_text('{"test": "data"}')

    mock_module = MagicMock(spec=SoniDU)
    with patch("soni.du.optimizers.SoniDU", return_value=mock_module):
        # Act
        result = load_optimized_module(module_file)

        # Assert
        assert result == mock_module
        mock_module.load.assert_called_once_with(str(module_file))


def test_load_optimized_module_load_error(tmp_path):
    """Test load_optimized_module handles load errors."""
    # Arrange
    module_file = tmp_path / "optimized_nlu.json"
    module_file.write_text('{"test": "data"}')

    mock_module = MagicMock(spec=SoniDU)
    mock_module.load.side_effect = ValueError("Load error")

    with patch("soni.du.optimizers.SoniDU", return_value=mock_module):
        # Act & Assert
        with pytest.raises(RuntimeError, match="Failed to load module"):
            load_optimized_module(module_file)
