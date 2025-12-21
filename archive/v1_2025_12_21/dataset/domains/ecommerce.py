"""E-commerce shopping domain configuration and example data."""

import dspy

from soni.dataset.base import ConversationContext, DomainConfig, DomainExampleData

# Example data constants
PRODUCTS = ["laptop", "phone", "headphones", "camera", "tablet", "smartwatch"]
COLORS = ["black", "white", "silver", "blue", "red"]
SIZES = ["small", "medium", "large", "XL"]
QUANTITIES = ["1", "2", "3", "5"]

# Build DomainExampleData
_EXAMPLE_DATA = DomainExampleData(
    slot_values={
        "product": PRODUCTS,
        "quantity": QUANTITIES,
        "color": COLORS,
        "size": SIZES,
        "shipping_address": ["123 Main St", "456 Oak Ave", "789 Pine Rd"],
    },
    trigger_intents={
        "search_product": [
            "I'm looking for a",
            "Show me",
            "I want to buy a",
            "Can you help me find a",
        ],
    },
    confirmation_positive=["Yes", "Correct", "That's right", "Confirmed", "Yeah", "Perfect"],
    confirmation_negative=["No", "That's wrong", "Incorrect", "Nope"],
    confirmation_unclear=["hmm, I'm not sure", "maybe", "I don't know", "Let me think", "um..."],
    # Multi-slot extraction examples for SlotExtractor optimization
    slot_extraction_cases=[
        # Product + Quantity
        (
            "I want 2 laptops",
            [
                {"slot": "quantity", "value": "2"},
                {"slot": "product", "value": "laptops"},
            ],
        ),
        (
            "3 black headphones",
            [
                {"slot": "quantity", "value": "3"},
                {"slot": "color", "value": "black"},
                {"slot": "product", "value": "headphones"},
            ],
        ),
        # Product + Color + Size
        (
            "Blue phone in large size",
            [
                {"slot": "color", "value": "blue"},
                {"slot": "product", "value": "phone"},
                {"slot": "size", "value": "large"},
            ],
        ),
        (
            "Silver tablet, medium",
            [
                {"slot": "color", "value": "silver"},
                {"slot": "product", "value": "tablet"},
                {"slot": "size", "value": "medium"},
            ],
        ),
        # Full order
        (
            "Order 2 white cameras to 123 Main St",
            [
                {"slot": "quantity", "value": "2"},
                {"slot": "color", "value": "white"},
                {"slot": "product", "value": "cameras"},
                {"slot": "shipping_address", "value": "123 Main St"},
            ],
        ),
        # Negative examples
        ("I'm looking for something", []),
        ("Show me products", []),
    ],
)

# Domain configuration
ECOMMERCE = DomainConfig(
    name="ecommerce",
    description="Shop for products and manage orders",
    available_flows=["search_product", "add_to_cart", "checkout", "track_order", "return_product"],
    available_actions=[
        "search_products",
        "add_to_cart",
        "process_payment",
        "track_shipment",
        "initiate_return",
    ],
    flow_descriptions={
        "search_product": "Search for products by name or category",
        "add_to_cart": "Add products to your shopping cart",
        "checkout": "Complete purchase and payment",
        "track_order": "Track the status of an order shipment",
        "return_product": "Return a product and get a refund",
    },
    slots={
        "product": "string",
        "quantity": "number",
        "color": "string",
        "size": "string",
        "shipping_address": "address",
    },
    slot_prompts={
        "product": "What product are you looking for?",
        "quantity": "How many would you like to order?",
        "color": "What color would you prefer?",
        "size": "What size do you need?",
        "shipping_address": "What's the shipping address?",
    },
    example_data=_EXAMPLE_DATA,
)

# Legacy exports for backward-compatibility
SEARCH_UTTERANCES = _EXAMPLE_DATA.trigger_intents.get("search_product", [])
CONFIRMATION_POSITIVE = _EXAMPLE_DATA.confirmation_positive
CONFIRMATION_NEGATIVE = _EXAMPLE_DATA.confirmation_negative
CONFIRMATION_UNCLEAR = _EXAMPLE_DATA.confirmation_unclear

CANCELLATION_UTTERANCES = ["Cancel", "Never mind", "Forget it", "I changed my mind", "Stop"]

# Invalid responses for testing
INVALID_RESPONSES = {
    "product": ["sunshine", "happiness", "asdf", "123", "purple feeling"],
    "quantity": ["some", "a lot", "purple", "many", "asdf"],
    "color": ["123", "asdf", "happiness", "very"],
    "size": ["pizza", "asdf", "123", "blue"],
    "shipping_address": ["asdf", "123", "pizza", "the moon"],
}


def create_empty_shopping_context() -> ConversationContext:
    """Create context for new shopping session.

    Returns:
        ConversationContext with empty history and no filled slots
    """
    return ConversationContext(
        history=dspy.History(messages=[]),
        current_slots={},
        current_flow="none",
        expected_slots=["product", "quantity"],
    )


def create_context_after_product(product: str = "laptop") -> ConversationContext:
    """Create context after user specified product.

    Args:
        product: Product name (default: "laptop")

    Returns:
        ConversationContext with product filled, asking for quantity/attributes
    """
    return ConversationContext(
        history=dspy.History(
            messages=[
                {
                    "user_message": f"I want to buy a {product}",
                    "result": {
                        "command": "search_product",
                        "message_type": "interruption",
                        "slots": [{"name": "product", "value": product}],
                    },
                },
            ]
        ),
        current_slots={"product": product},
        current_flow="search_product",
        expected_slots=["quantity", "color", "size"],
    )
