"""Tests for MessageSink interface and implementations."""

import pytest

from soni.core.message_sink import (
    BufferedMessageSink,
    MessageSink,
)


class TestBufferedMessageSink:
    """Tests for BufferedMessageSink implementation."""

    @pytest.mark.asyncio
    async def test_send_appends_message_to_buffer(self):
        """Test that send() appends message to internal buffer."""
        # Arrange
        sink = BufferedMessageSink()

        # Act
        await sink.send("Hello")
        await sink.send("World")

        # Assert
        assert sink.messages == ["Hello", "World"]

    @pytest.mark.asyncio
    async def test_buffer_starts_empty(self):
        """Test that buffer is empty initially."""
        # Arrange & Act
        sink = BufferedMessageSink()

        # Assert
        assert sink.messages == []

    @pytest.mark.asyncio
    async def test_clear_empties_buffer(self):
        """Test that clear() empties the message buffer."""
        # Arrange
        sink = BufferedMessageSink()
        await sink.send("Test")

        # Act
        sink.clear()

        # Assert
        assert sink.messages == []
