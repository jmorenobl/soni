"""Tests for hotel_booking domain data."""

import pytest

from soni.dataset.base import DomainConfig
from soni.dataset.domains.hotel_booking import HOTEL_BOOKING


def test_hotel_booking_domain_config():
    """Hotel booking should be a valid DomainConfig."""
    assert isinstance(HOTEL_BOOKING, DomainConfig)
    assert HOTEL_BOOKING.name == "hotel_booking"
    assert "book_hotel" in HOTEL_BOOKING.available_flows
    # In hotel_booking, 'city' might be 'location'
    assert any(s in HOTEL_BOOKING.slots for s in ["city", "location"])
