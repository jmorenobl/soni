"""Tests for PendingTaskHandler (SRP)."""

import pytest

from soni.core.message_sink import BufferedMessageSink
from soni.core.pending_task import collect, confirm, inform
from soni.dm.orchestrator.task_handler import (
    PendingTaskHandler,
    TaskAction,
)


class TestPendingTaskHandler:
    """Tests for PendingTaskHandler."""

    @pytest.mark.asyncio
    async def test_handle_collect_returns_interrupt(self):
        """Test that CollectTask always triggers interrupt."""
        # Arrange
        sink = BufferedMessageSink()
        handler = PendingTaskHandler(sink)
        task = collect(prompt="Enter amount", slot="amount")

        # Act
        result = await handler.handle(task)

        # Assert
        assert result.action == TaskAction.INTERRUPT
        assert result.task == task
        assert sink.messages == []  # Collect doesn't send message

    @pytest.mark.asyncio
    async def test_handle_confirm_returns_interrupt(self):
        """Test that ConfirmTask always triggers interrupt."""
        # Arrange
        sink = BufferedMessageSink()
        handler = PendingTaskHandler(sink)
        task = confirm(prompt="Proceed?")

        # Act
        result = await handler.handle(task)

        # Assert
        assert result.action == TaskAction.INTERRUPT
        assert result.task == task

    @pytest.mark.asyncio
    async def test_handle_inform_without_wait_sends_and_continues(self):
        """Test that InformTask without wait sends message and continues."""
        # Arrange
        sink = BufferedMessageSink()
        handler = PendingTaskHandler(sink)
        task = inform(prompt="Your balance is $1,234")

        # Act
        result = await handler.handle(task)

        # Assert
        assert result.action == TaskAction.CONTINUE
        assert sink.messages == ["Your balance is $1,234"]

    @pytest.mark.asyncio
    async def test_handle_inform_with_wait_sends_and_interrupts(self):
        """Test that InformTask with wait_for_ack sends message and interrupts."""
        # Arrange
        sink = BufferedMessageSink()
        handler = PendingTaskHandler(sink)
        task = inform(prompt="Transfer complete!", wait_for_ack=True)

        # Act
        result = await handler.handle(task)

        # Assert
        assert result.action == TaskAction.INTERRUPT
        assert result.task == task
        assert sink.messages == ["Transfer complete!"]
