"""
Bill payment scenarios.
"""

from examples.banking.scripts.base import Scenario, Turn

SCENARIOS = [
    Scenario(
        name="pay_bill_electricity",
        description="Pay an electricity bill",
        turns=[
            Turn("I want to pay a bill"),
            Turn("electricity"),  # bill type
            Turn("INV-2024-12345"),  # reference
            Turn("yes"),  # confirm
        ],
        expected_final=["PAY-", "paid"],
        tags=["bill", "basic"],
    ),
    Scenario(
        name="pay_bill_phone",
        description="Pay a phone bill",
        turns=[
            Turn("Pay my phone bill"),
            Turn("phone"),
            Turn("TEL-98765"),
            Turn("yes"),
        ],
        expected_final=["PAY-"],
        tags=["bill"],
    ),
    Scenario(
        name="pay_bill_cancelled",
        description="User cancels bill payment after seeing amount",
        turns=[
            Turn("I want to pay a bill"),
            Turn("water"),
            Turn("WATER-2024-001"),
            Turn("no"),  # cancel after seeing amount
        ],
        tags=["bill", "cancel"],
    ),
]
