import random
import uuid
from typing import Any

from soni.actions.registry import ActionRegistry

# Mock Database
ACCOUNTS = {
    "checking": {"balance": 5420.50, "currency": "USD"},
    "savings": {"balance": 12000.00, "currency": "USD"},
    "investment": {"balance": 45000.00, "currency": "USD"},
}


@ActionRegistry.register("get_balance")
def get_balance(account_type: str) -> dict[str, Any]:
    """Fetch balance for the account."""
    if account_type not in ACCOUNTS:
        return {"balance": 0.0, "currency": "USD"}  # Should happen after validation ideally

    return {
        "balance": ACCOUNTS[account_type]["balance"],
        "currency": ACCOUNTS[account_type]["currency"],
    }


@ActionRegistry.register("format_balance_message")
def format_balance_message(balance: float, currency: str, account_type: str) -> dict[str, Any]:
    """Format the output message."""
    return {"message": f"Your {account_type} balance is {currency} {balance:.2f}."}


@ActionRegistry.register("execute_transfer")
def execute_transfer(
    source_account: str, recipient: str, amount: float, currency: str
) -> dict[str, Any]:
    """Execute the transfer."""
    # Logic to deduct balance would go here
    tx_id = f"TX-{uuid.uuid4().hex[:8].upper()}"
    print(f"DEBUG: Transferring {amount} {currency} from {source_account} to {recipient}")
    return {"transaction_id": tx_id, "status": "success"}


@ActionRegistry.register("block_card_service")
def block_card_service(card_type: str, card_last_4: int) -> dict[str, Any]:
    """Block the card."""
    ref = f"BLK-{random.randint(1000, 9999)}"
    print(f"DEBUG: Blocking {card_type} card ending in {card_last_4}")
    return {"block_reference": ref}


@ActionRegistry.register("say_hello")
def say_hello() -> dict[str, Any]:
    """Say hello to the user."""
    return {
        "message": "Hello! I am your AI banking assistant. I can help you check your balance, transfer funds, or block a card. How can I help you today?"
    }
