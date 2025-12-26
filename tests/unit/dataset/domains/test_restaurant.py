"""Tests for restaurant domain data."""

import pytest

from soni.dataset.base import DomainConfig
from soni.dataset.domains.restaurant import RESTAURANT


def test_restaurant_domain_config():
    """Restaurant should be a valid DomainConfig."""
    assert isinstance(RESTAURANT, DomainConfig)
    assert RESTAURANT.name == "restaurant"
    assert "book_table" in RESTAURANT.available_flows
    assert "cuisine" in RESTAURANT.slots
