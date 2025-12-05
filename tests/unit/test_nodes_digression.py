"""Tests for handle_digression node."""

from unittest.mock import MagicMock

import pytest

from soni.core.state import create_empty_state
from soni.dm.nodes.handle_digression import handle_digression_node


@pytest.mark.asyncio
async def test_handle_digression_success():
    """Test handle digression with valid command."""
    # Arrange
    state = create_empty_state()
    state["nlu_result"] = {
        "command": "what_time",
    }

    mock_runtime = MagicMock()
    mock_runtime.context = {}

    # Act
    result = await handle_digression_node(state, mock_runtime)

    # Assert
    assert result["conversation_state"] == "generating_response"
    assert "last_response" in result
    assert result["digression_depth"] == 1
