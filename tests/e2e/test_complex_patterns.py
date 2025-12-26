import os

import pytest
from langgraph.checkpoint.memory import MemorySaver

# Import banking handlers
import examples.banking.handlers  # noqa: F401
from soni.config.loader import ConfigLoader
from soni.runtime.loop import RuntimeLoop


@pytest.mark.e2e
@pytest.mark.asyncio
async def test_nested_flow_with_multiple_digressions():
    """Test nested flows with multiple digressions."""
    if not os.getenv("OPENAI_API_KEY"):
        pytest.skip("OPENAI_API_KEY not set")

    config = ConfigLoader.load("examples/banking/domain")
    config.settings.rephrase_responses = False

    checkpointer = MemorySaver()
    async with RuntimeLoop(config, checkpointer=checkpointer) as runtime:
        session_id = "complex-test-001"

        # Start transfer flow
        await runtime.process_message("I want to transfer money", user_id=session_id)

        # Digression 1: Check balance
        response1 = await runtime.process_message(
            "Wait, what's my balance first?", user_id=session_id
        )
        # Should ask for account type (balance flow)
        assert "account" in response1.lower() or "checking" in response1.lower()

        # Complete balance check
        await runtime.process_message("My checking account", user_id=session_id)

        # Now continue with transfer - provide beneficiary
        response2 = await runtime.process_message("Transfer $100 to John", user_id=session_id)
        # Should ask for IBAN or next slot
        assert (
            "iban" in response2.lower()
            or "recipient" in response2.lower()
            or "account" in response2.lower()
        )


@pytest.mark.e2e
@pytest.mark.asyncio
async def test_correction_during_confirmation():
    """Test correcting a value during confirmation."""
    if not os.getenv("OPENAI_API_KEY"):
        pytest.skip("OPENAI_API_KEY not set")

    config = ConfigLoader.load("examples/banking/domain")
    config.settings.rephrase_responses = False

    checkpointer = MemorySaver()
    async with RuntimeLoop(config, checkpointer=checkpointer) as runtime:
        session_id = "complex-test-002"

        # Start transfer and provide some slots
        await runtime.process_message("Transfer $100 to John", user_id=session_id)
        await runtime.process_message("ES123", user_id=session_id)
        await runtime.process_message("Checking", user_id=session_id)

        # Now it should ask for concept
        # Correction of amount
        response = await runtime.process_message(
            "Wait, change the amount to $200", user_id=session_id
        )

        # Should confirm the change or just continue with new value
        assert "200" in response.lower() or "concept" in response.lower()


@pytest.mark.e2e
@pytest.mark.asyncio
async def test_cancellation_and_resume():
    """Test canceling a flow and starting a new one."""
    if not os.getenv("OPENAI_API_KEY"):
        pytest.skip("OPENAI_API_KEY not set")

    config = ConfigLoader.load("examples/banking/domain")
    config.settings.rephrase_responses = False

    checkpointer = MemorySaver()
    async with RuntimeLoop(config, checkpointer=checkpointer) as runtime:
        session_id = "complex-test-003"

        # Start transfer
        await runtime.process_message("Transfer money", user_id=session_id)

        # Cancel
        response1 = await runtime.process_message("Cancel", user_id=session_id)
        # cancellation leads to 'how can i help?' or similar greeting
        assert "help" in response1.lower() or "cancel" in response1.lower()

        # Start new flow
        response2 = await runtime.process_message("What's my balance?", user_id=session_id)
        assert "account" in response2.lower() or "checking" in response2.lower()
