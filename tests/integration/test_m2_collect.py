"""Integration test for M2: Collect + Interrupt."""

import pytest
from langgraph.checkpoint.memory import MemorySaver

from soni.config.models import CollectStepConfig, FlowConfig, SayStepConfig, SoniConfig
from soni.runtime.loop import RuntimeLoop


@pytest.mark.asyncio
async def test_collect_and_greet():
    """Two-turn conversation: collect name, then greet."""
    # Arrange
    config = SoniConfig(
        flows={
            "greet": FlowConfig(
                steps=[
                    CollectStepConfig(step="ask", slot="name", message="What is your name?"),
                    SayStepConfig(step="hello", message="Hello, {name}!"),
                ]
            )
        }
    )
    checkpointer = MemorySaver()

    # Act - Turn 1
    # We use explicit user_id="test" to ensure persistent thread ID
    async with RuntimeLoop(config, checkpointer=checkpointer) as runtime:
        response1 = await runtime.process_message("hi", user_id="test")

    # Assert - Turn 1
    # Should be the prompt from CollectNode
    assert "What is your name?" in response1

    # Act - Turn 2
    # New runtime instance with SAME checkpointer -> should resume
    async with RuntimeLoop(config, checkpointer=checkpointer) as runtime:
        response2 = await runtime.process_message("Alice", user_id="test")

    # Assert - Turn 2
    # Should be the greeting with filled slot
    assert "Hello, Alice!" in response2
