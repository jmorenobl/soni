import os
from unittest.mock import patch

import pytest
from langgraph.checkpoint.memory import MemorySaver

# Import banking handlers
import examples.banking.handlers  # noqa: F401
from soni.config.loader import ConfigLoader
from soni.runtime.loop import RuntimeLoop


@pytest.mark.e2e
@pytest.mark.asyncio
async def test_nlu_error_propagation():
    """Test that NLU errors propagate as NLUProviderError.

    Per design: NLU errors should NOT be silently caught.
    They should be wrapped in NLUProviderError and propagated.
    """
    if not os.getenv("OPENAI_API_KEY"):
        pytest.skip("OPENAI_API_KEY not set")

    from soni.core.errors import NLUProviderError

    config = ConfigLoader.load("examples/banking/domain")
    config.settings.rephrase_responses = False

    checkpointer = MemorySaver()
    session_id = "error-test-001"

    async with RuntimeLoop(config, checkpointer=checkpointer) as runtime:
        # NLU errors now propagate instead of being silently caught
        with patch.object(
            runtime._context.nlu_provider, "acall", side_effect=Exception("NLU down")
        ):
            with pytest.raises(NLUProviderError, match="NLU Pass 1 failed"):
                await runtime.process_message("Transfer money", user_id=session_id)

        # System remains responsive after error (new session)
        response = await runtime.process_message("Hi", user_id=session_id)
        assert response


@pytest.mark.e2e
@pytest.mark.asyncio
async def test_action_error_recovery():
    """Test recovery from action execution errors."""
    if not os.getenv("OPENAI_API_KEY"):
        pytest.skip("OPENAI_API_KEY not set")

    config = ConfigLoader.load("examples/banking/domain")
    config.settings.rephrase_responses = False

    checkpointer = MemorySaver()
    async with RuntimeLoop(config, checkpointer=checkpointer) as runtime:
        session_id = "error-test-002"

        await runtime.process_message("Check balance", user_id=session_id)

        # This will trigger an action call in 'get_balance' flow
        with patch.object(
            runtime._context.action_registry, "execute", side_effect=Exception("Database down")
        ):
            response = await runtime.process_message("In my checking account", user_id=session_id)

            # Now caught by my fix in action_node
            assert "sorry" in response.lower() or "error" in response.lower()
