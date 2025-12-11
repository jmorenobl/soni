"""DIGRESSION pattern generator.

Off-topic question without flow change.

Examples:
    - "What airlines fly that route?"
    - "Do you have direct flights?"
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


class DigressionGenerator(PatternGenerator):
    """Generates DIGRESSION pattern examples."""

    @property
    def message_type(self) -> MessageType:
        return MessageType.DIGRESSION

    def generate_examples(
        self,
        domain_config: DomainConfig,
        context_type: Literal["cold_start", "ongoing"],
        count: int = 3,
    ) -> list[ExampleTemplate]:
        """Generate DIGRESSION examples (ongoing only)."""
        if context_type == "cold_start":
            return []  # Digressions only happen in ongoing conversations

        return self._generate_ongoing_examples(domain_config, count)

    def _generate_ongoing_examples(
        self,
        domain_config: DomainConfig,
        count: int,
    ) -> list[ExampleTemplate]:
        """Generate digression examples."""
        examples = []

        if domain_config.name == "flight_booking":
            digression_questions = [
                "What airlines fly that route?",
                "Do you have direct flights?",
                "How long is the flight?",
            ]

            examples.append(
                ExampleTemplate(
                    user_message=digression_questions[0],
                    conversation_context=ConversationContext(
                        history=dspy.History(
                            messages=[
                                {
                                    "user_message": "I want to book a flight from Madrid to Barcelona"
                                },
                            ]
                        ),
                        current_slots={"origin": "Madrid", "destination": "Barcelona"},
                        current_flow="book_flight",
                        expected_slots=["departure_date"],
                    ),
                    expected_output=NLUOutput(
                        message_type=MessageType.DIGRESSION,
                        command="book_flight",
                        slots=[],
                        confidence=0.85,
                    ),
                    domain=domain_config.name,
                    pattern="digression",
                    context_type="ongoing",
                    current_datetime="2024-12-11T10:00:00",
                )
            )

        elif domain_config.name == "hotel_booking":
            examples.append(
                ExampleTemplate(
                    user_message="Do you have WiFi?",
                    conversation_context=ConversationContext(
                        history=dspy.History(
                            messages=[
                                {"user_message": "Book a hotel in Barcelona"},
                            ]
                        ),
                        current_slots={"location": "Barcelona"},
                        current_flow="book_hotel",
                        expected_slots=["checkin_date"],
                    ),
                    expected_output=NLUOutput(
                        message_type=MessageType.DIGRESSION,
                        command="book_hotel",
                        slots=[],
                        confidence=0.85,
                    ),
                    domain=domain_config.name,
                    pattern="digression",
                    context_type="ongoing",
                    current_datetime="2024-12-11T10:00:00",
                )
            )

        elif domain_config.name == "restaurant":
            examples.append(
                ExampleTemplate(
                    user_message="Do you have vegetarian options?",
                    conversation_context=ConversationContext(
                        history=dspy.History(
                            messages=[
                                {"user_message": "Book a table in Madrid"},
                            ]
                        ),
                        current_slots={"location": "Madrid"},
                        current_flow="book_table",
                        expected_slots=["date"],
                    ),
                    expected_output=NLUOutput(
                        message_type=MessageType.DIGRESSION,
                        command="book_table",
                        slots=[],
                        confidence=0.85,
                    ),
                    domain=domain_config.name,
                    pattern="digression",
                    context_type="ongoing",
                    current_datetime="2024-12-11T10:00:00",
                )
            )

        elif domain_config.name == "ecommerce":
            examples.append(
                ExampleTemplate(
                    user_message="What's the warranty?",
                    conversation_context=ConversationContext(
                        history=dspy.History(
                            messages=[
                                {"user_message": "I want to buy a laptop"},
                            ]
                        ),
                        current_slots={"product": "laptop"},
                        current_flow="search_product",
                        expected_slots=["quantity"],
                    ),
                    expected_output=NLUOutput(
                        message_type=MessageType.DIGRESSION,
                        command="search_product",
                        slots=[],
                        confidence=0.85,
                    ),
                    domain=domain_config.name,
                    pattern="digression",
                    context_type="ongoing",
                    current_datetime="2024-12-11T10:00:00",
                )
            )

        return examples[:count]
