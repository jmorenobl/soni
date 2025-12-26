"""Regression test for digression state loss."""

import pytest
from langgraph.checkpoint.memory import MemorySaver

from soni.config.models import (
    CollectStepConfig,
    FlowConfig,
    SayStepConfig,
    SoniConfig,
)
from soni.runtime.loop import RuntimeLoop


@pytest.mark.asyncio
async def test_digression_preserves_parent_progress(use_mock_nlu):
    """Verify that digression returns to correct step in parent flow."""
    # Arrange
    config = SoniConfig(
        flows={
            "transfer": FlowConfig(
                steps=[
                    CollectStepConfig(step="get_iban", slot="iban", message="IBAN?"),
                    CollectStepConfig(step="get_amount", slot="amount", message="Amount?"),
                    SayStepConfig(step="done", message="Done"),
                ]
            ),
            "check_balance": FlowConfig(
                steps=[
                    SayStepConfig(step="balance", message="Your balance is 100"),
                ]
            ),
        }
    )
    checkpointer = MemorySaver()

    # Act 1: Start transfer
    async with RuntimeLoop(config, checkpointer=checkpointer) as runtime:
        r1 = await runtime.process_message("start transfer", user_id="reg_test")
    assert "IBAN?" in r1

    # Act 2: Provide IBAN
    async with RuntimeLoop(config, checkpointer=checkpointer) as runtime:
        r2 = await runtime.process_message("ES123", user_id="reg_test")
    assert "Amount?" in r2

    # Act 3: Digression (check balance)
    async with RuntimeLoop(config, checkpointer=checkpointer) as runtime:
        r3 = await runtime.process_message("check balance", user_id="reg_test")

    # Expected: Balance info AND return to parent question (Amount?)
    assert "Your balance is 100" in r3

    # CRITICAL: Should NOT repeat "IBAN?" (step 1), should ask "Amount?" (step 2)
    assert "IBAN?" not in r3
    assert "Amount?" in r3
