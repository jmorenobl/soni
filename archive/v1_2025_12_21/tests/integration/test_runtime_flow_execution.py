from unittest.mock import AsyncMock, Mock

import pytest
from langgraph.checkpoint.memory import MemorySaver

from soni.config import FlowConfig, SoniConfig
from soni.config.steps import CollectStepConfig, SayStepConfig
from soni.core.commands import SetSlot, StartFlow
from soni.du.models import NLUOutput
from soni.runtime.loop import RuntimeLoop


@pytest.mark.asyncio
async def test_runtime_simple_flow_execution():
    """
    Test correct execution of a simple flow:
    1. Start flow 'greeting'
    2. Collect 'name'
    3. Say hello
    """
    # 1. Config
    config = SoniConfig(
        flows={
            "greeting": FlowConfig(
                description="Greets the user",
                steps=[
                    CollectStepConfig(step="ask_name", slot="name", message="What is your name?"),
                    SayStepConfig(step="say_hello", message="Hello {name}!"),
                ],
            )
        }
    )

    # 3. Mock NLU (Crucial for deterministic integration test)
    # We simulate the DU decision making
    mock_du = Mock()

    # Turn 1: User says "Hi" -> NLU starts 'greeting'
    mock_du.acall = AsyncMock(return_value=NLUOutput(commands=[StartFlow(flow_name="greeting")]))

    # 2. Runtime
    checkpointer = MemorySaver()
    runtime = RuntimeLoop(config, checkpointer=checkpointer, du=mock_du)
    await runtime.initialize()

    response1 = await runtime.process_message("Hi", user_id="test_user")

    # Expectation: System starts flow, hits 'collect' step, returns question
    assert "What is your name?" in response1
    state1 = await runtime.get_state("test_user")
    assert state1 is not None
    # Check if flow stack is active? Accessing internal state for deep verification
    # But public API is better. 'response1' correctness is the main contract.

    # Turn 2: User says "Jorge" -> NLU sets slot 'name'
    mock_du.acall = AsyncMock(
        return_value=NLUOutput(commands=[SetSlot(slot="name", value="Jorge")])
    )

    response2 = await runtime.process_message("Jorge", user_id="test_user")

    # Expectation: System records slot, advances to 'say', returns greeting
    assert "Hello Jorge!" in response2

    # Verify state persistence (final state)
    state2 = await runtime.get_state("test_user")
    assert state2 is not None

    # Flow completed successfully - stack should be empty (end_flow_node pops it)
    # The correct response "Hello Jorge!" already confirms slots worked correctly
    assert state2["flow_stack"] == [], "Flow should be popped from stack after completion"


@pytest.mark.asyncio
async def test_runtime_flow_persistence():
    """
    Test that RuntimeLoop persists state correctly using the checkpointer.
    We reuse the checkpointer in a new RuntimeLoop instance.
    """
    # 1. Config
    config = SoniConfig(
        flows={
            "status": FlowConfig(
                description="Check status",
                steps=[
                    CollectStepConfig(step="ask_id", slot="user_id", message="ID please?"),
                    SayStepConfig(step="show_status", message="Status OK for {user_id}"),
                ],
            )
        }
    )

    # 2. Shared Checkpointer
    checkpointer = MemorySaver()

    # --- Session A ---
    mock_du1 = Mock()
    mock_du1.acall = AsyncMock(return_value=NLUOutput(commands=[StartFlow(flow_name="status")]))

    runtime1 = RuntimeLoop(config, checkpointer=checkpointer, du=mock_du1)
    await runtime1.initialize()

    await runtime1.process_message("Check status", user_id="user_1")
    # State is now: Active flow 'status', waiting for 'user_id'

    # --- Session B (New Instance) ---
    # Simulates server restart or new request handler
    mock_du2 = Mock()
    # Resume flow: NLU understands slot filling
    mock_du2.acall = AsyncMock(
        return_value=NLUOutput(commands=[SetSlot(slot="user_id", value="123")])
    )

    runtime2 = RuntimeLoop(config, checkpointer=checkpointer, du=mock_du2)
    await runtime2.initialize()

    response = await runtime2.process_message("123", user_id="user_1")

    # Expectation: runtime2 retrieved state from checkpoint and continued flow
    assert "Status OK for 123" in response
