"""CLARIFICATION pattern generator.

Asking why info is needed.

Examples:
    - "Why do you need my email?"
    - "What's this for?"
"""

from typing import Literal

import dspy

from soni.core.commands import Clarify
from soni.dataset.base import (
    ConversationContext,
    DomainConfig,
    ExampleTemplate,
    PatternGenerator,
)
from soni.du.models import NLUOutput


class ClarificationGenerator(PatternGenerator):
    """Generates CLARIFICATION pattern examples."""

    def generate_examples(
        self,
        domain_config: DomainConfig,
        context_type: Literal["cold_start", "ongoing"],
        count: int = 3,
    ) -> list[ExampleTemplate]:
        """Generate CLARIFICATION examples (ongoing only)."""
        if context_type == "cold_start":
            return []  # Clarifications only happen in ongoing conversations

        return self._generate_ongoing_examples(domain_config, count)

    def _generate_ongoing_examples(
        self,
        domain_config: DomainConfig,
        count: int,
    ) -> list[ExampleTemplate]:
        """Generate clarification examples."""
        examples = []

        clarification_questions = [
            "Why do you need that?",
            "What's this for?",
            "Why is that necessary?",
        ]

        if domain_config.name == "flight_booking":
            # Example 1
            examples.append(
                ExampleTemplate(
                    user_message=clarification_questions[0],
                    conversation_context=ConversationContext(
                        history=dspy.History(
                            messages=[
                                {"user_message": "Book a flight"},
                                {"user_message": "From Madrid"},
                            ]
                        ),
                        current_slots={"origin": "Madrid"},
                        current_flow="book_flight",
                        expected_slots=["destination"],
                    ),
                    expected_output=NLUOutput(
                        commands=[
                            Clarify(topic="reason for destination"),
                        ],
                        confidence=0.9,
                    ),
                    domain=domain_config.name,
                    pattern="clarification",
                    context_type="ongoing",
                    current_datetime="2024-12-11T10:00:00",
                )
            )
            # Example 2: Passport clarification
            examples.append(
                ExampleTemplate(
                    user_message="Why do you need my passport number?",
                    conversation_context=ConversationContext(
                        history=dspy.History(
                            messages=[
                                {"user_message": "Book a flight to New York"},
                            ]
                        ),
                        current_slots={"origin": "London", "destination": "New York"},
                        current_flow="book_flight",
                        expected_slots=["passport_number"],
                    ),
                    expected_output=NLUOutput(
                        commands=[
                            Clarify(topic="passport number"),
                        ],
                        confidence=0.95,
                    ),
                    domain=domain_config.name,
                    pattern="clarification",
                    context_type="ongoing",
                    current_datetime="2024-12-11T10:00:00",
                )
            )
            # Example 3: Redress number
            examples.append(
                ExampleTemplate(
                    user_message="What is a redress number?",
                    conversation_context=ConversationContext(
                        history=dspy.History(
                            messages=[
                                {"user_message": "I want to book a flight"},
                            ]
                        ),
                        current_slots={},
                        current_flow="book_flight",
                        expected_slots=["redress_number"],
                    ),
                    expected_output=NLUOutput(
                        commands=[
                            Clarify(topic="redress number"),
                        ],
                        confidence=0.9,
                    ),
                    domain=domain_config.name,
                    pattern="clarification",
                    context_type="ongoing",
                    current_datetime="2024-12-11T10:00:00",
                )
            )

        elif domain_config.name == "hotel_booking":
            # Example 1
            examples.append(
                ExampleTemplate(
                    user_message=clarification_questions[1],
                    conversation_context=ConversationContext(
                        history=dspy.History(
                            messages=[
                                {"user_message": "Book a hotel"},
                            ]
                        ),
                        current_slots={},
                        current_flow="book_hotel",
                        expected_slots=["location"],
                    ),
                    expected_output=NLUOutput(
                        commands=[
                            Clarify(topic="reason for location"),
                        ],
                        confidence=0.9,
                    ),
                    domain=domain_config.name,
                    pattern="clarification",
                    context_type="ongoing",
                    current_datetime="2024-12-11T10:00:00",
                )
            )
            # Example 2: Credit card
            examples.append(
                ExampleTemplate(
                    user_message="Is a credit card required?",
                    conversation_context=ConversationContext(
                        history=dspy.History(
                            messages=[
                                {"user_message": "I'd like to reserve a room"},
                            ]
                        ),
                        current_slots={"location": "Paris"},
                        current_flow="book_hotel",
                        expected_slots=["payment_method"],
                    ),
                    expected_output=NLUOutput(
                        commands=[
                            Clarify(topic="credit card requirement"),
                        ],
                        confidence=0.9,
                    ),
                    domain=domain_config.name,
                    pattern="clarification",
                    context_type="ongoing",
                    current_datetime="2024-12-11T10:00:00",
                )
            )
            # Example 3: Deposit
            examples.append(
                ExampleTemplate(
                    user_message="Why do I need to pay a deposit?",
                    conversation_context=ConversationContext(
                        history=dspy.History(
                            messages=[
                                {"user_message": "Book the suite"},
                            ]
                        ),
                        current_slots={"room_type": "suite"},
                        current_flow="book_hotel",
                        expected_slots=["deposit"],
                    ),
                    expected_output=NLUOutput(
                        commands=[
                            Clarify(topic="deposit reason"),
                        ],
                        confidence=0.95,
                    ),
                    domain=domain_config.name,
                    pattern="clarification",
                    context_type="ongoing",
                    current_datetime="2024-12-11T10:00:00",
                )
            )

        elif domain_config.name == "restaurant":
            # Example 1
            examples.append(
                ExampleTemplate(
                    user_message=clarification_questions[2],
                    conversation_context=ConversationContext(
                        history=dspy.History(
                            messages=[
                                {"user_message": "Book a table"},
                            ]
                        ),
                        current_slots={},
                        current_flow="book_table",
                        expected_slots=["location"],
                    ),
                    expected_output=NLUOutput(
                        commands=[
                            Clarify(topic="reason for location"),
                        ],
                        confidence=0.9,
                    ),
                    domain=domain_config.name,
                    pattern="clarification",
                    context_type="ongoing",
                    current_datetime="2024-12-11T10:00:00",
                )
            )
            # Example 2: Phone number
            examples.append(
                ExampleTemplate(
                    user_message="Why do you need my phone number?",
                    conversation_context=ConversationContext(
                        history=dspy.History(
                            messages=[
                                {"user_message": "Reserve for 2 people"},
                            ]
                        ),
                        current_slots={"party_size": "2"},
                        current_flow="book_table",
                        expected_slots=["phone_number"],
                    ),
                    expected_output=NLUOutput(
                        commands=[
                            Clarify(topic="phone number reason"),
                        ],
                        confidence=0.95,
                    ),
                    domain=domain_config.name,
                    pattern="clarification",
                    context_type="ongoing",
                    current_datetime="2024-12-11T10:00:00",
                )
            )
            # Example 3: Dress code
            examples.append(
                ExampleTemplate(
                    user_message="Is there a dress code?",
                    conversation_context=ConversationContext(
                        history=dspy.History(
                            messages=[
                                {"user_message": "I want to book dinner"},
                            ]
                        ),
                        current_slots={},
                        current_flow="book_table",
                        expected_slots=["time"],
                    ),
                    expected_output=NLUOutput(
                        commands=[
                            Clarify(topic="dress code"),
                        ],
                        confidence=0.85,
                    ),
                    domain=domain_config.name,
                    pattern="clarification",
                    context_type="ongoing",
                    current_datetime="2024-12-11T10:00:00",
                )
            )

        elif domain_config.name == "ecommerce":
            # Example 1
            examples.append(
                ExampleTemplate(
                    user_message="Why do you need my address?",
                    conversation_context=ConversationContext(
                        history=dspy.History(
                            messages=[
                                {"user_message": "I want to buy a laptop"},
                            ]
                        ),
                        current_slots={"product": "laptop"},
                        current_flow="search_product",
                        expected_slots=["shipping_address"],
                    ),
                    expected_output=NLUOutput(
                        commands=[
                            Clarify(topic="shipping address reason"),
                        ],
                        confidence=0.9,
                    ),
                    domain=domain_config.name,
                    pattern="clarification",
                    context_type="ongoing",
                    current_datetime="2024-12-11T10:00:00",
                )
            )
            # Example 2: Email
            examples.append(
                ExampleTemplate(
                    user_message="What do you use my email for?",
                    conversation_context=ConversationContext(
                        history=dspy.History(
                            messages=[
                                {"user_message": "Buy these shoes"},
                            ]
                        ),
                        current_slots={"product": "shoes"},
                        current_flow="search_product",
                        expected_slots=["email"],
                    ),
                    expected_output=NLUOutput(
                        commands=[
                            Clarify(topic="email usage"),
                        ],
                        confidence=0.9,
                    ),
                    domain=domain_config.name,
                    pattern="clarification",
                    context_type="ongoing",
                    current_datetime="2024-12-11T10:00:00",
                )
            )
            # Example 3: Phone
            examples.append(
                ExampleTemplate(
                    user_message="Is my phone number necessary?",
                    conversation_context=ConversationContext(
                        history=dspy.History(
                            messages=[
                                {"user_message": "Checkout"},
                            ]
                        ),
                        current_slots={},
                        current_flow="search_product",
                        expected_slots=["phone"],
                    ),
                    expected_output=NLUOutput(
                        commands=[
                            Clarify(topic="phone number requirement"),
                        ],
                        confidence=0.9,
                    ),
                    domain=domain_config.name,
                    pattern="clarification",
                    context_type="ongoing",
                    current_datetime="2024-12-11T10:00:00",
                )
            )

        elif domain_config.name == "banking":
            from soni.dataset.domains.banking import (
                CLARIFICATION_UTTERANCES,
                create_context_after_transfer,
            )

            # Example 1: Ambiguity with account
            examples.append(
                ExampleTemplate(
                    user_message=CLARIFICATION_UTTERANCES[0],  # "Which account?"
                    conversation_context=create_context_after_transfer(
                        amount="100", currency="USD", recipient="mom"
                    ),
                    expected_output=NLUOutput(
                        commands=[
                            Clarify(topic="which account"),
                        ],
                        confidence=0.9,
                    ),
                    domain=domain_config.name,
                    pattern="clarification",
                    context_type="ongoing",
                    current_datetime="2024-12-11T10:00:00",
                )
            )
            # Example 2: Fee clarification
            examples.append(
                ExampleTemplate(
                    user_message="Is there a transfer fee?",
                    conversation_context=create_context_after_transfer(
                        amount="500", currency="EUR", recipient="Alice"
                    ),
                    expected_output=NLUOutput(
                        commands=[
                            Clarify(topic="transfer fee"),
                        ],
                        confidence=0.85,
                    ),
                    domain=domain_config.name,
                    pattern="clarification",
                    context_type="ongoing",
                    current_datetime="2024-12-11T10:00:00",
                )
            )
            # Example 3: Limit clarification
            examples.append(
                ExampleTemplate(
                    user_message="What is the daily limit?",
                    conversation_context=create_context_after_transfer(
                        amount="5000", currency="USD", recipient="Bob"
                    ),
                    expected_output=NLUOutput(
                        commands=[
                            Clarify(topic="daily limit"),
                        ],
                        confidence=0.85,
                    ),
                    domain=domain_config.name,
                    pattern="clarification",
                    context_type="ongoing",
                    current_datetime="2024-12-11T10:00:00",
                )
            )

        return examples[:count]
