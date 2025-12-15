from typing import cast
from unittest.mock import AsyncMock, Mock

import pytest

from soni.core.commands import (
    AffirmConfirmation,
    CancelFlow,
    Clarify,
    CorrectSlot,
    DenyConfirmation,
    StartFlow,
)
from soni.core.constants import ConversationState
from soni.core.patterns.cancellation import CancellationPattern
from soni.core.patterns.clarification import ClarificationPattern
from soni.core.patterns.confirmation import ConfirmationPattern
from soni.core.patterns.correction import CorrectionPattern
from soni.core.patterns.defaults import register_default_patterns
from soni.core.patterns.registry import PatternRegistry
from soni.core.types import DialogueState
from soni.dm.executor import _execute_single_command


@pytest.fixture
def clean_registry():
    """Clear registry before and after test."""
    PatternRegistry.clear()
    yield
    PatternRegistry.clear()


@pytest.fixture
def registered_defaults(clean_registry):
    """Register default patterns."""
    register_default_patterns()


@pytest.mark.asyncio
async def test_registry_management(clean_registry):
    """Test registering and retrieving patterns."""
    assert PatternRegistry.get_all() == []

    p = CorrectionPattern()
    PatternRegistry.register(p)

    assert PatternRegistry.get("correction") is p
    assert len(PatternRegistry.get_all()) == 1


@pytest.mark.asyncio
async def test_correction_pattern():
    """Test Correction pattern matches and handles."""
    p = CorrectionPattern()
    cmd = CorrectSlot(slot_name="city", new_value="Paris")
    state = cast(DialogueState, {})
    context = Mock()

    assert p.matches(cmd, state)
    assert not p.matches(StartFlow(flow_name="test"), state)

    result = await p.handle(cmd, state, context)
    assert result["conversation_state"] == ConversationState.WAITING_FOR_SLOT
    assert "Updated city" in result["last_response"]


@pytest.mark.asyncio
async def test_clarification_pattern():
    p = ClarificationPattern()
    cmd = Clarify(topic="usage")
    state = cast(DialogueState, {})
    context = Mock()

    assert p.matches(cmd, state)
    result = await p.handle(cmd, state, context)
    assert "usage" in result["last_response"]


@pytest.mark.asyncio
async def test_cancellation_pattern():
    p = CancellationPattern()
    cmd = CancelFlow(reason="bored")
    state = cast(DialogueState, {})
    context = Mock()

    assert p.matches(cmd, state)
    result = await p.handle(cmd, state, context)
    assert result["conversation_state"] == ConversationState.IDLE
    assert result["flow_stack"] == []


@pytest.mark.asyncio
async def test_confirmation_pattern():
    p = ConfirmationPattern()

    # Affirm
    cmd_yes = AffirmConfirmation()
    state = cast(DialogueState, {})
    assert p.matches(cmd_yes, state)
    result = await p.handle(cmd_yes, state, Mock())
    assert result["conversation_state"] == ConversationState.READY_FOR_ACTION

    # Deny
    cmd_no = DenyConfirmation(slot_to_change="date")
    result = await p.handle(cmd_no, state, Mock())
    assert result["conversation_state"] == ConversationState.WAITING_FOR_SLOT


@pytest.mark.asyncio
async def test_executor_dispatches_to_pattern(registered_defaults):
    """Test that executor finds the pattern in registry."""
    cmd = CorrectSlot(slot_name="city", new_value="Madrid")
    state = cast(DialogueState, {})
    context = Mock()

    result = await _execute_single_command(cmd, state, context)

    # Should come from CorrectionPattern
    assert "Updated city" in result.get("last_response", "")


@pytest.mark.asyncio
async def test_chitchat_pattern():
    from soni.core.commands import ChitChat
    from soni.core.patterns.chitchat import ChitChatPattern

    p = ChitChatPattern()
    cmd = ChitChat(response_hint="Fees are 5%")
    state = cast(DialogueState, {})
    context = Mock()

    assert p.matches(cmd, state)
    result = await p.handle(cmd, state, context)
    assert result["last_response"] == "Fees are 5%"
