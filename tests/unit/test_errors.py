"""Unit tests for Soni exceptions"""

from soni.core.errors import (
    ActionNotFoundError,
    CompilationError,
    ConfigurationError,
    NLUError,
    PersistenceError,
    SoniError,
    ValidationError,
)


def test_soni_error_base():
    """Test base SoniError"""
    error = SoniError("Test error", {"key": "value"})
    assert str(error) == "Test error (key=value)"
    assert error.message == "Test error"
    assert error.context == {"key": "value"}


def test_nlu_error():
    """Test NLUError"""
    error = NLUError("NLU processing failed", {"model": "gpt-4"})
    assert isinstance(error, SoniError)
    assert "NLU processing failed" in str(error)


def test_validation_error():
    """Test ValidationError"""
    error = ValidationError(
        "Invalid value",
        field="destination",
        value="InvalidCity",
        context={"allowed": ["Paris", "London"]},
    )
    assert error.field == "destination"
    assert error.value == "InvalidCity"
    assert "Invalid value" in str(error)


def test_action_not_found_error():
    """Test ActionNotFoundError"""
    error = ActionNotFoundError("search_flights", {"available": ["book_flight"]})
    assert error.action_name == "search_flights"
    assert "search_flights" in str(error)


def test_compilation_error():
    """Test CompilationError"""
    error = CompilationError(
        "Syntax error",
        yaml_path="config.yaml",
        line=42,
        context={"flow": "book_flight"},
    )
    assert error.yaml_path == "config.yaml"
    assert error.line == 42
    assert "Syntax error" in str(error)


def test_configuration_error():
    """Test ConfigurationError"""
    error = ConfigurationError("Missing required field: version")
    assert isinstance(error, SoniError)
    assert "Missing required field" in str(error)


def test_persistence_error():
    """Test PersistenceError"""
    error = PersistenceError("Failed to save state", {"conversation_id": "123"})
    assert isinstance(error, SoniError)
    assert "Failed to save state" in str(error)
