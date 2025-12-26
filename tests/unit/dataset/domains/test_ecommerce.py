"""Tests for ecommerce domain data."""

import pytest

from soni.dataset.base import DomainConfig
from soni.dataset.domains.ecommerce import ECOMMERCE


def test_ecommerce_domain_config():
    """Ecommerce should be a valid DomainConfig."""
    assert isinstance(ECOMMERCE, DomainConfig)
    assert ECOMMERCE.name == "ecommerce"
    assert any("search_product" in f for f in ECOMMERCE.available_flows)
    # The slot is 'product', not 'product_name'
    assert "product" in ECOMMERCE.slots
