"""Tests for dataset domains module."""

import pytest
from soni.dataset.domains import ALL_DOMAINS
from soni.dataset.domains.banking import BANKING
from soni.dataset.domains.ecommerce import ECOMMERCE
from soni.dataset.domains.flight_booking import FLIGHT_BOOKING
from soni.dataset.domains.hotel_booking import HOTEL_BOOKING
from soni.dataset.domains.restaurant import RESTAURANT


class TestAllDomainsRegistry:
    """Tests for ALL_DOMAINS registry."""

    def test_all_domains_contains_five_domains(self):
        """Verify all 5 domains are registered."""
        assert len(ALL_DOMAINS) == 5

    def test_all_domains_keys(self):
        """Verify expected domain keys exist."""
        expected_keys = {"flight_booking", "hotel_booking", "restaurant", "ecommerce", "banking"}
        assert set(ALL_DOMAINS.keys()) == expected_keys

    @pytest.mark.parametrize("domain_name", list(ALL_DOMAINS.keys()))
    def test_each_domain_has_example_data(self, domain_name):
        """Verify each domain has example_data populated."""
        domain = ALL_DOMAINS[domain_name]
        assert domain.example_data is not None
        assert len(domain.example_data.slot_values) > 0


class TestFlightBookingDomain:
    """Tests for flight_booking domain."""

    def test_domain_name(self):
        """Test domain name is correct."""
        assert FLIGHT_BOOKING.name == "flight_booking"

    def test_has_flows(self):
        """Test domain has available flows."""
        assert len(FLIGHT_BOOKING.available_flows) > 0
        assert "book_flight" in FLIGHT_BOOKING.available_flows

    def test_has_slots(self):
        """Test domain has slots defined."""
        assert len(FLIGHT_BOOKING.slots) > 0
        assert "origin" in FLIGHT_BOOKING.slots
        assert "destination" in FLIGHT_BOOKING.slots

    def test_example_data_slot_values(self):
        """Test example data has slot values."""
        assert len(FLIGHT_BOOKING.example_data.slot_values) > 0
        cities = FLIGHT_BOOKING.get_slot_values("origin")
        assert len(cities) > 0

    def test_example_data_trigger_intents(self):
        """Test example data has trigger intents."""
        intents = FLIGHT_BOOKING.get_trigger_intents("book_flight")
        assert len(intents) > 0


class TestHotelBookingDomain:
    """Tests for hotel_booking domain."""

    def test_domain_name(self):
        """Test domain name is correct."""
        assert HOTEL_BOOKING.name == "hotel_booking"

    def test_has_flows(self):
        """Test domain has available flows."""
        assert len(HOTEL_BOOKING.available_flows) > 0

    def test_has_slots(self):
        """Test domain has slots defined."""
        assert len(HOTEL_BOOKING.slots) > 0

    def test_example_data_slot_values(self):
        """Test example data has slot values."""
        assert len(HOTEL_BOOKING.example_data.slot_values) > 0


class TestRestaurantDomain:
    """Tests for restaurant domain."""

    def test_domain_name(self):
        """Test domain name is correct."""
        assert RESTAURANT.name == "restaurant"

    def test_has_flows(self):
        """Test domain has available flows."""
        assert len(RESTAURANT.available_flows) > 0

    def test_has_slots(self):
        """Test domain has slots defined."""
        assert len(RESTAURANT.slots) > 0

    def test_example_data_slot_values(self):
        """Test example data has slot values."""
        assert len(RESTAURANT.example_data.slot_values) > 0


class TestEcommerceDomain:
    """Tests for ecommerce domain."""

    def test_domain_name(self):
        """Test domain name is correct."""
        assert ECOMMERCE.name == "ecommerce"

    def test_has_flows(self):
        """Test domain has available flows."""
        assert len(ECOMMERCE.available_flows) > 0

    def test_has_slots(self):
        """Test domain has slots defined."""
        assert len(ECOMMERCE.slots) > 0

    def test_example_data_slot_values(self):
        """Test example data has slot values."""
        assert len(ECOMMERCE.example_data.slot_values) > 0


class TestBankingDomain:
    """Tests for banking domain."""

    def test_domain_name(self):
        """Test domain name is correct."""
        assert BANKING.name == "banking"

    def test_has_flows(self):
        """Test domain has available flows."""
        assert len(BANKING.available_flows) > 0

    def test_has_slots(self):
        """Test domain has slots defined."""
        assert len(BANKING.slots) > 0

    def test_example_data_slot_values(self):
        """Test example data has slot values."""
        assert len(BANKING.example_data.slot_values) > 0

    def test_has_multiple_flows(self):
        """Banking should have multiple flows."""
        assert len(BANKING.available_flows) >= 2
