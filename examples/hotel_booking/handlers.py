from soni.actions.registry import ActionRegistry

registry = ActionRegistry.get_default()


@registry.register("search_hotels")
async def search_hotels(slots: dict):
    return f"Searching hotels in {slots.get('location')}..."


@registry.register("book_hotel")
async def book_hotel(slots: dict):
    return f"Booking {slots.get('room_type')} in {slots.get('location')}..."


@registry.register("modify_reservation")
async def modify_reservation(slots: dict):
    return "Modification processed."


@registry.register("cancel_reservation")
async def cancel_reservation(slots: dict):
    return "Reservation cancelled."
