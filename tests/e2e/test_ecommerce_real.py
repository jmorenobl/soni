import os

import pytest
from langgraph.checkpoint.memory import MemorySaver

# Import handlers
import examples.ecommerce.handlers  # noqa: F401
from soni.config.loader import ConfigLoader
from soni.runtime.loop import RuntimeLoop


@pytest.mark.e2e
@pytest.mark.asyncio
async def test_product_search_and_purchase():
    """Test complete e-commerce flow: search → add to cart → checkout."""
    if not os.getenv("OPENAI_API_KEY"):
        pytest.skip("OPENAI_API_KEY not set")

    config = ConfigLoader.load("examples/ecommerce/domain")
    config.settings.rephrase_responses = False

    checkpointer = MemorySaver()
    async with RuntimeLoop(config, checkpointer=checkpointer) as runtime:
        session_id = "ecommerce-test-001"

        # 1. Search
        response = await runtime.process_message(
            "I'm looking for running shoes", user_id=session_id
        )
        assert "shoes" in response.lower()

        # 2. Add to cart (be explicit to help SlotExtractor)
        response = await runtime.process_message("Add 2 Nike shoes to my cart", user_id=session_id)
        assert "added" in response.lower() or "cart" in response.lower()

        # 3. Checkout
        response = await runtime.process_message("Checkout", user_id=session_id)
        assert "address" in response.lower() or "shipping" in response.lower()

        # 4. Address
        response = await runtime.process_message("123 Main St", user_id=session_id)
        assert "confirmed" in response.lower() or "order" in response.lower()


@pytest.mark.e2e
@pytest.mark.asyncio
async def test_order_modification():
    """Test modifying order - simpler version."""
    if not os.getenv("OPENAI_API_KEY"):
        pytest.skip("OPENAI_API_KEY not set")

    config = ConfigLoader.load("examples/ecommerce/domain")
    config.settings.rephrase_responses = False

    checkpointer = MemorySaver()
    async with RuntimeLoop(config, checkpointer=checkpointer) as runtime:
        session_id = "ecommerce-test-002"

        # Start adding specific items
        response = await runtime.process_message("Add 2 laptops to my cart", user_id=session_id)

        # Verify it was understood - should confirm or ask for next step
        assert (
            "laptop" in response.lower()
            or "added" in response.lower()
            or "cart" in response.lower()
        )
