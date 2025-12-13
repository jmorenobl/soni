"""Domain configurations for dataset generation.

Each domain represents a business context (e.g., flight booking, hotel booking)
with its own set of flows, actions, and slots.
"""

from soni.dataset.domains.banking import BANKING
from soni.dataset.domains.ecommerce import ECOMMERCE
from soni.dataset.domains.flight_booking import FLIGHT_BOOKING
from soni.dataset.domains.hotel_booking import HOTEL_BOOKING
from soni.dataset.domains.restaurant import RESTAURANT

# Registry of all available domains
ALL_DOMAINS = {
    "flight_booking": FLIGHT_BOOKING,
    "hotel_booking": HOTEL_BOOKING,
    "restaurant": RESTAURANT,
    "ecommerce": ECOMMERCE,
    "banking": BANKING,
}

__all__ = [
    "FLIGHT_BOOKING",
    "HOTEL_BOOKING",
    "RESTAURANT",
    "ECOMMERCE",
    "BANKING",
    "ALL_DOMAINS",
]
