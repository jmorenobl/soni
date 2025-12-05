"""Unit tests for CLI module"""

import json
import tempfile
from pathlib import Path

import pytest
from typer.testing import CliRunner

from soni.cli.main import app
from soni.cli.optimize import _load_trainset_from_file


def test_cli_help():
    """Test CLI help command displays framework info and available commands"""
    # Arrange
    runner = CliRunner()

    # Act
    result = runner.invoke(app, ["--help"])

    # Assert
    assert result.exit_code == 0
    assert "Soni Framework" in result.stdout
    assert "optimize" in result.stdout
    assert "server" in result.stdout


def test_cli_version():
    """Test CLI version command displays correct version"""
    # Arrange
    runner = CliRunner()

    # Act
    result = runner.invoke(app, ["--version"])

    # Assert
    assert result.exit_code == 0
    assert "Soni Framework version 0.4.0" in result.stdout


def test_optimize_help():
    """Test optimize subcommand help"""
    # Arrange
    runner = CliRunner()

    # Act
    result = runner.invoke(app, ["optimize", "--help"])

    # Assert
    assert result.exit_code == 0
    assert "Optimize NLU modules with DSPy" in result.stdout
    assert "optimize" in result.stdout
    assert "load" in result.stdout


def test_optimize_optimize_missing_trainset():
    """Test optimize command fails with missing trainset file"""
    # Arrange
    runner = CliRunner()

    # Act
    result = runner.invoke(
        app, ["optimize", "optimize", "--trainset", "/nonexistent/trainset.json"]
    )

    # Assert - Command should fail with non-zero exit code
    assert result.exit_code == 1
    assert "Loading trainset from" in result.stdout


def test_optimize_load_missing_module():
    """Test optimize load fails with missing module file"""
    # Arrange
    runner = CliRunner()

    # Act
    result = runner.invoke(app, ["optimize", "load", "--module", "/nonexistent/module.json"])

    # Assert - Command should fail with non-zero exit code
    assert result.exit_code == 1
    assert "Loading module from" in result.stdout


def test_server_command():
    """Test server command requires subcommand"""
    # Arrange
    runner = CliRunner()

    # Act - server command without subcommand should fail with exit code 2
    result = runner.invoke(app, ["server"])

    # Assert - Typer returns exit code 2 when subcommand is missing
    # The error message is in stderr, and stdout may be empty
    assert result.exit_code == 2  # Typer's standard exit code for missing subcommand
    # Verify that it's not the old placeholder message
    assert "Coming soon in Hito 7" not in result.stdout
    assert "Coming soon in Hito 7" not in result.stderr


# Tests for _load_trainset_from_file helper


def test_load_trainset_from_file_valid():
    """Test loading valid trainset from JSON file"""
    # Arrange
    with tempfile.NamedTemporaryFile(mode="w", suffix=".json", delete=False) as f:
        trainset_data = [
            {
                "user_message": "Book a flight to Paris",
                "dialogue_history": "",
                "current_slots": "{}",
                "available_actions": '["book_flight"]',
                "current_flow": "none",
                "structured_command": "book_flight",
                "extracted_slots": '{"destination": "Paris"}',
                "confidence": "0.9",
                "reasoning": "Clear intent",
            }
        ]
        json.dump(trainset_data, f)
        temp_path = Path(f.name)

    try:
        # Act
        examples = _load_trainset_from_file(temp_path)

        # Assert
        assert len(examples) == 1
        assert examples[0].user_message == "Book a flight to Paris"
        assert examples[0].structured_command == "book_flight"
    finally:
        # Cleanup
        temp_path.unlink()


def test_load_trainset_from_file_not_found():
    """Test loading trainset from non-existent file raises FileNotFoundError"""
    # Arrange
    non_existent = Path("/nonexistent/trainset.json")

    # Act & Assert
    with pytest.raises(FileNotFoundError, match="Trainset file not found"):
        _load_trainset_from_file(non_existent)


def test_load_trainset_from_file_invalid_json():
    """Test loading trainset from invalid JSON raises ValueError"""
    # Arrange
    with tempfile.NamedTemporaryFile(mode="w", suffix=".json", delete=False) as f:
        f.write("not valid json")
        temp_path = Path(f.name)

    try:
        # Act & Assert
        with pytest.raises((ValueError, json.JSONDecodeError)):
            _load_trainset_from_file(temp_path)
    finally:
        # Cleanup
        temp_path.unlink()


def test_load_trainset_from_file_not_array():
    """Test loading trainset from non-array JSON raises ValueError"""
    # Arrange
    with tempfile.NamedTemporaryFile(mode="w", suffix=".json", delete=False) as f:
        json.dump({"not": "an array"}, f)
        temp_path = Path(f.name)

    try:
        # Act & Assert
        with pytest.raises(ValueError, match="must contain a JSON array"):
            _load_trainset_from_file(temp_path)
    finally:
        # Cleanup
        temp_path.unlink()


def test_optimize_optimize_success(tmp_path, monkeypatch):
    """Test optimize command success path"""
    # Arrange
    import json

    from soni.du.modules import SoniDU

    trainset_file = tmp_path / "trainset.json"
    trainset_data = [
        {
            "user_message": "Book a flight",
            "dialogue_history": "",
            "current_slots": "{}",
            "available_actions": '["book_flight"]',
            "current_flow": "none",
            "structured_command": "book_flight",
            "extracted_slots": "{}",
            "confidence": "0.9",
            "reasoning": "Test",
        }
    ]
    trainset_file.write_text(json.dumps(trainset_data))

    # Mock optimize_soni_du to avoid actual optimization
    def mock_optimize(*args, **kwargs):
        return SoniDU(), {
            "baseline_accuracy": 0.5,
            "optimized_accuracy": 0.8,
            "improvement_pct": 30.0,
            "total_time": 10.5,
        }

    monkeypatch.setattr("soni.cli.optimize.optimize_soni_du", mock_optimize)

    runner = CliRunner()

    # Act
    result = runner.invoke(
        app, ["optimize", "optimize", "--trainset", str(trainset_file), "--trials", "1"]
    )

    # Assert
    assert result.exit_code == 0
    assert "Baseline accuracy:" in result.stdout
    assert "Optimized accuracy:" in result.stdout


def test_optimize_load_success(tmp_path, monkeypatch):
    """Test load command success path"""
    # Arrange
    from soni.du.modules import SoniDU

    module_file = tmp_path / "module.json"
    module_file.write_text("{}")  # Dummy file

    # Mock load_optimized_module
    def mock_load(path):
        return SoniDU()

    monkeypatch.setattr("soni.cli.optimize.load_optimized_module", mock_load)

    runner = CliRunner()

    # Act
    result = runner.invoke(app, ["optimize", "load", "--module", str(module_file)])

    # Assert
    assert result.exit_code == 0
    assert "Module loaded successfully" in result.stdout


def test_load_trainset_from_file_empty_array():
    """Test loading empty trainset returns empty list"""
    # Arrange
    with tempfile.NamedTemporaryFile(mode="w", suffix=".json", delete=False) as f:
        json.dump([], f)
        temp_path = Path(f.name)

    try:
        # Act
        examples = _load_trainset_from_file(temp_path)

        # Assert
        assert len(examples) == 0
        assert isinstance(examples, list)
    finally:
        # Cleanup
        temp_path.unlink()
