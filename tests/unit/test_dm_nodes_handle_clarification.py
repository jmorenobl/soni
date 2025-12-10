"""Unit tests for handle_clarification node.

All tests use mocked NLU for determinism.

Design Reference: docs/design/10-dsl-specification/06-patterns.md:19
Pattern: "Clarification: User asks why information is needed → Explain, re-prompt same slot"
"""

from unittest.mock import AsyncMock, MagicMock

import pytest

from soni.dm.nodes.handle_clarification import handle_clarification_node
from soni.du.models import MessageType, NLUOutput

# === TESTS FOR CLARIFICATION BEHAVIOR ===


@pytest.mark.asyncio
async def test_handle_clarification_explains_slot(create_state_with_flow, mock_runtime):
    """
    User asks why slot is needed - should explain and re-prompt.

    Design Reference: docs/design/10-dsl-specification/06-patterns.md:19
    Pattern: "Clarification: User asks why information is needed → Explain, re-prompt same slot"
    """
    # Arrange
    state = create_state_with_flow("book_flight")
    state["waiting_for_slot"] = "email"
    state["conversation_state"] = "waiting_for_slot"
    state["nlu_result"] = {
        "message_type": MessageType.CLARIFICATION.value,
        "clarification_target": "email",
    }

    # Mock step_manager to return step config with description
    mock_step_config = MagicMock()
    mock_step_config.slot = "email"
    mock_step_config.description = "to send booking confirmation"
    mock_step_config.type = "collect"
    mock_runtime.context["step_manager"].get_current_step_config.return_value = mock_step_config

    # Act
    result = await handle_clarification_node(state, mock_runtime)

    # Assert
    # Must explain why slot is needed
    assert "booking confirmation" in result["last_response"] or "email" in result["last_response"]
    # Must re-prompt for same slot
    assert result["waiting_for_slot"] == "email"
    # Must not change conversation_state
    assert result["conversation_state"] == "waiting_for_slot"


@pytest.mark.asyncio
async def test_handle_clarification_preserves_flow_stack(create_state_with_flow, mock_runtime):
    """
    Clarification doesn't modify flow stack (design principle).

    Design Reference: docs/design/10-dsl-specification/06-patterns.md:201
    Principle: "DigressionHandler coordinates question/help handling. Does NOT modify flow stack"
    """
    # Arrange
    state = create_state_with_flow("book_flight")
    state["waiting_for_slot"] = "email"
    original_stack = state["flow_stack"].copy()

    state["nlu_result"] = {
        "message_type": MessageType.CLARIFICATION.value,
        "clarification_target": "email",
    }

    mock_step_config = MagicMock()
    mock_step_config.slot = "email"
    mock_step_config.description = "for booking confirmation"
    mock_runtime.context["step_manager"].get_current_step_config.return_value = mock_step_config

    # Act
    result = await handle_clarification_node(state, mock_runtime)

    # Assert
    # CRITICAL: flow_stack must NOT be modified
    assert result.get("flow_stack", state["flow_stack"]) == original_stack, (
        "Clarification must NOT modify flow stack (design principle)"
    )


@pytest.mark.asyncio
async def test_handle_clarification_re_prompts_same_slot(create_state_with_flow, mock_runtime):
    """Clarification re-prompts for the same slot."""
    # Arrange
    state = create_state_with_flow("book_flight")
    state["waiting_for_slot"] = "destination"
    state["conversation_state"] = "waiting_for_slot"

    state["nlu_result"] = {
        "message_type": MessageType.CLARIFICATION.value,
        "clarification_target": "destination",
    }

    mock_step_config = MagicMock()
    mock_step_config.slot = "destination"
    mock_step_config.description = "to find available flights"
    mock_step_config.type = "collect"
    mock_runtime.context["step_manager"].get_current_step_config.return_value = mock_step_config

    # Act
    result = await handle_clarification_node(state, mock_runtime)

    # Assert
    assert result["waiting_for_slot"] == "destination"
    assert result["conversation_state"] == "waiting_for_slot"
    assert (
        "destination" in result["last_response"].lower()
        or "where" in result["last_response"].lower()
    )


@pytest.mark.asyncio
async def test_handle_clarification_without_description(create_state_with_flow, mock_runtime):
    """Clarification when step has no description."""
    # Arrange
    state = create_state_with_flow("book_flight")
    state["waiting_for_slot"] = "origin"
    state["conversation_state"] = "waiting_for_slot"

    state["nlu_result"] = {
        "message_type": MessageType.CLARIFICATION.value,
        "clarification_target": "origin",
    }

    # Mock step config without description
    mock_step_config = MagicMock()
    mock_step_config.slot = "origin"
    mock_step_config.description = None
    mock_step_config.type = "collect"
    mock_runtime.context["step_manager"].get_current_step_config.return_value = mock_step_config

    # Act
    result = await handle_clarification_node(state, mock_runtime)

    # Assert
    # Should handle gracefully even without description
    assert result["waiting_for_slot"] == "origin"
    assert result["conversation_state"] == "waiting_for_slot"
    assert len(result["last_response"]) > 0


@pytest.mark.asyncio
async def test_handle_clarification_during_confirmation(create_state_with_flow, mock_runtime):
    """Clarification during confirmation step."""
    # Arrange
    state = create_state_with_flow("book_flight")
    state["conversation_state"] = "confirming"
    state["nlu_result"] = {
        "message_type": MessageType.CLARIFICATION.value,
        "clarification_target": "email",
    }

    mock_step_config = MagicMock()
    mock_step_config.slot = "email"
    mock_step_config.description = "for booking confirmation"
    mock_step_config.type = "confirm"
    mock_runtime.context["step_manager"].get_current_step_config.return_value = mock_step_config

    # Act
    result = await handle_clarification_node(state, mock_runtime)

    # Assert
    # Should handle appropriately during confirmation
    assert (
        "email" in result["last_response"].lower()
        or "confirmation" in result["last_response"].lower()
    )
    # State should be preserved or transition appropriately
    assert "conversation_state" in result
