"""Unit tests for error hierarchy."""
import pytest

from soni.core.errors import (
    ActionError,
    ConfigError,
    FlowError,
    FlowStackError,
    NLUError,
    SoniError,
    ValidationError,
)


def test_soni_error_is_base_exception():
    """
    GIVEN SoniError
    WHEN verified
    THEN it is a subclass of Exception
    """
    assert issubclass(SoniError, Exception)


def test_error_hierarchy():
    """
    GIVEN specific errors
    WHEN verified
    THEN they inherit from correct parents
    """
    assert issubclass(ConfigError, SoniError)
    assert issubclass(FlowError, SoniError)
    assert issubclass(FlowStackError, FlowError)
    assert issubclass(ValidationError, SoniError)
    assert issubclass(ActionError, SoniError)
    assert issubclass(NLUError, SoniError)


def test_error_instantiation():
    """
    GIVEN an error class
    WHEN instantiated with message
    THEN check it stores the message
    """
    err = ConfigError("Config missing")
    assert str(err) == "Config missing"
