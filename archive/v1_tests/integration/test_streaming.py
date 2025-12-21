"""Integration tests for streaming functionality."""

from unittest.mock import AsyncMock, Mock

import pytest
from langgraph.checkpoint.memory import MemorySaver

from soni.config import FlowConfig, SoniConfig
from soni.config.steps import CollectStepConfig
from soni.core.commands import StartFlow
from soni.du.models import NLUOutput
from soni.runtime.loop import RuntimeLoop


@pytest.fixture
def streaming_config():
    """Config for streaming tests."""
    return SoniConfig(
        flows={
            "simple_chat": FlowConfig(
                description="Simple chat flow",
                steps=[
                    CollectStepConfig(step="ask_name", slot="name", message="What is your name?"),
                ],
            ),
        }
    )


@pytest.fixture
async def runtime_loop(streaming_config):
    """Runtime with mocked DU for streaming tests."""
    checkpointer = MemorySaver()
    # Mock DU to return a StartFlow command by default
    mock_du = Mock()
    mock_du.acall = AsyncMock(return_value=NLUOutput(commands=[StartFlow(flow_name="simple_chat")]))

    rt = RuntimeLoop(streaming_config, checkpointer=checkpointer, du=mock_du)
    await rt.initialize()
    return rt


@pytest.mark.integration
class TestStreamingIntegration:
    """End-to-end streaming tests."""

    @pytest.mark.asyncio
    async def test_full_conversation_streaming(self, runtime_loop):
        """Test streaming through full conversation flow."""
        chunks = []
        async for chunk in runtime_loop.process_message_streaming("Hello", user_id="stream_user_1"):
            chunks.append(chunk)

        # Should receive multiple chunks (one per node)
        assert len(chunks) > 0

        # At least one chunk should have response content
        # LangGraph updates format: {'node_name': {'field': value}}
        # Our runtime or nodes might set 'last_response' in state.
        has_response = False
        for chunk in chunks:
            for _node_name, updates in chunk.items():
                if isinstance(updates, dict) and "last_response" in updates:
                    has_response = True
                    break
            if has_response:
                break

        assert has_response

    @pytest.mark.asyncio
    async def test_streaming_maintains_state(self, runtime_loop):
        """Test that streaming maintains conversation state."""
        user_id = "stream_user_2"

        # 1. Start flow (DU returns StartFlow by default)
        async for _ in runtime_loop.process_message_streaming("Hi", user_id=user_id):
            pass

        # 2. Second turn
        # Update mock to NOT start flow again (simulate simple slot fill or continue)
        runtime_loop.du.acall = AsyncMock(return_value=NLUOutput(commands=[]))

        async for _chunk in runtime_loop.process_message_streaming("John", user_id=user_id):
            pass

        # State should reflect both messages
        state = await runtime_loop.get_state(user_id)
        assert state is not None
        assert state.get("turn_count", 0) >= 2
