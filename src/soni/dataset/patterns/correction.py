"""CORRECTION pattern generator.

Reactive corrections - user realizes they made a mistake.

Examples:
    - Bot: "Flying to Madrid, correct?"
    - User: "No, I meant Barcelona"
"""

from typing import Literal

import dspy

from soni.dataset.base import (
    ConversationContext,
    DomainConfig,
    ExampleTemplate,
    PatternGenerator,
)
from soni.du.models import MessageType, NLUOutput, SlotValue


class CorrectionGenerator(PatternGenerator):
    """Generates CORRECTION pattern examples."""

    @property
    def message_type(self) -> MessageType:
        return MessageType.CORRECTION

    def generate_examples(
        self,
        domain_config: DomainConfig,
        context_type: Literal["cold_start", "ongoing"],
        count: int = 3,
    ) -> list[ExampleTemplate]:
        """Generate CORRECTION examples (ongoing only)."""
        if context_type == "cold_start":
            return []  # Corrections only happen in ongoing conversations

        return self._generate_ongoing_examples(domain_config, count)

    def _generate_ongoing_examples(
        self,
        domain_config: DomainConfig,
        count: int,
    ) -> list[ExampleTemplate]:
        """Generate correction examples."""
        examples = []

        if domain_config.name == "flight_booking":
            from soni.dataset.domains.flight_booking import (
                CITIES,
                create_context_before_confirmation,
            )

            # Example 1: Correcting destination
            examples.append(
                ExampleTemplate(
                    user_message=f"No, I said {CITIES[5]} not {CITIES[1]}",
                    conversation_context=create_context_before_confirmation(
                        origin=CITIES[0],
                        destination=CITIES[1],  # Wrong value
                        departure_date="tomorrow",
                    ),
                    expected_output=NLUOutput(
                        message_type=MessageType.CORRECTION,
                        command="book_flight",
                        slots=[
                            SlotValue(name="destination", value=CITIES[5], confidence=0.9),
                        ],
                        confidence=0.9,
                    ),
                    domain=domain_config.name,
                    pattern="correction",
                    context_type="ongoing",
                    current_datetime="2024-12-11T10:00:00",
                )
            )

            # Example 2: Correcting date with "actually"
            examples.append(
                ExampleTemplate(
                    user_message="Actually, I want to leave next Monday",
                    conversation_context=create_context_before_confirmation(
                        origin=CITIES[0],
                        destination=CITIES[1],
                        departure_date="tomorrow",  # Wrong value
                    ),
                    expected_output=NLUOutput(
                        message_type=MessageType.CORRECTION,
                        command="book_flight",
                        slots=[
                            SlotValue(name="departure_date", value="next Monday", confidence=0.9),
                        ],
                        confidence=0.9,
                    ),
                    domain=domain_config.name,
                    pattern="correction",
                    context_type="ongoing",
                    current_datetime="2024-12-11T10:00:00",
                )
            )

        elif domain_config.name == "hotel_booking":
            from soni.dataset.domains.hotel_booking import CITIES

            examples.append(
                ExampleTemplate(
                    user_message=f"No wait, {CITIES[2]}, not {CITIES[0]}",
                    conversation_context=ConversationContext(
                        history=dspy.History(
                            messages=[
                                {"user_message": f"Book hotel in {CITIES[0]}"},
                            ]
                        ),
                        current_slots={"location": CITIES[0]},
                        current_flow="book_hotel",
                        expected_slots=["checkin_date"],
                    ),
                    expected_output=NLUOutput(
                        message_type=MessageType.CORRECTION,
                        command="book_hotel",
                        slots=[
                            SlotValue(name="location", value=CITIES[2], confidence=0.9),
                        ],
                        confidence=0.9,
                    ),
                    domain=domain_config.name,
                    pattern="correction",
                    context_type="ongoing",
                    current_datetime="2024-12-11T10:00:00",
                )
            )

        elif domain_config.name == "restaurant":
            from soni.dataset.domains.restaurant import CITIES, TIMES

            examples.append(
                ExampleTemplate(
                    user_message=f"Actually, {TIMES[1]} instead",
                    conversation_context=ConversationContext(
                        history=dspy.History(
                            messages=[
                                {"user_message": f"Book table at {TIMES[0]}"},
                            ]
                        ),
                        current_slots={"time": TIMES[0]},
                        current_flow="book_table",
                        expected_slots=[],
                    ),
                    expected_output=NLUOutput(
                        message_type=MessageType.CORRECTION,
                        command="book_table",
                        slots=[
                            SlotValue(name="time", value=TIMES[1], confidence=0.9),
                        ],
                        confidence=0.9,
                    ),
                    domain=domain_config.name,
                    pattern="correction",
                    context_type="ongoing",
                    current_datetime="2024-12-11T10:00:00",
                )
            )

        elif domain_config.name == "ecommerce":
            examples.append(
                ExampleTemplate(
                    user_message="No, I want black not blue",
                    conversation_context=ConversationContext(
                        history=dspy.History(
                            messages=[
                                {"user_message": "I want blue"},
                            ]
                        ),
                        current_slots={"color": "blue"},
                        current_flow="search_product",
                        expected_slots=[],
                    ),
                    expected_output=NLUOutput(
                        message_type=MessageType.CORRECTION,
                        command="search_product",
                        slots=[
                            SlotValue(name="color", value="black", confidence=0.9),
                        ],
                        confidence=0.9,
                    ),
                    domain=domain_config.name,
                    pattern="correction",
                    context_type="ongoing",
                    current_datetime="2024-12-11T10:00:00",
                )
            )

        return examples[:count]
