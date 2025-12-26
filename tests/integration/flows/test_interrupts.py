"""M7: Confirm + Patterns Integration Tests."""

import pytest
from langgraph.checkpoint.memory import MemorySaver

from soni.config.models import (
    CollectStepConfig,
    ConfirmStepConfig,
    FlowConfig,
    SayStepConfig,
    SoniConfig,
)
from soni.runtime.loop import RuntimeLoop


@pytest.mark.asyncio
async def test_confirm_affirm_continues():
    """User affirms confirmation and flow continues."""
    # Arrange
    config = SoniConfig(
        flows={
            "main": FlowConfig(
                steps=[
                    CollectStepConfig(step="ask", slot="param", message="Value?"),
                    ConfirmStepConfig(
                        step="conf",
                        slot="param",
                        message="Confirm {param}?",
                        # on_confirm default is continue
                        on_deny="end",
                    ),
                    SayStepConfig(step="do_it", message="Done {param}"),
                    SayStepConfig(step="end", message="Ended"),
                ]
            )
        }
    )
    # Confirm needs persistent state for multi-turn checkpointer (or keep in memory)
    # Checkpointer is needed for interrupts
    checkpointer = MemorySaver()

    async with RuntimeLoop(config, checkpointer=checkpointer) as runtime:
        # Turn 1: Start
        await runtime.process_message("start", user_id="u1")

        # Turn 2: Provide value
        r2 = await runtime.process_message("100", user_id="u1")
        assert "Confirm 100?" in r2

        # Turn 3: Affirm
        r3 = await runtime.process_message("yes", user_id="u1")
        assert "Done 100" in r3


@pytest.mark.asyncio
async def test_confirm_deny_routes_to_on_deny():
    """User denies and flow routes to on_deny target."""
    # Arrange
    config = SoniConfig(
        flows={
            "main": FlowConfig(
                steps=[
                    CollectStepConfig(step="ask", slot="param", message="Value?"),
                    ConfirmStepConfig(
                        step="conf", slot="param", message="Confirm {param}?", on_deny="cancelled"
                    ),
                    SayStepConfig(step="do_it", message="Done {param}"),
                    SayStepConfig(step="cancelled", message="Operation cancelled"),
                ]
            )
        }
    )
    checkpointer = MemorySaver()

    async with RuntimeLoop(config, checkpointer=checkpointer) as runtime:
        # Turn 1: Start
        await runtime.process_message("start", user_id="u2")

        # Turn 2: Provide value
        r2 = await runtime.process_message("200", user_id="u2")
        assert "Confirm 200?" in r2

        # Turn 3: Deny
        r3 = await runtime.process_message("no", user_id="u2")
        assert "Operation cancelled" in r3
        assert "Done 200" not in r3


@pytest.mark.asyncio
async def test_confirm_correction_updates_slot():
    """User corrects value during confirmation."""
    # Arrange
    config = SoniConfig(
        flows={
            "transfer": FlowConfig(
                steps=[
                    CollectStepConfig(step="get_amount", slot="amount", message="How much?"),
                    ConfirmStepConfig(
                        step="confirm", slot="amount", message="Transfer ${amount}?", on_deny="end"
                    ),
                    SayStepConfig(step="done", message="Transferred ${amount}"),
                    SayStepConfig(step="end", message="Cancelled"),
                ]
            )
        }
    )
    checkpointer = MemorySaver()

    # Act & Assert - Turn 1: Start
    async with RuntimeLoop(config, checkpointer=checkpointer) as runtime:
        await runtime.process_message("transfer", user_id="u3")

    # Act & Assert - Turn 2: Provide amount
    async with RuntimeLoop(config, checkpointer=checkpointer) as runtime:
        response2 = await runtime.process_message("100", user_id="u3")
    assert "Transfer $100?" in response2

    # Act & Assert - Turn 3: Correction
    async with RuntimeLoop(config, checkpointer=checkpointer) as runtime:
        # This requires NLU to detect correction 'actually 50'
        # Currently standard NLU handles it? Or we need M7 parser support.
        # Assuming M7 parser support will be added (RED phase).
        response3 = await runtime.process_message("actually 50", user_id="u3")
    assert "Transfer $50?" in response3

    # Act & Assert - Turn 4: Confirm
    async with RuntimeLoop(config, checkpointer=checkpointer) as runtime:
        response4 = await runtime.process_message("yes", user_id="u3")
    assert "Transferred $50" in response4
