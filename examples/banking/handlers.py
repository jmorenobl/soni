"""
Banking action handlers with realistic simulations.

These handlers simulate backend integrations for demo purposes.
In production, they would connect to actual banking APIs.
"""

import random
import uuid
from datetime import datetime, timedelta
from typing import Any

from soni.actions.registry import ActionRegistry

# =============================================================================
# Mock Database
# =============================================================================

ACCOUNTS: dict[str, dict[str, Any]] = {
    "checking": {"balance": 3_847.52, "currency": "EUR", "iban": "ES9121000418450200051332"},
    "savings": {"balance": 15_230.00, "currency": "EUR", "iban": "ES7620770024003102575766"},
    "investment": {"balance": 42_150.75, "currency": "EUR", "iban": "ES1000492352082414205416"},
}

# Bank names by country code (for IBAN lookup simulation)
BANK_DIRECTORY: dict[str, list[str]] = {
    "ES": ["Santander", "BBVA", "CaixaBank", "Sabadell", "Bankinter"],
    "DE": ["Deutsche Bank", "Commerzbank", "DZ Bank", "KfW"],
    "FR": ["BNP Paribas", "Crédit Agricole", "Société Générale"],
    "GB": ["HSBC", "Barclays", "Lloyds", "NatWest"],
    "IT": ["UniCredit", "Intesa Sanpaolo", "Banco BPM"],
    "NL": ["ING", "ABN AMRO", "Rabobank"],
    "PT": ["Millennium BCP", "Novo Banco", "Santander Totta"],
}

# Simulated transaction data
MOCK_TRANSACTIONS: list[dict[str, Any]] = [
    {
        "date": "2024-12-15",
        "description": "Spotify Premium",
        "amount": -9.99,
        "category": "subscriptions",
    },
    {
        "date": "2024-12-14",
        "description": "Salary - TechCorp",
        "amount": 3200.00,
        "category": "income",
    },
    {"date": "2024-12-13", "description": "Amazon.es", "amount": -47.89, "category": "shopping"},
    {"date": "2024-12-12", "description": "Carrefour", "amount": -82.34, "category": "groceries"},
    {"date": "2024-12-11", "description": "Netflix", "amount": -12.99, "category": "subscriptions"},
    {
        "date": "2024-12-10",
        "description": "Transfer from Maria",
        "amount": 150.00,
        "category": "transfer",
    },
    {
        "date": "2024-12-09",
        "description": "Electricity - Iberdrola",
        "amount": -67.50,
        "category": "utilities",
    },
    {
        "date": "2024-12-08",
        "description": "Restaurant La Tasca",
        "amount": -35.00,
        "category": "dining",
    },
    {"date": "2024-12-05", "description": "Gym membership", "amount": -29.90, "category": "health"},
    {"date": "2024-12-01", "description": "Rent payment", "amount": -850.00, "category": "housing"},
]

# Bill issuers
BILL_ISSUERS: dict[str, list[str]] = {
    "electricity": ["Iberdrola", "Endesa", "Naturgy", "EDP"],
    "water": ["Canal de Isabel II", "Aguas de Barcelona", "EMASESA"],
    "gas": ["Naturgy", "Endesa Gas", "Repsol Gas"],
    "phone": ["Movistar", "Vodafone", "Orange", "MasMovil"],
    "internet": ["Movistar Fibra", "Vodafone Fibra", "Orange Fibra"],
    "mobile": ["Movistar", "Vodafone", "Orange", "Yoigo"],
}


# =============================================================================
# Greeting Handler
# =============================================================================


@ActionRegistry.register("get_greeting")
def get_greeting() -> dict[str, Any]:
    """Generate a contextual greeting based on time of day."""
    hour = datetime.now().hour

    if hour < 12:
        greeting = "Good morning"
    elif hour < 18:
        greeting = "Good afternoon"
    else:
        greeting = "Good evening"

    return {
        "message": (
            f"{greeting}! I'm your banking assistant. "
            "I can help you check balances, make transfers, view transactions, "
            "manage your cards, or pay bills. What would you like to do?"
        )
    }


# =============================================================================
# Balance Handlers
# =============================================================================


@ActionRegistry.register("get_balance")
def get_balance(account_type: str) -> dict[str, Any]:
    """Fetch balance for the specified account."""
    account_key = account_type.lower().strip()

    if account_key not in ACCOUNTS:
        return {"balance": 0.0, "currency": "EUR"}

    account = ACCOUNTS[account_key]
    return {
        "balance": account["balance"],
        "currency": account["currency"],
    }


@ActionRegistry.register("format_balance_message")
def format_balance_message(balance: float, currency: str, account_type: str) -> dict[str, Any]:
    """Format the balance into a human-readable message."""
    formatted_balance = f"{balance:,.2f}".replace(",", " ")
    return {"message": f"Your {account_type} account balance is {formatted_balance} {currency}."}


# =============================================================================
# Transfer Handlers
# =============================================================================


@ActionRegistry.register("lookup_iban")
def lookup_iban(iban: str) -> dict[str, Any]:
    """
    Look up bank information from IBAN.

    In production, this would query a real BIC/SWIFT directory.
    """
    # Clean IBAN
    clean_iban = iban.replace(" ", "").upper()
    country_code = clean_iban[:2]

    # Get bank name based on country
    if country_code in BANK_DIRECTORY:
        bank_name = random.choice(BANK_DIRECTORY[country_code])
    else:
        bank_name = f"International Bank ({country_code})"

    return {
        "bank_name": bank_name,
        "is_valid": True,  # Already validated by validator
    }


# High-value transfer limit (EUR)
TRANSFER_LIMIT = 10_000.0


@ActionRegistry.register("check_transfer_limits")
def check_transfer_limits(amount: float) -> dict[str, Any]:
    """
    Check if transfer amount requires extra authorization.

    Transfers > 10,000 EUR require 2FA verification.
    """
    try:
        amount_float = float(amount)
    except (ValueError, TypeError):
        amount_float = 0.0

    requires_auth = amount_float > TRANSFER_LIMIT

    if requires_auth:
        limit_message = (
            f"This transfer of {amount_float:,.2f} EUR exceeds the {TRANSFER_LIMIT:,.0f} EUR limit "
            "and requires additional security verification."
        )
    else:
        limit_message = ""

    return {
        "requires_auth": "yes" if requires_auth else "no",
        "limit_message": limit_message,
    }


@ActionRegistry.register("verify_security_code")
def verify_security_code(security_code: str) -> dict[str, Any]:
    """
    Verify the 2FA security code.

    In production, this would validate against the OTP service.
    For demo, accepts any 6-digit code.
    """
    # Simple validation: 6 digits
    is_valid = len(str(security_code).strip()) == 6 and str(security_code).strip().isdigit()

    return {
        "is_verified": "yes" if is_valid else "no",
    }


@ActionRegistry.register("execute_transfer")
def execute_transfer(
    source_account: str,
    beneficiary_name: str,
    iban: str,
    amount: float | str,
    transfer_concept: str,
) -> dict[str, Any]:
    """
    Execute a bank transfer.

    In production, this would:
    1. Check sufficient funds
    2. Create pending transaction
    3. Submit to payment processor
    4. Return confirmation
    """
    # Convert amount to float (slots come as strings)
    try:
        amount_float = float(amount)
    except (ValueError, TypeError):
        return {
            "transaction_id": "FAILED",
            "status": "invalid_amount",
        }

    # Simulate balance check
    account = ACCOUNTS.get(source_account.lower(), {})
    current_balance = account.get("balance", 0)

    if amount_float > current_balance:
        return {
            "transaction_id": "FAILED",
            "status": "insufficient_funds",
        }

    # Generate transaction ID
    tx_id = f"TRF-{datetime.now().strftime('%Y%m%d')}-{uuid.uuid4().hex[:8].upper()}"

    # In a real system, deduct from balance
    # ACCOUNTS[source_account.lower()]["balance"] -= amount

    return {
        "transaction_id": tx_id,
        "status": "completed",
    }


# =============================================================================
# Transaction History Handler
# =============================================================================


@ActionRegistry.register("get_transactions")
def get_transactions(account_type: str, transaction_period: str) -> dict[str, Any]:
    """
    Fetch recent transactions for an account (legacy, non-paginated).

    In production, this would query the transaction database.
    """
    # Determine number of transactions based on period
    period_lower = transaction_period.lower()
    if "week" in period_lower:
        num_transactions = 5
    elif "3" in period_lower or "three" in period_lower:
        num_transactions = 10
    else:  # month
        num_transactions = 7

    transactions = MOCK_TRANSACTIONS[:num_transactions]

    # Build summary
    lines = []
    for tx in transactions:
        sign = "+" if tx["amount"] > 0 else ""
        lines.append(f"  {tx['date']}: {tx['description']} ({sign}{tx['amount']:.2f} EUR)")

    transactions_summary = "\n".join(lines)

    # Calculate totals
    total_income = sum(tx["amount"] for tx in transactions if tx["amount"] > 0)
    total_expenses = sum(tx["amount"] for tx in transactions if tx["amount"] < 0)

    return {
        "transactions_summary": transactions_summary,
        "total_income": f"{total_income:.2f}",
        "total_expenses": f"{total_expenses:.2f}",
    }


# Pagination settings
TRANSACTIONS_PER_PAGE = 3


@ActionRegistry.register("init_transaction_page")
def init_transaction_page() -> dict[str, Any]:
    """Initialize transaction pagination state."""
    return {
        "page": 1,
        "continue": "yes",  # Start the loop
    }


@ActionRegistry.register("get_transactions_paginated")
def get_transactions_paginated(
    account_type: str, transaction_period: str, transaction_page: int = 1
) -> dict[str, Any]:
    """
    Fetch transactions with pagination support.

    Returns a page of transactions and indicates if more are available.
    """
    try:
        page = int(transaction_page)
    except (ValueError, TypeError):
        page = 1

    # Calculate offset
    start_idx = (page - 1) * TRANSACTIONS_PER_PAGE
    end_idx = start_idx + TRANSACTIONS_PER_PAGE

    # Get transactions for this page
    transactions = MOCK_TRANSACTIONS[start_idx:end_idx]
    has_more = end_idx < len(MOCK_TRANSACTIONS)

    if not transactions:
        return {
            "transactions_summary": "No more transactions to show.",
            "total_income": "0.00",
            "total_expenses": "0.00",
            "has_more": "no",
        }

    # Build summary
    lines = [f"Page {page}:"]
    for tx in transactions:
        sign = "+" if tx["amount"] > 0 else ""
        lines.append(f"  {tx['date']}: {tx['description']} ({sign}{tx['amount']:.2f} EUR)")

    transactions_summary = "\n".join(lines)

    # Calculate totals for this page
    total_income = sum(tx["amount"] for tx in transactions if tx["amount"] > 0)
    total_expenses = sum(tx["amount"] for tx in transactions if tx["amount"] < 0)

    return {
        "transactions_summary": transactions_summary,
        "total_income": f"{total_income:.2f}",
        "total_expenses": f"{total_expenses:.2f}",
        "has_more": "yes" if has_more else "no",
    }


@ActionRegistry.register("increment_page")
def increment_page(transaction_page: int = 1) -> dict[str, Any]:
    """Increment the transaction page number."""
    try:
        page = int(transaction_page)
    except (ValueError, TypeError):
        page = 1

    return {"page": page + 1}


# =============================================================================
# Card Handlers
# =============================================================================


@ActionRegistry.register("block_card")
def block_card(card_type: str, card_last_4: str) -> dict[str, Any]:
    """
    Block a card immediately.

    In production, this would:
    1. Verify card ownership
    2. Submit block request to card processor
    3. Send SMS confirmation
    """
    block_ref = f"BLK-{datetime.now().strftime('%Y%m%d')}-{random.randint(1000, 9999)}"

    return {
        "block_reference": block_ref,
        "replacement_info": (
            "Would you like me to order a replacement card? "
            "It typically takes 5-7 business days to arrive."
        ),
    }


@ActionRegistry.register("request_new_card")
def request_new_card(card_type: str, delivery_address: str) -> dict[str, Any]:
    """
    Request a new card.

    In production, this would:
    1. Verify eligibility
    2. Create card order
    3. Schedule delivery
    """
    request_id = f"CARD-{uuid.uuid4().hex[:8].upper()}"

    # Calculate estimated arrival (5-7 business days)
    arrival_date = datetime.now() + timedelta(days=random.randint(5, 7))
    estimated_arrival = arrival_date.strftime("%B %d, %Y")

    return {
        "request_id": request_id,
        "estimated_arrival": estimated_arrival,
    }


# =============================================================================
# Bill Payment Handlers
# =============================================================================


@ActionRegistry.register("lookup_bill")
def lookup_bill(bill_type: str, bill_reference: str) -> dict[str, Any]:
    """
    Look up bill details by reference.

    In production, this would query the biller's system.
    """
    bill_type_lower = bill_type.lower()

    # Get random issuer for this bill type
    if bill_type_lower in BILL_ISSUERS:
        issuer = random.choice(BILL_ISSUERS[bill_type_lower])
    else:
        issuer = f"{bill_type.title()} Provider"

    # Generate realistic amount based on bill type
    amount_ranges: dict[str, tuple[float, float]] = {
        "electricity": (45.0, 120.0),
        "water": (20.0, 50.0),
        "gas": (30.0, 80.0),
        "phone": (25.0, 60.0),
        "internet": (35.0, 55.0),
        "mobile": (15.0, 45.0),
    }

    min_amt, max_amt = amount_ranges.get(bill_type_lower, (30.0, 100.0))
    amount = round(random.uniform(min_amt, max_amt), 2)

    # Due date is within next 2 weeks
    due_date = datetime.now() + timedelta(days=random.randint(3, 14))

    return {
        "bill_amount": f"{amount:.2f}",
        "bill_issuer": issuer,
        "bill_due_date": due_date.strftime("%B %d, %Y"),
    }


@ActionRegistry.register("pay_bill")
def pay_bill(bill_type: str, bill_reference: str, bill_amount: str) -> dict[str, Any]:
    """
    Execute bill payment.

    In production, this would:
    1. Verify sufficient funds
    2. Submit payment to biller
    3. Update account balance
    """
    payment_id = f"PAY-{datetime.now().strftime('%Y%m%d')}-{uuid.uuid4().hex[:6].upper()}"

    return {
        "payment_id": payment_id,
        "payment_status": "completed",
    }
