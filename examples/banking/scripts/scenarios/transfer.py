"""
Transfer flow scenarios: basic transfers, high-value with 2FA, modifications.
"""

from examples.banking.scripts.base import Scenario, Turn

SCENARIOS = [
    Scenario(
        name="transfer_basic",
        description="Transfer < 10K (no extra auth required)",
        turns=[
            Turn("I want to transfer money"),
            Turn("John Doe"),  # beneficiary
            Turn("ES9121000418450200051332"),  # IBAN
            Turn("500"),  # amount
            Turn("Rent payment"),  # concept
            Turn("checking"),  # source account
            Turn("yes"),  # confirm
        ],
        expected_final=["Transaction ID", "TRF-"],
        tags=["transfer", "basic"],
    ),
    Scenario(
        name="transfer_high_value",
        description="Transfer > 10K (requires 2FA security code branch)",
        turns=[
            Turn("Transfer funds"),
            Turn("Maria Garcia"),  # beneficiary
            Turn("DE89370400440532013000"),  # German IBAN
            Turn("15000"),  # amount > 10K triggers branch
            Turn("123456"),  # security code
            Turn("Investment fund"),  # concept
            Turn("savings"),  # source
            Turn("yes"),  # confirm
        ],
        expected_final=["Transaction ID"],
        tags=["transfer", "branching", "2fa"],
    ),
    Scenario(
        name="transfer_denied",
        description="Transfer flow where user denies confirmation",
        turns=[
            Turn("Send money"),
            Turn("Carlos"),
            Turn("FR7630006000011234567890189"),
            Turn("200"),
            Turn("Dinner"),
            Turn("checking"),
            Turn("no"),  # deny
        ],
        tags=["transfer", "confirmation", "deny"],
    ),
    Scenario(
        name="transfer_with_modification",
        description="Confirm flow with slot modification request",
        turns=[
            Turn("Send money"),
            Turn("Carlos"),
            Turn("FR7630006000011234567890189"),
            Turn("200"),
            Turn("Dinner"),
            Turn("checking"),
            Turn("No, change the amount"),  # deny + request change
            Turn("250"),  # new amount
            Turn("yes"),  # confirm
        ],
        expected_final=["Transaction ID"],
        tags=["transfer", "confirmation", "modify"],
    ),
    Scenario(
        name="transfer_invalid_iban",
        description="Transfer with invalid IBAN (validation failure)",
        turns=[
            Turn("I want to transfer money"),
            Turn("Test User"),
            Turn("INVALID123"),  # Invalid IBAN
            Turn("ES9121000418450200051332"),  # Valid IBAN after retry
            Turn("100"),
            Turn("Test"),
            Turn("checking"),
            Turn("yes"),
        ],
        tags=["transfer", "validation", "retry"],
    ),
]
