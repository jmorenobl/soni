"""Tests for flight booking domain-specific validators."""

from validators import validate_booking_ref, validate_passenger_count


def test_validate_booking_ref_valid():
    """Test booking ref validation with valid references."""
    assert validate_booking_ref("ABC123") is True
    assert validate_booking_ref("XYZ789") is True
    assert validate_booking_ref("000000") is True


def test_validate_booking_ref_invalid_length():
    """Test booking ref validation rejects wrong length."""
    assert validate_booking_ref("ABC") is False  # Too short
    assert validate_booking_ref("ABCD1234") is False  # Too long


def test_validate_booking_ref_invalid_characters():
    """Test booking ref validation rejects invalid characters."""
    assert validate_booking_ref("abc123") is False  # Lowercase
    assert validate_booking_ref("ABC-123") is False  # Special chars


def test_validate_booking_ref_invalid_type():
    """Test booking ref validation rejects non-strings."""
    assert validate_booking_ref(123456) is False
    assert validate_booking_ref(None) is False


def test_validate_passenger_count_valid():
    """Test passenger count validation with valid counts."""
    assert validate_passenger_count(1) is True
    assert validate_passenger_count(4) is True
    assert validate_passenger_count(9) is True


def test_validate_passenger_count_invalid():
    """Test passenger count validation rejects invalid counts."""
    assert validate_passenger_count(0) is False  # Too low
    assert validate_passenger_count(10) is False  # Too high
    assert validate_passenger_count(-1) is False  # Negative
