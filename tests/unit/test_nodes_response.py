"""Tests for generate_response node."""

from unittest.mock import MagicMock

import pytest

from soni.core.state import create_empty_state
from soni.dm.nodes.generate_response import generate_response_node


@pytest.mark.asyncio
async def test_generate_response_with_action_result():
    """Test generate response with action result."""
    # Arrange
    state = create_empty_state()
    state["action_result"] = {"booking_ref": "BK-123"}

    mock_runtime = MagicMock()
    mock_runtime.context = {}

    # Act
    result = await generate_response_node(state, mock_runtime)

    # Assert
    assert result["conversation_state"] == "idle"
    assert "last_response" in result
    assert "BK-123" in result["last_response"]


@pytest.mark.asyncio
async def test_generate_response_no_action_result():
    """Test generate response without action result."""
    # Arrange
    state = create_empty_state()

    mock_runtime = MagicMock()
    mock_runtime.context = {}

    # Act
    result = await generate_response_node(state, mock_runtime)

    # Assert
    assert result["conversation_state"] == "idle"
    assert "last_response" in result
