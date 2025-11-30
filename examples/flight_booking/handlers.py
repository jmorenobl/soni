"""Action handlers for flight booking example"""

import logging
from typing import Any

from soni.actions.registry import ActionRegistry

logger = logging.getLogger(__name__)


@ActionRegistry.register("search_available_flights")
async def search_available_flights(
    origin: str,
    destination: str,
    departure_date: str,
) -> dict[str, Any]:
    """
    Search for available flights.

    This is a mock implementation for MVP.
    In production, this would call a real flight API.

    Args:
        origin: Departure city
        destination: Destination city
        departure_date: Departure date

    Returns:
        Dictionary with flights and price
    """
    logger.info(f"Searching flights: {origin} -> {destination} on {departure_date}")

    # Mock flight data
    flights = [
        {
            "flight_number": "AA123",
            "departure_time": "08:00",
            "arrival_time": "10:30",
            "price": 299.99,
        },
        {
            "flight_number": "UA456",
            "departure_time": "14:00",
            "arrival_time": "16:30",
            "price": 349.99,
        },
    ]

    min_price = min(f["price"] for f in flights)  # type: ignore[type-var]
    return {
        "flights": flights,
        "price": min_price,
    }


@ActionRegistry.register("confirm_flight_booking")
async def confirm_flight_booking(
    flights: list[dict[str, Any]],
    origin: str,
    destination: str,
    departure_date: str,
) -> dict[str, Any]:
    """
    Confirm flight booking.

    This is a mock implementation for MVP.
    In production, this would create a real booking.

    Args:
        flights: List of available flights
        origin: Departure city
        destination: Destination city
        departure_date: Departure date

    Returns:
        Dictionary with booking reference and confirmation
    """
    logger.info(f"Confirming booking: {origin} -> {destination} on {departure_date}")

    # Select first flight (in real system, user would choose)
    selected_flight = flights[0] if flights else None

    if not selected_flight:
        raise ValueError("No flights available to book")

    # Mock booking reference
    booking_ref = f"BK-{selected_flight['flight_number']}-2024-001"

    return {
        "booking_ref": booking_ref,
        "confirmation": f"Your flight {selected_flight['flight_number']} from {origin} to {destination} on {departure_date} has been confirmed. Booking reference: {booking_ref}",
    }
