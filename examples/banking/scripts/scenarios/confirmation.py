"""
Test scenario for confirmation flow bug: slot modification during confirmation.

Reproduces the exact issue from user report where saying "let's make 200 €"
during confirmation shows template placeholders instead of formatting values.
"""

from examples.banking.scripts.base import Scenario, Turn

SCENARIOS = [
    Scenario(
        name="transfer_modify_amount_during_confirmation",
        description="User modifies amount directly during confirmation (Bug Report)",
        turns=[
            Turn("I want to transfer money"),
            Turn("my mom"),  # Beneficiary name
            Turn("23455235"),  # IBAN (invalid but accepted for test)
            Turn("100 e"),  # Initial amount
            Turn("christmas gift"),  # concept
            Turn("savings"),  # source account
            # At this point, confirmation prompt should show:
            # "To: my mom, IBAN: 23455235, Amount: 100 EUR, ..."
            Turn(
                "let's make 200 €",  # BUG: Should modify amount, not ask for yes/no
                expected_patterns=[
                    "200",  # Should show updated amount
                    # Should NOT show: "I need a clear yes or no answer"
                ],
            ),
            Turn("yes"),  # Confirm with new amount
        ],
        expected_final=["Transaction ID", "TRF-"],
        tags=["transfer", "confirmation", "bug", "modification"],
    ),
    Scenario(
        name="transfer_modify_beneficiary_during_confirmation",
        description="User modifies beneficiary name during confirmation",
        turns=[
            Turn("Send money"),
            Turn("John"),  # Initial beneficiary
            Turn("ES9121000418450200051332"),  # IBAN
            Turn("50"),  # amount
            Turn("gift"),  # concept
            Turn("checking"),  # source
            Turn(
                "No, the name should be Maria",
                expected_patterns=["Maria"],
            ),
            Turn("yes"),
        ],
        expected_final=["Transaction ID"],
        tags=["transfer", "confirmation", "modification"],
    ),
    Scenario(
        name="transfer_unclear_confirmation_retry",
        description="User provides unclear confirmation → retry with formatted template",
        turns=[
            Turn("Transfer money"),
            Turn("Carlos"),
            Turn("FR7630006000011234567890189"),
            Turn("100"),
            Turn("Dinner"),
            Turn("savings"),
            Turn(
                "maybe later",  # Unclear confirmation
                expected_patterns=[
                    "yes or no",  # Should ask for clarification
                    "Carlos",  # Should show actual beneficiary name (NOT {beneficiary_name})
                    "100",  # Should show actual amount (NOT {amount})
                ],
            ),
            Turn("no"),
        ],
        tags=["transfer", "confirmation", "retry", "template-bug"],
    ),
]
