from typing import Any

from soni.validation.registry import ValidatorRegistry


@ValidatorRegistry.register("account_type")
def validate_account_type(value: Any) -> bool:
    """Validate account type is checking or savings."""
    valid_types = ["checking", "savings", "investment"]
    return str(value).lower() in valid_types


@ValidatorRegistry.register("currency_code")
def validate_currency(value: Any) -> bool:
    """Validate currency code."""
    valid_currencies = ["USD", "EUR", "GBP", "JPY"]
    return str(value).upper() in valid_currencies


@ValidatorRegistry.register("positive_amount")
def validate_amount(value: Any) -> bool:
    """Validate amount is positive."""
    try:
        amount = float(value)
        return amount > 0
    except ValueError:
        return False


@ValidatorRegistry.register("card_digits")
def validate_card_digits(value: Any) -> bool:
    """Validate 4 digits."""
    s_val = str(value)
    return len(s_val) == 4 and s_val.isdigit()


@ValidatorRegistry.register("card_type")
def validate_card_type(value: Any) -> bool:
    """Validate card type."""
    valid_types = ["debit", "credit"]
    return str(value).lower() in valid_types


@ValidatorRegistry.register("person_name")
def validate_person_name(value: Any) -> bool:
    """Simple name validation."""
    return isinstance(value, str) and len(value) > 1
