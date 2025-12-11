"""Test last_response update issue with real Soni system.

This test creates a real RuntimeLoop and simulates the flow:
1. User says "San Francisco" (for origin)
2. validate_slot processes it
3. collect_next_slot should set last_response to "Where would you like to go?"
4. generate_response should read and return that updated last_response
"""

import asyncio
import logging

from langgraph.checkpoint.memory import MemorySaver

from soni.core.config import SoniConfig
from soni.runtime.runtime import RuntimeLoop

# Configure logging to see all debug messages
logging.basicConfig(
    level=logging.INFO,
    format="%(levelname)s [%(name)s] %(message)s",
)

# Set specific loggers to INFO to see our debug messages
logging.getLogger("soni.dm.nodes.validate_slot").setLevel(logging.INFO)
logging.getLogger("soni.dm.nodes.collect_next_slot").setLevel(logging.INFO)
logging.getLogger("soni.dm.nodes.generate_response").setLevel(logging.INFO)
logging.getLogger("soni.dm.routing").setLevel(logging.INFO)

logger = logging.getLogger(__name__)


async def main() -> None:
    """Run the test."""
    # Create RuntimeLoop
    runtime = RuntimeLoop(config_path="examples/flight_booking/soni.yaml")

    user_id = "test-last-response-1"

    logger.info("=" * 100)
    logger.info(
        "TEST: Checking last_response update after validate_slot → collect_next_slot → generate_response"
    )
    logger.info("=" * 100)

    # Step 1: Start conversation
    logger.info("\n" + "=" * 100)
    logger.info("STEP 1: Start conversation - 'I want to book a flight'")
    logger.info("=" * 100)

    response1 = await runtime.process_message(
        user_msg="I want to book a flight",
        user_id=user_id,
    )

    logger.info(f"\nRESULT: {response1}")
    logger.info("Expected: Should ask for origin (first slot)")

    # Step 2: Provide origin
    logger.info("\n" + "=" * 100)
    logger.info("STEP 2: Provide origin - 'San Francisco'")
    logger.info("=" * 100)
    logger.info("This should:")
    logger.info("  1. validate_slot: validate 'San Francisco' as origin, clear user_message")
    logger.info(
        "  2. collect_next_slot: detect transition (origin→destination), set last_response='Where would you like to go?'"
    )
    logger.info("  3. generate_response: read last_response and return it")
    logger.info("=" * 100)

    response2 = await runtime.process_message(
        user_msg="San Francisco",
        user_id=user_id,
    )

    logger.info("\n" + "=" * 100)
    logger.info("FINAL RESULT:")
    logger.info(f"  Response: '{response2}'")
    logger.info("  Expected: 'Where would you like to go?' (or similar destination prompt)")
    logger.info("=" * 100)

    # Check if the response is correct
    response = response2
    if "destination" in response.lower() or "where" in response.lower() or "go" in response.lower():
        logger.info("✅ SUCCESS: Response correctly asks for destination")
    else:
        logger.error("❌ FAILURE: Response does not ask for destination!")
        logger.error(f"   Got: '{response}'")
        logger.error("   This suggests last_response was not updated correctly")


if __name__ == "__main__":
    asyncio.run(main())
