"""CONTINUATION pattern generator.

General continuation signals.

Examples:
    - "Continue"
    - "Go ahead"
    - "Next"
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


class ContinuationGenerator(PatternGenerator):
    """Generates CONTINUATION pattern examples."""

    @property
    def message_type(self) -> MessageType:
        return MessageType.CONTINUATION

    def generate_examples(
        self,
        domain_config: DomainConfig,
        context_type: Literal["cold_start", "ongoing"],
        count: int = 3,
    ) -> list[ExampleTemplate]:
        """Generate CONTINUATION examples (ongoing only)."""
        if context_type == "cold_start":
            return []  # Continuations only happen in ongoing conversations

        return self._generate_ongoing_examples(domain_config, count)

    def _generate_ongoing_examples(
        self,
        domain_config: DomainConfig,
        count: int,
    ) -> list[ExampleTemplate]:
        """Generate continuation examples."""
        examples = []

        continuation_phrases = ["Continue", "Go ahead", "Next", "Yes, continue", "Proceed"]

        if domain_config.name == "flight_booking":
            examples.append(
                ExampleTemplate(
                    user_message=continuation_phrases[0],
                    conversation_context=ConversationContext(
                        history=dspy.History(
                            messages=[
                                {"user_message": "I want to book a flight"},
                            ]
                        ),
                        current_slots={},
                        current_flow="book_flight",
                        expected_slots=["origin"],
                    ),
                    expected_output=NLUOutput(
                        message_type=MessageType.CONTINUATION,
                        command="book_flight",
                        slots=[],
                        confidence=0.9,
                    ),
                    domain=domain_config.name,
                    pattern="continuation",
                    context_type="ongoing",
                    current_datetime="2024-12-11T10:00:00",
                )
            )

            examples.append(
                ExampleTemplate(
                    user_message=continuation_phrases[1],
                    conversation_context=ConversationContext(
                        history=dspy.History(
                            messages=[
                                {"user_message": "Book a flight from Madrid"},
                            ]
                        ),
                        current_slots={"origin": "Madrid"},
                        current_flow="book_flight",
                        expected_slots=["destination"],
                    ),
                    expected_output=NLUOutput(
                        message_type=MessageType.CONTINUATION,
                        command="book_flight",
                        slots=[],
                        confidence=0.9,
                    ),
                    domain=domain_config.name,
                    pattern="continuation",
                    context_type="ongoing",
                    current_datetime="2024-12-11T10:00:00",
                )
            )

        elif domain_config.name == "hotel_booking":
            examples.append(
                ExampleTemplate(
                    user_message=continuation_phrases[2],
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
                        message_type=MessageType.CONTINUATION,
                        command="book_hotel",
                        slots=[],
                        confidence=0.9,
                    ),
                    domain=domain_config.name,
                    pattern="continuation",
                    context_type="ongoing",
                    current_datetime="2024-12-11T10:00:00",
                )
            )

        elif domain_config.name == "restaurant":
            examples.append(
                ExampleTemplate(
                    user_message=continuation_phrases[3],
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
                        message_type=MessageType.CONTINUATION,
                        command="book_table",
                        slots=[],
                        confidence=0.9,
                    ),
                    domain=domain_config.name,
                    pattern="continuation",
                    context_type="ongoing",
                    current_datetime="2024-12-11T10:00:00",
                )
            )

        elif domain_config.name == "ecommerce":
            examples.append(
                ExampleTemplate(
                    user_message=continuation_phrases[4],
                    conversation_context=ConversationContext(
                        history=dspy.History(
                            messages=[
                                {"user_message": "I want to buy a laptop"},
                            ]
                        ),
                        current_slots={},
                        current_flow="search_product",
                        expected_slots=["product"],
                    ),
                    expected_output=NLUOutput(
                        message_type=MessageType.CONTINUATION,
                        command="search_product",
                        slots=[],
                        confidence=0.9,
                    ),
                    domain=domain_config.name,
                    pattern="continuation",
                    context_type="ongoing",
                    current_datetime="2024-12-11T10:00:00",
                )
            )

        return examples[:count]
