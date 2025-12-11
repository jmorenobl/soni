"""Unit tests for domain configurations."""

import dspy
import pytest

from soni.dataset.base import ConversationContext, DomainConfig
from soni.dataset.domains.ecommerce import (
    ECOMMERCE,
    create_context_after_product,
    create_empty_shopping_context,
)
from soni.dataset.domains.flight_booking import (
    CABIN_CLASSES,
    CITIES,
    FLIGHT_BOOKING,
    create_context_after_origin,
    create_context_after_origin_destination,
    create_context_before_confirmation,
    create_empty_flight_context,
)
from soni.dataset.domains.hotel_booking import (
    HOTEL_BOOKING,
    create_empty_hotel_context,
)
from soni.dataset.domains.hotel_booking import (
    create_context_after_location as create_hotel_context_after_location,
)
from soni.dataset.domains.restaurant import (
    RESTAURANT,
    create_empty_restaurant_context,
)
from soni.dataset.domains.restaurant import (
    create_context_after_location as create_restaurant_context_after_location,
)


def test_flight_booking_domain_is_valid():
    """Test FLIGHT_BOOKING domain configuration is valid."""
    # Assert
    assert isinstance(FLIGHT_BOOKING, DomainConfig)
    assert FLIGHT_BOOKING.name == "flight_booking"
    assert len(FLIGHT_BOOKING.available_flows) > 0
    assert len(FLIGHT_BOOKING.available_actions) > 0
    assert len(FLIGHT_BOOKING.slots) > 0


def test_flight_booking_has_required_slots():
    """Test flight booking domain has all required slots."""
    # Arrange
    required_slots = ["origin", "destination", "departure_date"]

    # Assert
    for slot in required_slots:
        assert slot in FLIGHT_BOOKING.slots
        assert slot in FLIGHT_BOOKING.slot_prompts


def test_flight_booking_has_required_flows():
    """Test flight booking domain has common flows."""
    # Arrange
    required_flows = ["book_flight", "search_flights"]

    # Assert
    for flow in required_flows:
        assert flow in FLIGHT_BOOKING.available_flows


def test_cities_list_has_variety():
    """Test CITIES list has sufficient variety."""
    # Assert
    assert len(CITIES) >= 5
    assert "Madrid" in CITIES
    assert "Barcelona" in CITIES


def test_cabin_classes_list_is_complete():
    """Test CABIN_CLASSES has all standard classes."""
    # Arrange
    expected_classes = ["economy", "business", "first class"]

    # Assert
    for cabin_class in expected_classes:
        assert cabin_class in CABIN_CLASSES


def test_create_empty_flight_context():
    """Test creating empty flight context."""
    # Act
    context = create_empty_flight_context()

    # Assert
    assert isinstance(context, ConversationContext)
    assert len(context.history.messages) == 0
    assert len(context.current_slots) == 0
    assert context.current_flow == "none"
    assert "origin" in context.expected_slots


def test_create_context_after_origin():
    """Test creating context after origin is provided."""
    # Act
    context = create_context_after_origin(origin="Paris")

    # Assert
    assert isinstance(context, ConversationContext)
    assert len(context.history.messages) == 2
    assert context.current_slots["origin"] == "Paris"
    assert context.current_flow == "book_flight"
    assert "destination" in context.expected_slots


def test_create_context_after_origin_destination():
    """Test creating context after origin and destination are provided."""
    # Act
    context = create_context_after_origin_destination(origin="London", destination="New York")

    # Assert
    assert isinstance(context, ConversationContext)
    assert context.current_slots["origin"] == "London"
    assert context.current_slots["destination"] == "New York"
    assert context.current_flow == "book_flight"
    assert "departure_date" in context.expected_slots


def test_create_context_before_confirmation():
    """Test creating context with all slots filled."""
    # Act
    context = create_context_before_confirmation(
        origin="Tokyo", destination="Paris", departure_date="next Monday"
    )

    # Assert
    assert isinstance(context, ConversationContext)
    assert context.current_slots["origin"] == "Tokyo"
    assert context.current_slots["destination"] == "Paris"
    assert context.current_slots["departure_date"] == "next Monday"
    assert len(context.expected_slots) == 0  # All filled


def test_helper_functions_use_defaults():
    """Test helper functions work with default values."""
    # Act
    context1 = create_context_after_origin()
    context2 = create_context_after_origin_destination()
    context3 = create_context_before_confirmation()

    # Assert - should not raise and should have sensible defaults
    assert context1.current_slots["origin"] == "Madrid"
    assert context2.current_slots["destination"] == "Barcelona"
    assert context3.current_slots["departure_date"] == "tomorrow"


# Hotel Booking Tests


def test_hotel_booking_domain_is_valid():
    """Test HOTEL_BOOKING domain configuration is valid."""
    assert isinstance(HOTEL_BOOKING, DomainConfig)
    assert HOTEL_BOOKING.name == "hotel_booking"
    assert "book_hotel" in HOTEL_BOOKING.available_flows


def test_hotel_booking_has_required_slots():
    """Test hotel booking has location and date slots."""
    required_slots = ["location", "checkin_date", "checkout_date"]
    for slot in required_slots:
        assert slot in HOTEL_BOOKING.slots


def test_create_empty_hotel_context():
    """Test creating empty hotel context."""
    context = create_empty_hotel_context()
    assert len(context.history.messages) == 0
    assert context.current_flow == "none"


def test_create_hotel_context_after_location():
    """Test creating hotel context after location."""
    context = create_hotel_context_after_location(location="Paris")
    assert context.current_slots["location"] == "Paris"
    assert context.current_flow == "book_hotel"


# Restaurant Tests


def test_restaurant_domain_is_valid():
    """Test RESTAURANT domain configuration is valid."""
    assert isinstance(RESTAURANT, DomainConfig)
    assert RESTAURANT.name == "restaurant"
    assert "book_table" in RESTAURANT.available_flows


def test_restaurant_has_required_slots():
    """Test restaurant has location, date, time, party_size slots."""
    required_slots = ["location", "date", "time", "party_size"]
    for slot in required_slots:
        assert slot in RESTAURANT.slots


def test_create_empty_restaurant_context():
    """Test creating empty restaurant context."""
    context = create_empty_restaurant_context()
    assert len(context.history.messages) == 0
    assert context.current_flow == "none"


def test_create_restaurant_context_after_location():
    """Test creating restaurant context after location."""
    context = create_restaurant_context_after_location(location="Tokyo")
    assert context.current_slots["location"] == "Tokyo"
    assert context.current_flow == "book_table"


# Ecommerce Tests


def test_ecommerce_domain_is_valid():
    """Test ECOMMERCE domain configuration is valid."""
    assert isinstance(ECOMMERCE, DomainConfig)
    assert ECOMMERCE.name == "ecommerce"
    assert "search_product" in ECOMMERCE.available_flows


def test_ecommerce_has_required_slots():
    """Test ecommerce has product, quantity slots."""
    required_slots = ["product", "quantity"]
    for slot in required_slots:
        assert slot in ECOMMERCE.slots


def test_create_empty_shopping_context():
    """Test creating empty shopping context."""
    context = create_empty_shopping_context()
    assert len(context.history.messages) == 0
    assert context.current_flow == "none"


def test_create_context_after_product():
    """Test creating context after product."""
    context = create_context_after_product(product="laptop")
    assert context.current_slots["product"] == "laptop"
    assert context.current_flow == "search_product"
