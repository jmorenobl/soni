"""Banking domain configuration and example data."""

from soni.dataset.base import ConversationContext, DomainConfig, DomainExampleData

# Example data constants
ACCOUNTS = ["checking", "savings", "current", "investment"]
CURRENCIES = ["USD", "EUR", "GBP", "dollars", "euros"]
RECIPIENTS = ["mom", "dad", "landlord", "Amazon", "Alice", "Bob", "Charlie"]
AMOUNTS = ["10", "50", "100", "500", "1000"]
CARD_DIGITS = ["1234", "5678", "9012", "3456"]

# Build DomainExampleData
_EXAMPLE_DATA = DomainExampleData(
    slot_values={
        "amount": AMOUNTS,
        "currency": CURRENCIES,
        "recipient": RECIPIENTS,
        "account_type": ACCOUNTS,
        "card_last_4": CARD_DIGITS,
    },
    trigger_intents={
        "transfer_funds": [
            "I want to transfer money",
            "Send funds",
            "Make a payment",
            "Transfer to",
        ],
        "check_balance": [
            "What is my balance?",
            "Check my account",
            "How much money do I have",
            "How much do I have?",
            "What's my balance?",
            "Show me my funds",
            "How much is in my account?",
            "What's in my account?",
        ],
    },
    confirmation_positive=["Yes", "Sure", "Confirm", "That's right", "Go ahead"],
    confirmation_negative=["No", "Cancel", "That's wrong", "Stop", "Don't do it"],
    confirmation_unclear=["Maybe", "I don't know", "Later", "What?"],
)

# Domain configuration
BANKING = DomainConfig(
    name="banking",
    description="Manage bank accounts, transfers, and cards",
    available_flows=[
        "transfer_funds",
        "check_balance",
        "activate_card",
        "block_card",
        "transaction_history",
    ],
    available_actions=[
        "execute_transfer",
        "get_balance",
        "activate_card_service",
        "block_card_service",
        "fetch_transactions",
    ],
    flow_descriptions={
        "transfer_funds": "Transfer money between accounts or to other people",
        "check_balance": "Check your account balance or how much money you have",
        "activate_card": "Activate a new debit or credit card",
        "block_card": "Block a lost or stolen card",
        "transaction_history": "View recent transactions and account activity",
    },
    slots={
        "amount": "number",
        "currency": "string",
        "recipient": "string",
        "account_type": "string",
        "card_last_4": "number",
    },
    slot_prompts={
        "amount": "How much would you like to transfer?",
        "currency": "In which currency?",
        "recipient": "Who would you like to send money to?",
        "account_type": "Which account (checking or savings)?",
        "card_last_4": "What are the last 4 digits of the card?",
    },
    example_data=_EXAMPLE_DATA,
)

# Legacy exports for backward-compatibility (deprecated - use example_data instead)
TRANSFER_UTTERANCES = _EXAMPLE_DATA.trigger_intents.get("transfer_funds", [])
BALANCE_UTTERANCES = _EXAMPLE_DATA.trigger_intents.get("check_balance", [])
CONFIRMATION_POSITIVE = _EXAMPLE_DATA.confirmation_positive
CONFIRMATION_NEGATIVE = _EXAMPLE_DATA.confirmation_negative
CONFIRMATION_UNCLEAR = _EXAMPLE_DATA.confirmation_unclear

# Intent switch utterances (unique to banking for cross-flow examples)
INTENT_SWITCH_TO_BALANCE = [
    "How much do I have?",
    "What's my balance?",
    "First, how much is in my account?",
    "Wait, what's my balance?",
    "Let me check my balance first",
]

INTENT_SWITCH_TO_TRANSFER = [
    "I want to send some to my sister",
    "Actually, transfer some to mom",
    "Let me transfer money instead",
]

# Other pattern-specific utterances
CANCELLATION_UTTERANCES = ["Cancel transfer", "Stop", "Forget it", "Abort"]
CORRECTION_UTTERANCES = [
    "No, I meant 50 dollars",
    "Change amount to 100",
    "Not to mom",
    "Actually 20 EUR",
]
MODIFICATION_UTTERANCES = ["Change the amount", "Update recipient", "Can I change the currency?"]
DIGRESSION_UTTERANCES = ["What are your fees?", "Is it safe?", "Do you have a branch nearby?"]
CLARIFICATION_UTTERANCES = ["Which account?", "mom", "checking"]
CONTINUATION_UTTERANCES = ["Also check balance", "Transfer more", "Another one"]


def create_context_after_transfer(
    amount=None, currency=None, recipient=None
) -> ConversationContext:
    """Create context after user initiates transfer."""
    import dspy

    current_slots = {}
    if amount:
        current_slots["amount"] = amount
    if currency:
        current_slots["currency"] = currency
    if recipient:
        current_slots["recipient"] = recipient

    return ConversationContext(
        history=dspy.History(
            messages=[
                {"user_message": "I want to transfer money"},
                {
                    "result": {
                        "command": "transfer_funds",
                        "slots": [{"name": k, "value": v} for k, v in current_slots.items()],
                    }
                },
            ]
        ),
        current_slots=current_slots,
        current_flow="transfer_funds",
        expected_slots=[s for s in ["amount", "currency", "recipient"] if s not in current_slots],
    )
