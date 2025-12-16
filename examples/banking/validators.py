"""
Banking validators with realistic validation logic.
"""

import re
from typing import Any

from soni.validation.registry import ValidatorRegistry

# IBAN country lengths (subset of common ones)
IBAN_LENGTHS: dict[str, int] = {
    "AL": 28,
    "AD": 24,
    "AT": 20,
    "AZ": 28,
    "BH": 22,
    "BY": 28,
    "BE": 16,
    "BA": 20,
    "BR": 29,
    "BG": 22,
    "CR": 22,
    "HR": 21,
    "CY": 28,
    "CZ": 24,
    "DK": 18,
    "DO": 28,
    "TL": 23,
    "EE": 20,
    "FO": 18,
    "FI": 18,
    "FR": 27,
    "GE": 22,
    "DE": 22,
    "GI": 23,
    "GR": 27,
    "GL": 18,
    "GT": 28,
    "HU": 28,
    "IS": 26,
    "IQ": 23,
    "IE": 22,
    "IL": 23,
    "IT": 27,
    "JO": 30,
    "KZ": 20,
    "XK": 20,
    "KW": 30,
    "LV": 21,
    "LB": 28,
    "LI": 21,
    "LT": 20,
    "LU": 20,
    "MK": 19,
    "MT": 31,
    "MR": 27,
    "MU": 30,
    "MC": 27,
    "MD": 24,
    "ME": 22,
    "NL": 18,
    "NO": 15,
    "PK": 24,
    "PS": 29,
    "PL": 28,
    "PT": 25,
    "QA": 29,
    "RO": 24,
    "SM": 27,
    "SA": 24,
    "RS": 22,
    "SC": 31,
    "SK": 24,
    "SI": 19,
    "ES": 24,
    "SE": 24,
    "CH": 21,
    "TN": 24,
    "TR": 26,
    "UA": 29,
    "AE": 23,
    "GB": 22,
    "VA": 22,
    "VG": 24,
}


def _iban_checksum_valid(iban: str) -> bool:
    """Validate IBAN using MOD-97 algorithm (ISO 7064)."""
    # Move first 4 chars to end
    rearranged = iban[4:] + iban[:4]

    # Convert letters to numbers (A=10, B=11, ..., Z=35)
    numeric = ""
    for char in rearranged:
        if char.isdigit():
            numeric += char
        else:
            numeric += str(ord(char) - ord("A") + 10)

    # Check MOD 97
    return int(numeric) % 97 == 1


@ValidatorRegistry.register("iban")
def validate_iban(value: Any) -> bool:
    """
    Validate IBAN format and checksum.

    Performs:
    1. Format validation (country code + check digits + BBAN)
    2. Length validation per country
    3. MOD-97 checksum validation
    """
    if not isinstance(value, str):
        return False

    # Normalize: remove spaces and convert to uppercase
    iban = re.sub(r"\s+", "", str(value)).upper()

    # Basic format check: 2 letters + 2 digits + alphanumeric BBAN
    if not re.match(r"^[A-Z]{2}[0-9]{2}[A-Z0-9]+$", iban):
        return False

    # Check country code and length
    country_code = iban[:2]
    if country_code not in IBAN_LENGTHS:
        return False

    expected_length = IBAN_LENGTHS[country_code]
    if len(iban) != expected_length:
        return False

    # Validate checksum
    return _iban_checksum_valid(iban)


@ValidatorRegistry.register("account_type")
def validate_account_type(value: Any) -> bool:
    """Validate account type is one of the available accounts."""
    valid_types = ["checking", "savings", "investment"]
    return str(value).lower().strip() in valid_types


@ValidatorRegistry.register("positive_amount")
def validate_amount(value: Any) -> bool:
    """Validate amount is a positive number."""
    try:
        amount = float(str(value).replace(",", ".").replace("€", "").replace("$", "").strip())
        return amount > 0
    except ValueError:
        return False


@ValidatorRegistry.register("card_digits")
def validate_card_digits(value: Any) -> bool:
    """Validate exactly 4 digits for card last digits."""
    s_val = str(value).strip()
    return len(s_val) == 4 and s_val.isdigit()


@ValidatorRegistry.register("card_type")
def validate_card_type(value: Any) -> bool:
    """Validate card type is debit or credit."""
    valid_types = ["debit", "credit"]
    return str(value).lower().strip() in valid_types


@ValidatorRegistry.register("person_name")
def validate_person_name(value: Any) -> bool:
    """Validate person name has reasonable format."""
    if not isinstance(value, str):
        return False
    name = value.strip()
    # At least 2 chars, contains letters
    return len(name) >= 2 and any(c.isalpha() for c in name)


@ValidatorRegistry.register("transaction_period")
def validate_transaction_period(value: Any) -> bool:
    """Validate transaction period is a recognized time range."""
    if not isinstance(value, str):
        return False

    normalized = value.lower().strip()

    valid_periods = [
        "last week",
        "week",
        "this week",
        "last month",
        "month",
        "this month",
        "last 3 months",
        "3 months",
        "three months",
        "last three months",
    ]
    return normalized in valid_periods


@ValidatorRegistry.register("address")
def validate_address(value: Any) -> bool:
    """Validate address has minimum required components."""
    if not isinstance(value, str):
        return False

    address = value.strip()
    # Basic check: at least 10 chars and contains numbers (for street number/postal code)
    return len(address) >= 10 and any(c.isdigit() for c in address)


@ValidatorRegistry.register("bill_type")
def validate_bill_type(value: Any) -> bool:
    """Validate bill type is a recognized utility type."""
    valid_types = ["electricity", "water", "gas", "phone", "internet", "mobile"]
    return str(value).lower().strip() in valid_types


@ValidatorRegistry.register("bill_reference")
def validate_bill_reference(value: Any) -> bool:
    """Validate bill reference number format."""
    if not isinstance(value, str):
        return False
    ref = value.strip()
    # At least 6 alphanumeric characters
    return len(ref) >= 6 and ref.replace("-", "").replace("/", "").isalnum()


@ValidatorRegistry.register("security_code")
def validate_security_code(value: Any) -> bool:
    """Validate 6-digit security/OTP code."""
    if not isinstance(value, str):
        value = str(value)
    code = value.strip()
    return len(code) == 6 and code.isdigit()


@ValidatorRegistry.register("yes_no")
def validate_yes_no(value: Any) -> bool:
    """Validate yes/no response."""
    if not isinstance(value, str):
        return False
    normalized = value.lower().strip()
    return normalized in ["yes", "no", "y", "n", "si", "sí"]
