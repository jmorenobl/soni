"""M4: NLU Integration Tests.

Tests verify that NLU correctly processes user messages and generates
commands that the DM understands and executes.

Note: Uses MockCommandGenerator from conftest.py for deterministic testing.
MockCommandGenerator always returns StartFlow for the first available flow.
"""

import pytest

from soni.config.models import CollectStepConfig, FlowConfig, SayStepConfig, SoniConfig
from soni.runtime.loop import RuntimeLoop


@pytest.mark.asyncio
async def test_nlu_triggers_flow():
    """NLU detects intent and triggers appropriate flow.

    MockCommandGenerator returns StartFlow for first flow in config.
    """
    # Arrange - two flows, NLU should trigger first one
    config = SoniConfig(
        flows={
            "check_balance": FlowConfig(
                description="Check account balance",
                steps=[SayStepConfig(step="balance", message="Your balance is $1,000.")],
            ),
            "transfer": FlowConfig(
                description="Transfer funds",
                steps=[SayStepConfig(step="transfer", message="Transfer initiated.")],
            ),
        }
    )

    # Act - any message with MockCommandGenerator triggers first flow
    async with RuntimeLoop(config) as runtime:
        response = await runtime.process_message("I want to check my account")

    # Assert - first flow executed
    assert "balance" in response.lower() or "$1,000" in response


@pytest.mark.asyncio
async def test_nlu_with_slot_collection():
    """NLU triggers flow with slot collection."""
    # Arrange
    config = SoniConfig(
        flows={
            "greeting": FlowConfig(
                description="Greet user by name",
                steps=[
                    CollectStepConfig(step="ask", slot="name", message="What's your name?"),
                    SayStepConfig(step="greet", message="Nice to meet you, {name}!"),
                ],
            )
        }
    )

    # Act - first turn triggers flow, asks for name
    from langgraph.checkpoint.memory import MemorySaver

    checkpointer = MemorySaver()

    async with RuntimeLoop(config, checkpointer=checkpointer) as runtime:
        response1 = await runtime.process_message("Hello", user_id="test")

    assert "name" in response1.lower()

    # Turn 2 - provide name
    async with RuntimeLoop(config, checkpointer=checkpointer) as runtime:
        response2 = await runtime.process_message("Alice", user_id="test")

    assert "Alice" in response2


@pytest.mark.asyncio
async def test_nlu_empty_message_returns_no_commands():
    """Empty message should not trigger any flow."""
    # Arrange
    config = SoniConfig(
        flows={
            "test": FlowConfig(
                description="Test flow", steps=[SayStepConfig(step="say", message="Hello!")]
            )
        }
    )

    # Act - empty message
    async with RuntimeLoop(config) as runtime:
        response = await runtime.process_message("")

    # Assert - should get "no flow" response
    assert "help" in response.lower() or "what would you like" in response.lower()


@pytest.mark.asyncio
async def test_understand_node_builds_dialogue_context():
    """Verify understand_node correctly builds DialogueContext for NLU."""
    # This tests the internal flow: user message → understand_node → commands
    config = SoniConfig(
        flows={
            "flow_a": FlowConfig(
                description="First flow",
                steps=[SayStepConfig(step="say_a", message="Flow A response")],
            ),
        }
    )

    async with RuntimeLoop(config) as runtime:
        response = await runtime.process_message("trigger flow")

    # MockSoniDU should have received the context and returned StartFlow
    assert "Flow A" in response
