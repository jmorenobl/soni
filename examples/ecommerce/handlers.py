from soni.actions.registry import ActionRegistry

registry = ActionRegistry.get_default()


@registry.register("search_products")
async def search_products(slots: dict):
    return f"Searching for {slots.get('product')}..."


@registry.register("add_to_cart")
async def add_to_cart(slots: dict):
    return f"Adding {slots.get('quantity')} {slots.get('product')} to cart."


@registry.register("process_payment")
async def process_payment(slots: dict):
    return f"Processing payment for shipping to {slots.get('shipping_address')}."
