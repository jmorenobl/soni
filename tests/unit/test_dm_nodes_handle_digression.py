"""Unit tests for handle_digression node.

All tests use mocked dependencies for determinism.
"""

from unittest.mock import MagicMock, patch

import pytest

from soni.dm.nodes.handle_digression import handle_digression_node
from soni.du.models import MessageType, NLUOutput


@pytest.mark.asyncio
async def test_handle_digression_preserves_waiting_for_slot(mock_runtime):
    """Test that handle_digression preserves waiting_for_slot and re-prompts."""
    # Arrange
    from soni.core.state import create_empty_state

    state = create_empty_state()
    state["waiting_for_slot"] = "destination"
    state["current_step"] = "collect_destination"
    state["nlu_result"] = NLUOutput(
        message_type=MessageType.DIGRESSION,
        command="airports",
        confidence=0.9,
    ).model_dump()

    # Mock get_slot_config to return prompt for destination
    destination_slot_config = MagicMock()
    destination_slot_config.prompt = "Where would you like to go?"

    def get_slot_config_side_effect(context, slot_name):
        if slot_name == "destination":
            return destination_slot_config
        raise KeyError(f"Slot {slot_name} not found")

    with patch("soni.core.state.get_slot_config", side_effect=get_slot_config_side_effect):
        # Act
        result = await handle_digression_node(state, mock_runtime)

    # Assert
    # Should preserve waiting_for_slot
    assert result["waiting_for_slot"] == "destination"
    # Should preserve current_step
    assert result["current_step"] == "collect_destination"
    # Should be in waiting_for_slot state
    assert result["conversation_state"] == "waiting_for_slot"
    # Should include both digression response and slot re-prompt
    last_response = result["last_response"]
    assert (
        "I understand you're asking about airports" in last_response
        or "airports" in last_response.lower()
    )
    assert "Where would you like to go?" in last_response
    # Should increment digression_depth
    assert result["digression_depth"] == 1
    assert result["last_digression_type"] == "airports"


@pytest.mark.asyncio
async def test_handle_digression_no_waiting_for_slot(mock_runtime):
    """Test that handle_digression works normally when no slot is waiting."""
    # Arrange
    from soni.core.state import create_empty_state

    state = create_empty_state()
    # No waiting_for_slot
    state["nlu_result"] = NLUOutput(
        message_type=MessageType.DIGRESSION,
        command="help",
        confidence=0.9,
    ).model_dump()

    # Act
    result = await handle_digression_node(state, mock_runtime)

    # Assert
    # Should not have waiting_for_slot
    assert "waiting_for_slot" not in result
    # Should be in generating_response state
    assert result["conversation_state"] == "generating_response"
    # Should include digression response
    assert (
        "I understand you're asking about help" in result["last_response"]
        or "help" in result["last_response"].lower()
    )
    # Should increment digression_depth
    assert result["digression_depth"] == 1
    assert result["last_digression_type"] == "help"


@pytest.mark.asyncio
async def test_handle_digression_uses_generic_prompt_when_config_missing(mock_runtime):
    """Test that handle_digression uses generic prompt when slot config is missing."""
    # Arrange
    from soni.core.state import create_empty_state

    state = create_empty_state()
    state["waiting_for_slot"] = "destination"
    state["current_step"] = "collect_destination"
    state["nlu_result"] = NLUOutput(
        message_type=MessageType.DIGRESSION,
        command="airports",
        confidence=0.9,
    ).model_dump()

    # Mock get_slot_config to raise KeyError (slot config not found)
    def get_slot_config_side_effect(context, slot_name):
        raise KeyError(f"Slot {slot_name} not found")

    with patch("soni.core.state.get_slot_config", side_effect=get_slot_config_side_effect):
        # Act
        result = await handle_digression_node(state, mock_runtime)

    # Assert
    # Should preserve waiting_for_slot
    assert result["waiting_for_slot"] == "destination"
    # Should use generic prompt
    last_response = result["last_response"]
    assert "Please provide your destination" in last_response
    # Should still include digression response
    assert "airports" in last_response.lower() or "I understand" in last_response


@pytest.mark.asyncio
async def test_handle_digression_no_command(mock_runtime):
    """Test that handle_digression handles missing command gracefully."""
    # Arrange
    from soni.core.state import create_empty_state

    state = create_empty_state()
    state["waiting_for_slot"] = "origin"
    state["nlu_result"] = NLUOutput(
        message_type=MessageType.DIGRESSION,
        command=None,
        confidence=0.9,
    ).model_dump()

    # Mock get_slot_config
    origin_slot_config = MagicMock()
    origin_slot_config.prompt = "Which city are you departing from?"

    def get_slot_config_side_effect(context, slot_name):
        if slot_name == "origin":
            return origin_slot_config
        raise KeyError(f"Slot {slot_name} not found")

    with patch("soni.core.state.get_slot_config", side_effect=get_slot_config_side_effect):
        # Act
        result = await handle_digression_node(state, mock_runtime)

    # Assert
    # Should preserve waiting_for_slot
    assert result["waiting_for_slot"] == "origin"
    # Should include default digression response
    last_response = result["last_response"]
    assert "I understand you have a question" in last_response or "How can I help" in last_response
    # Should include slot prompt
    assert "Which city are you departing from?" in last_response
