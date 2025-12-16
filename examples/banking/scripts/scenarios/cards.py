"""
Card flow scenarios: blocking cards and requesting new ones.
"""

from examples.banking.scripts.base import Scenario, Turn

SCENARIOS = [
    Scenario(
        name="block_card_happy",
        description="Block a lost card successfully",
        turns=[
            Turn("I lost my card"),
            Turn("debit"),  # card type
            Turn("1234"),  # last 4 digits
            Turn("yes"),  # confirm block
        ],
        expected_final=["blocked", "BLK-"],
        tags=["card", "block", "basic"],
    ),
    Scenario(
        name="block_card_stolen",
        description="Block a stolen card with urgency",
        turns=[
            Turn("My card was stolen"),
            Turn("credit"),
            Turn("5678"),
            Turn("yes"),
        ],
        expected_final=["blocked"],
        tags=["card", "block"],
    ),
    Scenario(
        name="block_card_cancelled",
        description="User cancels card blocking",
        turns=[
            Turn("Block my card"),
            Turn("debit"),
            Turn("9999"),
            Turn("no"),  # cancel
        ],
        tags=["card", "block", "cancel"],
    ),
    Scenario(
        name="request_card_debit",
        description="Request a new debit card",
        turns=[
            Turn("I want a new card"),
            Turn("debit"),  # card type
            Turn("123 Main Street, Madrid 28001"),  # address
            Turn("yes"),  # confirm
        ],
        expected_final=["CARD-", "requested"],
        tags=["card", "request", "basic"],
    ),
    Scenario(
        name="request_card_credit",
        description="Request a new credit card",
        turns=[
            Turn("I need a credit card"),
            Turn("credit"),
            Turn("456 Oak Avenue, Barcelona 08001"),
            Turn("yes"),
        ],
        expected_final=["CARD-"],
        tags=["card", "request"],
    ),
]
