"""Tests for RuntimeLoop."""

from unittest.mock import AsyncMock, Mock

import pytest
from langgraph.checkpoint.memory import MemorySaver

from soni.config import FlowConfig, SayStepConfig, SoniConfig
from soni.runtime.loop import RuntimeLoop


class TestRuntimeLoop:
    """Tests for RuntimeLoop execution."""

    @pytest.mark.asyncio
    async def test_process_message_returns_response(self):
        """
        GIVEN initialized runtime
        WHEN processing message
        THEN returns response string
        """
        # Arrange
        # Minimal config to produce a response
        config = SoniConfig(
            flows={
                "greet": FlowConfig(
                    description="Greets user",
                    steps=[SayStepConfig(step="say_hello", type="say", message="Hello world")],
                )
            }
        )

        runtime = RuntimeLoop(config)
        # Initialize first so we can patch components
        await runtime.initialize()

        # Mock DU to return start_flow('greet') command
        from soni.core.commands import StartFlow
        from soni.du.models import NLUOutput

        mock_du = Mock()
        mock_du.acall = AsyncMock(return_value=NLUOutput(commands=[StartFlow(flow_name="greet")]))
        runtime.du = mock_du

        # Act
        response = await runtime.process_message("Hi")

        # Assert
        assert "Hello world" in response

    @pytest.mark.asyncio
    async def test_state_persists_between_messages(self):
        """
        GIVEN runtime with checkpointer
        WHEN separate calls with same user_id
        THEN state is preserved
        """
        config = SoniConfig(flows={})
        runtime = RuntimeLoop(config, checkpointer=MemorySaver())
        await runtime.initialize()

        # MOCK DU to avoid dspy error
        from soni.du.models import NLUOutput

        mock_du = Mock()
        mock_du.acall = AsyncMock(return_value=NLUOutput(commands=[]))
        runtime.du = mock_du

        # First turn
        await runtime.process_message("Hi", user_id="user1")
        state1 = await runtime.get_state("user1")
        assert state1 is not None
        assert state1["turn_count"] == 1

        # Second turn
        await runtime.process_message("Second", user_id="user1")
        state2 = await runtime.get_state("user1")
        assert state2 is not None
        assert state2["turn_count"] == 2
