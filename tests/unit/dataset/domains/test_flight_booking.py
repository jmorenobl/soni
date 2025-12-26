"""Tests for flight_booking domain data."""

import pytest

from soni.dataset.base import DomainConfig
from soni.dataset.domains.flight_booking import FLIGHT_BOOKING


def test_flight_booking_domain_config():
    """Flight booking should be a valid DomainConfig."""
    assert isinstance(FLIGHT_BOOKING, DomainConfig)
    assert FLIGHT_BOOKING.name == "flight_booking"
    assert "book_flight" in FLIGHT_BOOKING.available_flows
    assert "destination" in FLIGHT_BOOKING.slots
