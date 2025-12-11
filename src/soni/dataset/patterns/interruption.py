"""INTERRUPTION pattern generator.

User starts new task mid-conversation or at conversation start.

Examples:
    Cold start: "I want to book a flight"
    Ongoing: "Actually, check hotel prices first"
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


class InterruptionGenerator(PatternGenerator):
    """Generates INTERRUPTION pattern examples."""

    @property
    def message_type(self) -> MessageType:
        return MessageType.INTERRUPTION

    def generate_examples(
        self,
        domain_config: DomainConfig,
        context_type: Literal["cold_start", "ongoing"],
        count: int = 3,
    ) -> list[ExampleTemplate]:
        """Generate INTERRUPTION examples (both contexts)."""
        if context_type == "cold_start":
            return self._generate_cold_start_examples(domain_config, count)
        else:
            return self._generate_ongoing_examples(domain_config, count)

    def _generate_cold_start_examples(
        self,
        domain_config: DomainConfig,
        count: int,
    ) -> list[ExampleTemplate]:
        """Generate cold start interruption examples."""
        examples = []

        if domain_config.name == "flight_booking":
            from soni.dataset.domains.flight_booking import BOOKING_UTTERANCES

            examples.append(
                ExampleTemplate(
                    user_message=BOOKING_UTTERANCES[0],
                    conversation_context=ConversationContext(
                        history=dspy.History(messages=[]),
                        current_slots={},
                        current_flow="none",
                        expected_slots=[],
                    ),
                    expected_output=NLUOutput(
                        message_type=MessageType.INTERRUPTION,
                        command="book_flight",
                        slots=[],
                        confidence=0.9,
                    ),
                    domain=domain_config.name,
                    pattern="interruption",
                    context_type="cold_start",
                    current_datetime="2024-12-11T10:00:00",
                )
            )

        elif domain_config.name == "hotel_booking":
            from soni.dataset.domains.hotel_booking import BOOKING_UTTERANCES

            examples.append(
                ExampleTemplate(
                    user_message=BOOKING_UTTERANCES[0],
                    conversation_context=ConversationContext(
                        history=dspy.History(messages=[]),
                        current_slots={},
                        current_flow="none",
                        expected_slots=[],
                    ),
                    expected_output=NLUOutput(
                        message_type=MessageType.INTERRUPTION,
                        command="book_hotel",
                        slots=[],
                        confidence=0.9,
                    ),
                    domain=domain_config.name,
                    pattern="interruption",
                    context_type="cold_start",
                    current_datetime="2024-12-11T10:00:00",
                )
            )

        elif domain_config.name == "restaurant":
            from soni.dataset.domains.restaurant import BOOKING_UTTERANCES

            examples.append(
                ExampleTemplate(
                    user_message=BOOKING_UTTERANCES[0],
                    conversation_context=ConversationContext(
                        history=dspy.History(messages=[]),
                        current_slots={},
                        current_flow="none",
                        expected_slots=[],
                    ),
                    expected_output=NLUOutput(
                        message_type=MessageType.INTERRUPTION,
                        command="book_table",
                        slots=[],
                        confidence=0.9,
                    ),
                    domain=domain_config.name,
                    pattern="interruption",
                    context_type="cold_start",
                    current_datetime="2024-12-11T10:00:00",
                )
            )

        elif domain_config.name == "ecommerce":
            from soni.dataset.domains.ecommerce import PRODUCTS, SEARCH_UTTERANCES

            examples.append(
                ExampleTemplate(
                    user_message=f"{SEARCH_UTTERANCES[0]} {PRODUCTS[0]}",
                    conversation_context=ConversationContext(
                        history=dspy.History(messages=[]),
                        current_slots={},
                        current_flow="none",
                        expected_slots=[],
                    ),
                    expected_output=NLUOutput(
                        message_type=MessageType.INTERRUPTION,
                        command="search_product",
                        slots=[],
                        confidence=0.9,
                    ),
                    domain=domain_config.name,
                    pattern="interruption",
                    context_type="cold_start",
                    current_datetime="2024-12-11T10:00:00",
                )
            )

        return examples[:count]

    def _generate_ongoing_examples(
        self,
        domain_config: DomainConfig,
        count: int,
    ) -> list[ExampleTemplate]:
        """Generate ongoing interruption examples (switching tasks)."""
        examples = []

        if domain_config.name == "flight_booking":
            examples.append(
                ExampleTemplate(
                    user_message="Actually, check hotel prices first",
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
                        message_type=MessageType.INTERRUPTION,
                        command="search_hotels",
                        slots=[],
                        confidence=0.85,
                    ),
                    domain=domain_config.name,
                    pattern="interruption",
                    context_type="ongoing",
                    current_datetime="2024-12-11T10:00:00",
                )
            )

        elif domain_config.name == "hotel_booking":
            examples.append(
                ExampleTemplate(
                    user_message="Wait, let me search for flights instead",
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
                        message_type=MessageType.INTERRUPTION,
                        command="search_flights",
                        slots=[],
                        confidence=0.85,
                    ),
                    domain=domain_config.name,
                    pattern="interruption",
                    context_type="ongoing",
                    current_datetime="2024-12-11T10:00:00",
                )
            )

        elif domain_config.name == "restaurant":
            examples.append(
                ExampleTemplate(
                    user_message="Actually, I need to book a flight first",
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
                        message_type=MessageType.INTERRUPTION,
                        command="book_flight",
                        slots=[],
                        confidence=0.85,
                    ),
                    domain=domain_config.name,
                    pattern="interruption",
                    context_type="ongoing",
                    current_datetime="2024-12-11T10:00:00",
                )
            )

        elif domain_config.name == "ecommerce":
            examples.append(
                ExampleTemplate(
                    user_message="Actually, let me check flights first",
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
                        message_type=MessageType.INTERRUPTION,
                        command="search_flights",
                        slots=[],
                        confidence=0.85,
                    ),
                    domain=domain_config.name,
                    pattern="interruption",
                    context_type="ongoing",
                    current_datetime="2024-12-11T10:00:00",
                )
            )

        return examples[:count]
