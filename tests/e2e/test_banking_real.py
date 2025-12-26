"""End-to-end test for Banking domain using Real NLU (DSPy).

This test verifies the system behavior with actual LLM calls.
It requires OPENAI_API_KEY to be set (handled by conftest.py).
"""

from pathlib import Path

import pytest

# Import banking handlers to register actions
import examples.banking.handlers  # noqa: F401
from soni.config import SoniConfig
from soni.config.loader import ConfigLoader
from soni.runtime.loop import RuntimeLoop


@pytest.mark.asyncio
async def test_real_nlu_transfer_flow():
    """Verify that real NLU correctly identifies transfer intent and extracts slots.

    This is a "smoke test" for the real integration.
    """
    # 1. Setup Banking Domain (Load from example YAMLs)
    config_path = Path("examples/banking/domain")
    if not config_path.exists():
        pytest.skip("Banking example domain not found")

    config = ConfigLoader.load(str(config_path))

    # Disable rephrasing for easier assertion match
    config.settings.rephrase_responses = False

    from langgraph.checkpoint.memory import MemorySaver

    checkpointer = MemorySaver()

    async with RuntimeLoop(config, checkpointer=checkpointer) as runtime:
        # 2. Start Conversation
        response = await runtime.process_message("I want to transfer money")

        # Expecting it to ask "Who" (Beneficiary)
        assert "Who" in response or "recipient" in response

        # 3. Provide Name (Beneficiary)
        response = await runtime.process_message("To Alice")

        # Now it should ask for IBAN
        assert "IBAN" in response

        # 4. Provide Slot (IBAN)
        response = await runtime.process_message("ES123456789")

        # Should ask for Amount
        assert "How much" in response or "amount" in response

        # 5. Provide Amount
        response = await runtime.process_message("100 EUR")

        # Should ask for Concept
        assert "concept" in response or "reference" in response
