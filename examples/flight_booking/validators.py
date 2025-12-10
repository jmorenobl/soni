"""Domain-specific validators for flight booking example.

This module contains validators specific to the flight booking domain.
These are NOT part of the Soni framework - they are application-level validators.
"""

import re


def validate_booking_ref(value: str) -> bool:
    """
    Validate booking reference format for flight bookings.

    This is a domain-specific validator for the flight booking example.
    Different domains will have different reference formats.

    Args:
        value: Booking reference to validate

    Returns:
        True if valid booking reference (6 uppercase alphanumeric characters), False otherwise

    Examples:
        >>> validate_booking_ref("ABC123")
        True
        >>> validate_booking_ref("XYZ789")
        True
        >>> validate_booking_ref("abc123")  # lowercase not allowed
        False
        >>> validate_booking_ref("AB12")  # too short
        False
    """
    if not isinstance(value, str):
        return False
    # Booking reference: 6 uppercase alphanumeric characters
    return bool(re.match(r"^[A-Z0-9]{6}$", value))


def validate_passenger_count(value: int) -> bool:
    """
    Validate passenger count for flight booking.

    Domain-specific rule: Most commercial flights support 1-9 passengers per booking.

    Args:
        value: Number of passengers

    Returns:
        True if valid passenger count (1-9), False otherwise
    """
    if not isinstance(value, int):
        return False
    return 1 <= value <= 9
