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


@pytest.mark.asyncio
async def test_generate_response_uses_confirmation_slot_generic():
    """Test that generate_response uses generic 'confirmation' slot, not domain-specific slots."""
    # Arrange
    state = create_empty_state()
    state["flow_stack"] = [{"flow_id": "test_flow", "flow_name": "test"}]
    state["flow_slots"] = {
        "test_flow": {
            "confirmation": "Order confirmed! Reference: XYZ789",  # Generic slot
            "order_ref": "XYZ789",  # Domain-specific slot (should be ignored)
        }
    }
    state["conversation_state"] = "completed"

    mock_runtime = MagicMock()
    mock_runtime.context = {}

    # Act
    result = await generate_response_node(state, mock_runtime)

    # Assert
    assert result["last_response"] == "Order confirmed! Reference: XYZ789"
    # Should use confirmation slot, NOT domain-specific slot


@pytest.mark.asyncio
async def test_generate_response_no_hardcoded_slot_names():
    """Test that generate_response doesn't check for hardcoded slot names like 'booking_ref'."""
    # Arrange
    state = create_empty_state()
    state["flow_stack"] = [{"flow_id": "test_flow", "flow_name": "test"}]
    state["flow_slots"] = {
        "test_flow": {
            "booking_ref": "ABC123",  # Framework should NOT look for this
            "reservation_id": "XYZ789",  # Or this
            # No "confirmation" slot
        }
    }
    state["conversation_state"] = "idle"

    mock_runtime = MagicMock()
    mock_runtime.context = {}

    # Act
    result = await generate_response_node(state, mock_runtime)

    # Assert
    # Should fall back to default, NOT use booking_ref or reservation_id
    assert result["last_response"] == "How can I help you?"


@pytest.mark.asyncio
async def test_generate_response_works_for_any_domain():
    """Test that response generation is truly domain-agnostic."""
    # Arrange - Simulate restaurant booking domain
    state = create_empty_state()
    state["flow_stack"] = [{"flow_id": "restaurant_flow", "flow_name": "book_table"}]
    state["flow_slots"] = {
        "restaurant_flow": {
            "confirmation": "Table reserved! Confirmation code: TBL456",  # Generic
            "table_number": "12",  # Domain-specific (restaurant)
            "party_size": "4",  # Domain-specific (restaurant)
        }
    }
    state["conversation_state"] = "completed"

    mock_runtime = MagicMock()
    mock_runtime.context = {}

    # Act
    result = await generate_response_node(state, mock_runtime)

    # Assert
    assert result["last_response"] == "Table reserved! Confirmation code: TBL456"
    # Works for restaurant domain without any framework changes!
