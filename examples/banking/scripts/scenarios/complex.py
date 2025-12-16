"""
Complex flow scenarios: interruptions, digressions, and multi-flow sequences.
"""

from examples.banking.scripts.base import Scenario, Turn

SCENARIOS = [
    # =========================================================================
    # Flow Interruptions
    # =========================================================================
    Scenario(
        name="transfer_interrupted_by_balance",
        description="User interrupts transfer flow to check balance, then resumes",
        turns=[
            Turn("I want to transfer money"),
            Turn("John"),  # beneficiary
            Turn("How much do I have?"),  # Interruption!
            Turn("savings"),  # answer for balance flow
            # After balance flow completes, should resume transfer
            Turn("ES9121000418450200051332"),  # Continue with IBAN
            Turn("500"),
            Turn("Rent"),
            Turn("checking"),
            Turn("yes"),
        ],
        expected_final=["Transaction ID"],
        tags=["complex", "interruption", "resume"],
    ),
    Scenario(
        name="balance_then_transfer",
        description="Complete one flow then start another",
        turns=[
            Turn("What's my balance?"),
            Turn("checking"),
            # First flow complete, start new one
            Turn("Transfer 100 euros"),
            Turn("Maria"),
            Turn("ES1234567890123456789012"),
            Turn("100"),
            Turn("Gift"),
            Turn("checking"),
            Turn("yes"),
        ],
        tags=["complex", "sequential"],
    ),
    # =========================================================================
    # Nested Confirmations and Modifications
    # =========================================================================
    Scenario(
        name="transfer_multiple_modifications",
        description="User modifies multiple fields during confirmation",
        turns=[
            Turn("Send money"),
            Turn("Carlos"),
            Turn("DE89370400440532013000"),
            Turn("500"),
            Turn("Dinner payment"),
            Turn("savings"),
            Turn("No, change the beneficiary"),  # First modification
            Turn("Roberto"),
            Turn("No, change the amount"),  # Second modification
            Turn("600"),
            Turn("yes"),  # Finally confirm
        ],
        expected_final=["Transaction ID"],
        tags=["complex", "modification", "multi-change"],
    ),
    # =========================================================================
    # Branching Scenarios
    # =========================================================================
    Scenario(
        name="transfer_edge_of_limit",
        description="Transfer exactly at 10K limit (should NOT require 2FA)",
        turns=[
            Turn("Transfer funds"),
            Turn("Test User"),
            Turn("ES9121000418450200051332"),
            Turn("10000"),  # Exactly at limit
            Turn("Large payment"),
            Turn("investment"),
            Turn("yes"),
        ],
        expected_final=["Transaction ID"],
        tags=["complex", "branching", "edge-case"],
    ),
    Scenario(
        name="transfer_just_over_limit",
        description="Transfer just above 10K limit (requires 2FA)",
        turns=[
            Turn("Transfer funds"),
            Turn("Test User"),
            Turn("ES9121000418450200051332"),
            Turn("10001"),  # Just over limit
            Turn("654321"),  # Security code
            Turn("Large payment"),
            Turn("investment"),
            Turn("yes"),
        ],
        expected_final=["Transaction ID"],
        tags=["complex", "branching", "2fa"],
    ),
    # =========================================================================
    # Card + Transfer Combined
    # =========================================================================
    Scenario(
        name="block_card_then_transfer",
        description="Block card due to theft, then make secure transfer",
        turns=[
            Turn("My card was stolen"),
            Turn("credit"),
            Turn("4567"),
            Turn("yes"),  # Block confirmed
            # Now make a transfer
            Turn("I need to transfer money urgently"),
            Turn("Emergency Fund"),
            Turn("GB82WEST12345698765432"),
            Turn("1000"),
            Turn("Emergency"),
            Turn("savings"),
            Turn("yes"),
        ],
        tags=["complex", "multi-flow", "security"],
    ),
    # =========================================================================
    # Help and Digression
    # =========================================================================
    Scenario(
        name="transfer_with_help_request",
        description="User asks for help during transfer flow",
        turns=[
            Turn("Transfer money"),
            Turn("What is an IBAN?"),  # Help/digression
            Turn("ES9121000418450200051332"),  # Continue with IBAN
            Turn("Alice"),
            Turn("250"),
            Turn("Payment"),
            Turn("checking"),
            Turn("yes"),
        ],
        tags=["complex", "digression", "help"],
    ),
    # =========================================================================
    # Validation Retries
    # =========================================================================
    Scenario(
        name="transfer_iban_retry",
        description="User provides invalid IBAN, then corrects it",
        turns=[
            Turn("I want to transfer money"),
            Turn("Bob"),
            Turn("NOTANIBAN"),  # Invalid
            Turn("ES9121000418450200051332"),  # Valid
            Turn("150"),
            Turn("Lunch"),
            Turn("checking"),
            Turn("yes"),
        ],
        expected_final=["Transaction ID"],
        tags=["complex", "validation", "retry"],
    ),
    Scenario(
        name="card_digits_retry",
        description="User provides wrong format card digits, then corrects",
        turns=[
            Turn("Block my card"),
            Turn("debit"),
            Turn("12345678"),  # Too many digits
            Turn("1234"),  # Correct format
            Turn("yes"),
        ],
        expected_final=["blocked"],
        tags=["complex", "validation", "retry"],
    ),
]
