"""Banking domain configuration and example data."""

from soni.dataset.base import ConversationContext, DomainConfig

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
)

# Example data
ACCOUNTS = [
    "checking",
    "savings",
    "current",
    "investment",
]

CURRENCIES = [
    "USD",
    "EUR",
    "GBP",
    "dollars",
    "euros",
]

RECIPIENTS = [
    "mom",
    "dad",
    "landlord",
    "Amazon",
    "Alice",
    "Bob",
    "Charlie",
]

AMOUNTS = [10, 50, 100, 500, 1000]

CARD_DIGITS = [1234, 5678, 9012, 3456]

TRANSFER_UTTERANCES = [
    "I want to transfer money",
    "Send funds",
    "Make a payment",
    "Transfer to",
]

BALANCE_UTTERANCES = [
    "What is my balance?",
    "Check my account",
    "How much money do I have",
    "How much do I have?",
    "What's my balance?",
    "Show me my funds",
    "How much is in my account?",
    "What's in my account?",
]

# Intent switch utterances - when user switches from one flow to another
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

# Pattern Helpers
CONFIRMATION_POSITIVE = ["Yes", "Sure", "Confirm", "That's right", "Go ahead"]
CONFIRMATION_NEGATIVE = ["No", "Cancel", "That's wrong", "Stop", "Don't do it"]
CONFIRMATION_UNCLEAR = ["Maybe", "I don't know", "Later", "What?"]

CANCELLATION_UTTERANCES = ["Cancel transfer", "Stop", "Forget it", "Abort"]

CORRECTION_UTTERANCES = [
    "No, I meant 50 dollars",
    "Change amount to 100",
    "Not to mom",
    "Actually 20 EUR",
]

MODIFICATION_UTTERANCES = [
    "Change the amount",
    "Update recipient",
    "Can I change the currency?",
]

DIGRESSION_UTTERANCES = [
    "What are your fees?",
    "Is it safe?",
    "Do you have a branch nearby?",
]

CLARIFICATION_UTTERANCES = [
    "Which account?",
    "mom",
    "checking",
]

CONTINUATION_UTTERANCES = [
    "Also check balance",
    "Transfer more",
    "Another one",
]


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
