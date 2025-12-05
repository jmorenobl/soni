"""Tests for structured logging."""

import logging

import pytest

from soni.observability.logging import ContextLogger, setup_logging


def test_logging_setup():
    """Test logging configuration."""
    # Arrange & Act
    setup_logging(level="DEBUG")

    # Assert
    logger = logging.getLogger("soni")
    assert logger.level == logging.DEBUG


def test_logging_setup_info_level():
    """Test logging setup with INFO level."""
    # Arrange & Act
    setup_logging(level="INFO")

    # Assert
    logger = logging.getLogger("soni")
    assert logger.level == logging.INFO


def test_context_logger():
    """Test ContextLogger with context."""
    # Arrange
    setup_logging(level="INFO")
    context_logger = ContextLogger("soni.test")

    # Act
    adapter = context_logger.with_context(user_id="test-user", flow="book_flight")

    # Assert
    assert isinstance(adapter, logging.LoggerAdapter)
    assert adapter.extra == {"user_id": "test-user", "flow": "book_flight"}


def test_context_logger_logging():
    """Test ContextLogger actually logs with context."""
    # Arrange
    setup_logging(level="DEBUG")
    context_logger = ContextLogger("soni.test")
    adapter = context_logger.with_context(user_id="test-user")

    # Act & Assert
    # Should not raise
    adapter.info("Test message")
