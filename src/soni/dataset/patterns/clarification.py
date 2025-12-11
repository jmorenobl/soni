"""CLARIFICATION pattern generator.

Asking why info is needed.

Examples:
    - "Why do you need my email?"
    - "What's this for?"
"""

from typing import Literal

import dspy

from soni.dataset.base import (
    ConversationContext,
    DomainConfig,
    ExampleTemplate,
    PatternGenerator,
)
from soni.du.models import MessageType, NLUOutput


class ClarificationGenerator(PatternGenerator):
    """Generates CLARIFICATION pattern examples."""

    @property
    def message_type(self) -> MessageType:
        return MessageType.CLARIFICATION

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
                        message_type=MessageType.CLARIFICATION,
                        command="book_flight",
                        slots=[],
                        confidence=0.9,
                    ),
                    domain=domain_config.name,
                    pattern="clarification",
                    context_type="ongoing",
                    current_datetime="2024-12-11T10:00:00",
                )
            )

        elif domain_config.name == "hotel_booking":
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
                        message_type=MessageType.CLARIFICATION,
                        command="book_hotel",
                        slots=[],
                        confidence=0.9,
                    ),
                    domain=domain_config.name,
                    pattern="clarification",
                    context_type="ongoing",
                    current_datetime="2024-12-11T10:00:00",
                )
            )

        elif domain_config.name == "restaurant":
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
                        message_type=MessageType.CLARIFICATION,
                        command="book_table",
                        slots=[],
                        confidence=0.9,
                    ),
                    domain=domain_config.name,
                    pattern="clarification",
                    context_type="ongoing",
                    current_datetime="2024-12-11T10:00:00",
                )
            )

        elif domain_config.name == "ecommerce":
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
                        message_type=MessageType.CLARIFICATION,
                        command="search_product",
                        slots=[],
                        confidence=0.9,
                    ),
                    domain=domain_config.name,
                    pattern="clarification",
                    context_type="ongoing",
                    current_datetime="2024-12-11T10:00:00",
                )
            )

        return examples[:count]
