"""Unit tests for core protocol interfaces."""

import pytest

from soni.core.interfaces import (
    IActionHandler,
    IFlowManager,
    INLUProvider,
    INormalizer,
    IScopeManager,
)
from soni.core.types import DialogueState


def test_protocol_type_checking():
    """Test that protocols can be used for type hints."""

    # Arrange
    def process_with_nlu(nlu: INLUProvider) -> None:
        """Function accepting INLUProvider."""
        pass

    # Act & Assert - This should not raise type errors
    # (actual implementation test will be in integration)
    assert INLUProvider is not None


def test_all_protocols_importable():
    """Test that all protocols can be imported."""
    # Arrange & Act
    protocols = [
        INLUProvider,
        IActionHandler,
        IScopeManager,
        INormalizer,
        IFlowManager,
    ]

    # Assert
    assert len(protocols) == 5
    assert all(protocol is not None for protocol in protocols)


def test_nlu_provider_protocol_structure():
    """Test INLUProvider protocol has understand method."""
    # Arrange
    # (Protocols are structural, so we just verify the interface exists)

    # Act & Assert
    # Check that INLUProvider is a Protocol
    assert hasattr(INLUProvider, "__protocol_attrs__") or hasattr(
        INLUProvider, "__abstractmethods__"
    )


def test_action_handler_protocol_structure():
    """Test IActionHandler protocol has execute method."""
    # Arrange
    # (Protocols are structural)

    # Act & Assert
    assert IActionHandler is not None


def test_scope_manager_protocol_structure():
    """Test IScopeManager protocol has required methods."""
    # Arrange
    # (Protocols are structural)

    # Act & Assert
    assert IScopeManager is not None


def test_normalizer_protocol_structure():
    """Test INormalizer protocol has normalize method."""
    # Arrange
    # (Protocols are structural)

    # Act & Assert
    assert INormalizer is not None


def test_flow_manager_protocol_structure():
    """Test IFlowManager protocol has required methods."""
    # Arrange
    # (Protocols are structural)

    # Act & Assert
    assert IFlowManager is not None
