"""Tests for RuntimeLoop."""

from unittest.mock import AsyncMock, Mock

import pytest
from langgraph.checkpoint.memory import MemorySaver

from soni.core.config import FlowConfig, SoniConfig, StepConfig
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
        # We need a flow that says something or default response
        config = SoniConfig(
            flows={
                "greet": FlowConfig(
                    description="Greets user",
                    steps=[StepConfig(step="say_hello", type="say", message="Hello world")],
                )
            }
        )

        runtime = RuntimeLoop(config)
        # We mock SoniDU to return a command that starts the flow, or rely on defaults?
        # If we rely on real SoniDU, it might need real prompt logic or mocking.
        # Ideally we test RuntimeLoop integration.
        # For simplicity, let's mock the DU inside runtime to force a path.

        # Initialize first so we can patch components
        await runtime.initialize()

        # Mock DU to return start_flow('greet') command
        from soni.du.models import Command, NLUOutput

        mock_du = Mock()
        mock_du.aforward = AsyncMock(
            return_value=NLUOutput(commands=[Command(command_type="start_flow", flow_name="greet")])
        )
        runtime.du = mock_du

        # Ac
        response = await runtime.process_message("Hi")

        # Asser
        # The 'say' node sets active output. The runtime should return it.
        # Wait, 'say' node creates a response message in messages list or returns a dict?
        # SayNodeFactory returns {"messages": [AIMessage(...)]} usually.
        # And DialogueState reducer adds it.
        # RuntimeLoop should return `state["last_response"]` or extract from messages.
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
        mock_du.aforward = AsyncMock(return_value=NLUOutput(commands=[]))
        runtime.du = mock_du

        # First turn
        await runtime.process_message("Hi", user_id="user1")
        state1 = await runtime.get_state("user1")
        assert state1["turn_count"] == 1

        # Second turn
        await runtime.process_message("Second", user_id="user1")
        state2 = await runtime.get_state("user1")
        assert state2["turn_count"] == 2
