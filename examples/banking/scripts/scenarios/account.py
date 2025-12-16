"""
Account flow scenarios: balance checking and transactions.
"""

from examples.banking.scripts.base import Scenario, Turn

SCENARIOS = [
    Scenario(
        name="check_balance_happy",
        description="Simple balance check flow",
        turns=[
            Turn("What's my balance?"),
            Turn("checking"),
        ],
        expected_final=["balance", "EUR"],
        tags=["account", "basic"],
    ),
    Scenario(
        name="check_balance_savings",
        description="Check savings account balance",
        turns=[
            Turn("How much do I have?"),
            Turn("savings"),
        ],
        expected_final=["balance"],
        tags=["account", "basic"],
    ),
    Scenario(
        name="transactions_basic",
        description="View transactions without pagination",
        turns=[
            Turn("Show my transactions"),
            Turn("checking"),
            Turn("last week"),
        ],
        expected_final=["transactions"],
        tags=["account", "transactions"],
    ),
    Scenario(
        name="transactions_with_pagination",
        description="Transaction list with while loop pagination",
        turns=[
            Turn("Show my transactions"),
            Turn("checking"),
            Turn("last month"),
            Turn("yes"),  # View more
            Turn("no"),  # Stop
        ],
        expected_final=["transactions"],
        tags=["account", "transactions", "loop"],
    ),
]
