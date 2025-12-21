"""E2E Integration Tests."""

import pytest
from langgraph.checkpoint.memory import MemorySaver
from soni.actions.registry import ActionRegistry
from soni.runtime.loop import RuntimeLoop

from soni.config import FlowConfig, SoniConfig
from soni.config.steps import ActionStepConfig, CollectStepConfig, SayStepConfig


@pytest.mark.asyncio
class TestE2E:
    async def test_book_flight_flow(self):
        """
        GIVEN a flight booking flow with an action to check price
        WHEN user interacts to book flight
        THEN system collects slots, runs action, and confirms
        """
        # 1. Define Actions
        registry = ActionRegistry()

        @registry.register("check_price")
        async def check_price(destination: str):
            prices = {"Paris": 200, "London": 150}
            price = prices.get(destination, 500)
            return {"price": price, "currency": "EUR"}

        # 2. Define Config
        config = SoniConfig(
            flows={
                "book_flight": FlowConfig(
                    description="Book a flight",
                    steps=[
                        CollectStepConfig(step="ask_dest", slot="destination", message="Where to?"),
                        ActionStepConfig(step="get_price", call="check_price"),
                        SayStepConfig(step="show_price", message="Price is {price} {currency}"),
                    ],
                )
            }
        )

        # 3. Initialize Runtime
        from unittest.mock import AsyncMock, Mock

        from soni.core.commands import SetSlot, StartFlow
        from soni.du.models import NLUOutput

        mock_du = Mock()
        mock_du.acall = AsyncMock(
            side_effect=[
                NLUOutput(commands=[StartFlow(flow_name="book_flight")]),  # Turn 1
                NLUOutput(commands=[SetSlot(slot="destination", value="Paris")]),  # Turn 2
            ]
        )

        # Use MemorySaver for state persistence across turns
        checkpointer = MemorySaver()
        runtime = RuntimeLoop(config, checkpointer=checkpointer, registry=registry, du=mock_du)
        await runtime.initialize()

        # Run Turn 1
        response1 = await runtime.process_message("I want to book a flight", user_id="e2e_user")
        # System should ask "Where to?" (ask_dest)
        # Note: 'collect' step asks question.
        # Response should be the question.
        assert "Where to?" in response1

        # Run Turn 2
        response2 = await runtime.process_message("Paris", user_id="e2e_user")
        # System should run check_price (Paris) -> {price: 200...}
        # Then say "Price is 200 EUR"
        # show_price message template formatting logic:
        # We haven't implemented template formatting in SayNode!
        # Wait, SayNode implementation uses static message.
        # We need to implement templating in SayNode for this to work.
        # Or assertion just checks if it finished.

        # Let's assume for now SayNode outputs static str.
        # "Price is {price} {currency}"
        # If templating not implemented, it returns literal.
        # "Price is {price} {currency}"
        # Templating is implemented in SayNode, so it should return formatted string.
        assert "200" in response2
        assert "EUR" in response2
        assert "Price is 200 EUR" in response2
