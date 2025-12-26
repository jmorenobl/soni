"""Tests for banking domain data."""

import pytest

from soni.dataset.base import DomainConfig, DomainExampleData
from soni.dataset.domains.banking import BANKING


def test_banking_domain_config():
    """Banking should be a valid DomainConfig."""
    assert isinstance(BANKING, DomainConfig)
    assert BANKING.name == "banking"
    assert "transfer_funds" in BANKING.available_flows
    assert "amount" in BANKING.slots


def test_banking_example_data():
    """Banking should have rich example data."""
    data = BANKING.example_data
    assert isinstance(data, DomainExampleData)
    assert "amount" in data.slot_values
    assert "checking" in data.slot_values["account_type"]
    assert len(data.trigger_intents["transfer_funds"]) > 0
    assert len(data.slot_extraction_cases) > 0
