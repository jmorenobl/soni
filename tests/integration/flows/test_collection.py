"""Integration test for M2: Collect + Interrupt (M4 - NLU-driven)."""

import pytest
from langgraph.checkpoint.memory import MemorySaver

from soni.config.models import CollectStepConfig, FlowConfig, SayStepConfig, SoniConfig
from soni.runtime.loop import RuntimeLoop


@pytest.mark.asyncio
async def test_collect_and_greet():
    """Two-turn conversation: collect name, then greet.

    NLU detects intent from flow description and triggers the flow.
    """
    # Arrange - flow with description for NLU to match
    config = SoniConfig(
        flows={
            "greet": FlowConfig(
                description="Greet user by asking their name first",
                steps=[
                    CollectStepConfig(step="ask", slot="name", message="What is your name?"),
                    SayStepConfig(step="hello", message="Hello, {name}!"),
                ],
            )
        }
    )
    checkpointer = MemorySaver()

    # Act - Turn 1: User triggers greet intent
    async with RuntimeLoop(config, checkpointer=checkpointer) as runtime:
        response1 = await runtime.process_message("I want to be greeted", user_id="test")

    # Assert - Turn 1: Should be the prompt from CollectNode
    assert "What is your name?" in response1

    # Act - Turn 2: User provides name
    async with RuntimeLoop(config, checkpointer=checkpointer) as runtime:
        response2 = await runtime.process_message("Alice", user_id="test")

    # Assert - Turn 2: Should be the greeting with filled slot
    assert "Hello, Alice!" in response2
