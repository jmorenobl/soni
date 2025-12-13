"""E-commerce shopping domain configuration and example data."""

import dspy

from soni.dataset.base import ConversationContext, DomainConfig

# Domain configuration
ECOMMERCE = DomainConfig(
    name="ecommerce",
    description="Shop for products and manage orders",
    available_flows=[
        "search_product",
        "add_to_cart",
        "checkout",
        "track_order",
        "return_product",
    ],
    available_actions=[
        "search_products",
        "add_to_cart",
        "process_payment",
        "track_shipment",
        "initiate_return",
    ],
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
)

# Example data
PRODUCTS = [
    "laptop",
    "phone",
    "headphones",
    "camera",
    "tablet",
    "smartwatch",
]

COLORS = [
    "black",
    "white",
    "silver",
    "blue",
    "red",
]

SIZES = [
    "small",
    "medium",
    "large",
    "XL",
]

QUANTITIES = [1, 2, 3, 5]

SEARCH_UTTERANCES = [
    "I'm looking for a",
    "Show me",
    "I want to buy a",
    "Can you help me find a",
]

# Confirmation responses - consistent across domains
CONFIRMATION_POSITIVE = [
    "Yes",
    "Correct",
    "That's right",
    "Yes, add it to cart",
    "Confirmed",
    "Yeah",
    "Perfect",
]

CONFIRMATION_NEGATIVE = [
    "No",
    "That's wrong",
    "No, that's not right",
    "Incorrect",
    "Nope",
    # Negative with modification intent
    "No, different color",
    "No, change the size",
    "No, I want a different one",
    "No, let me modify that",
    "No, wrong product",
]

CONFIRMATION_UNCLEAR = [
    "hmm, I'm not sure",
    "maybe",
    "hmm",
    "I don't know",
    "I'm not sure",
    "Let me think",
    "Not really sure",
    "Perhaps",
    "Maybe",
    "um...",
    "let me check",
]

CANCELLATION_UTTERANCES = [
    "Cancel",
    "Never mind",
    "Forget it",
    "I changed my mind",
    "Stop",
    "Remove from cart",
    "Actually, cancel this",
]

# Invalid responses - for testing NLU rejection/clarification
INVALID_RESPONSES = {
    "product": ["sunshine", "happiness", "asdf", "123", "purple feeling"],
    "quantity": ["some", "a lot", "purple", "many", "asdf"],
    "color": ["123", "asdf", "happiness", "very", "the"],
    "size": ["pizza", "asdf", "123", "blue", "happiness"],
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
