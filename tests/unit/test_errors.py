"""Unit tests for core error classes."""

import pytest

from soni.core.errors import (
    ActionNotFoundError,
    CompilationError,
    ConfigurationError,
    FlowStackLimitError,
    NLUError,
    PersistenceError,
    SoniError,
    ValidationError,
)


def test_base_error_with_context():
    """Test SoniError includes context in message."""
    # Arrange
    error = SoniError(
        "Something failed",
        user_id="123",
        flow="book_flight",
    )

    # Act
    error_message = str(error)

    # Assert
    assert "Something failed" in error_message
    assert "user_id=123" in error_message
    assert "flow=book_flight" in error_message


def test_base_error_without_context():
    """Test SoniError without context."""
    # Arrange & Act
    error = SoniError("Simple error")

    # Assert
    assert str(error) == "Simple error"
    assert error.context == {}


def test_validation_error_inheritance():
    """Test ValidationError is a SoniError."""
    # Arrange & Act
    error = ValidationError("Invalid slot", slot="origin", value="invalid")

    # Assert
    assert isinstance(error, SoniError)
    assert "Invalid slot" in str(error)
    assert "slot=origin" in str(error)
    assert "value=invalid" in str(error)


def test_all_error_types_inherit_from_soni_error():
    """Test all specific error types inherit from SoniError."""
    # Arrange
    error_types = [
        (NLUError, "Test NLU error"),
        (ValidationError, "Test validation error", {"field": "test"}),
        (ActionNotFoundError, "test_action"),
        (FlowStackLimitError, "Stack limit exceeded", {"max_depth": 10}),
        (ConfigurationError, "Config error"),
        (PersistenceError, "Persistence error"),
        (CompilationError, "Compilation error"),
    ]

    # Act & Assert
    for error_data in error_types:
        if len(error_data) == 2:
            error = error_data[0](error_data[1])
        elif len(error_data) == 3:
            error = error_data[0](error_data[1], **error_data[2])
        else:
            error = error_data[0](error_data[1])
        assert isinstance(error, SoniError)
        assert error_data[1] in str(error) or error_data[1] in error.message


def test_flow_stack_limit_error():
    """Test FlowStackLimitError with context."""
    # Arrange & Act
    error = FlowStackLimitError(
        "Flow stack depth limit exceeded",
        current_depth=10,
        flow_name="test_flow",
    )

    # Assert
    assert isinstance(error, SoniError)
    assert "Flow stack depth limit exceeded" in str(error)
    assert "current_depth=10" in str(error)
    assert "flow_name=test_flow" in str(error)
