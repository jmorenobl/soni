"""Built-in validators for Soni Framework"""

import re
from datetime import datetime

from soni.validation.registry import ValidatorRegistry


@ValidatorRegistry.register("city_name")
def validate_city_name(value: str) -> bool:
    """
    Validate city name format.

    Args:
        value: City name to validate

    Returns:
        True if valid city name format, False otherwise
    """
    if not isinstance(value, str):
        return False
    # Only letters, spaces, hyphens
    return bool(re.match(r"^[a-zA-Z\s\-]+$", value)) and len(value) > 1


@ValidatorRegistry.register("future_date_only")
def validate_future_date(value: str) -> bool:
    """
    Validate date is in the future.

    Args:
        value: Date string to validate (ISO format)

    Returns:
        True if date is in the future, False otherwise
    """
    try:
        # Parse date (format depends on normalization)
        if isinstance(value, str):
            date = datetime.fromisoformat(value)
        elif isinstance(value, datetime):
            date = value
        else:
            return False
        return date > datetime.now()
    except (ValueError, AttributeError, TypeError):
        return False


@ValidatorRegistry.register("iata_code")
def validate_iata_code(value: str) -> bool:
    """
    Validate IATA airport code.

    Args:
        value: Airport code to validate

    Returns:
        True if valid IATA code, False otherwise
    """
    if not isinstance(value, str):
        return False
    # 3 uppercase letters
    return bool(re.match(r"^[A-Z]{3}$", value))


@ValidatorRegistry.register("booking_reference")
def validate_booking_ref(value: str) -> bool:
    """
    Validate booking reference format.

    Args:
        value: Booking reference to validate

    Returns:
        True if valid booking reference, False otherwise
    """
    if not isinstance(value, str):
        return False
    # 6 uppercase alphanumeric
    return bool(re.match(r"^[A-Z0-9]{6}$", value))
