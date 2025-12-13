"""CONFIRMATION pattern generator.

Yes/no answers to confirmation prompts.

Examples:
    Positive: "Yes", "Correct", "That's right"
    Negative: "No", "That's wrong", "Incorrect"
"""

from typing import Literal

from soni.dataset.base import (
    DomainConfig,
    ExampleTemplate,
    PatternGenerator,
)
from soni.du.models import MessageType, NLUOutput


class ConfirmationGenerator(PatternGenerator):
    """Generates CONFIRMATION pattern examples."""

    @property
    def message_type(self) -> MessageType:
        return MessageType.CONFIRMATION

    def generate_examples(
        self,
        domain_config: DomainConfig,
        context_type: Literal["cold_start", "ongoing"],
        count: int = 3,
    ) -> list[ExampleTemplate]:
        """Generate CONFIRMATION examples (ongoing only)."""
        if context_type == "cold_start":
            return []  # Confirmations only happen in ongoing conversations

        return self._generate_ongoing_examples(domain_config, count)

    def _generate_ongoing_examples(
        self,
        domain_config: DomainConfig,
        count: int,
    ) -> list[ExampleTemplate]:
        """Generate confirmation examples."""
        examples = []

        if domain_config.name == "flight_booking":
            from soni.dataset.domains.flight_booking import (
                CONFIRMATION_NEGATIVE,
                CONFIRMATION_POSITIVE,
                CONFIRMATION_UNCLEAR,
                create_context_before_confirmation,
            )

            # Positive confirmation
            examples.append(
                ExampleTemplate(
                    user_message=CONFIRMATION_POSITIVE[0],
                    conversation_context=create_context_before_confirmation(),
                    expected_output=NLUOutput(
                        message_type=MessageType.CONFIRMATION,
                        command="book_flight",
                        slots=[],
                        confidence=0.95,
                        confirmation_value=True,
                    ),
                    domain=domain_config.name,
                    pattern="confirmation",
                    context_type="ongoing",
                    current_datetime="2024-12-11T10:00:00",
                )
            )

            # Negative confirmation
            examples.append(
                ExampleTemplate(
                    user_message=CONFIRMATION_NEGATIVE[0],
                    conversation_context=create_context_before_confirmation(),
                    expected_output=NLUOutput(
                        message_type=MessageType.CONFIRMATION,
                        command="book_flight",
                        slots=[],
                        confidence=0.95,
                        confirmation_value=False,
                    ),
                    domain=domain_config.name,
                    pattern="confirmation",
                    context_type="ongoing",
                    current_datetime="2024-12-11T10:00:00",
                )
            )

            # Unclear confirmations - with confirmation_value=None
            for unclear_phrase in CONFIRMATION_UNCLEAR[:5]:  # First 5 to avoid exceeding count
                examples.append(
                    ExampleTemplate(
                        user_message=unclear_phrase,
                        conversation_context=create_context_before_confirmation(),
                        expected_output=NLUOutput(
                            message_type=MessageType.CONFIRMATION,
                            command="book_flight",
                            slots=[],
                            confidence=0.7,  # Lower confidence for ambiguous responses
                            confirmation_value=None,  # CRITICAL: None indicates ambiguity
                        ),
                        domain=domain_config.name,
                        pattern="confirmation",
                        context_type="ongoing",
                        current_datetime="2024-12-11T10:00:00",
                    )
                )

        elif domain_config.name == "hotel_booking":
            from soni.dataset.domains.hotel_booking import (
                CONFIRMATION_NEGATIVE,
                CONFIRMATION_POSITIVE,
                CONFIRMATION_UNCLEAR,
                create_context_after_location,
            )

            context = create_context_after_location()
            context.current_slots = {"location": "Barcelona", "checkin_date": "2024-12-20"}
            context.expected_slots = []

            # Positive confirmation
            examples.append(
                ExampleTemplate(
                    user_message=CONFIRMATION_POSITIVE[0],
                    conversation_context=context,
                    expected_output=NLUOutput(
                        message_type=MessageType.CONFIRMATION,
                        command="book_hotel",
                        slots=[],
                        confidence=0.95,
                        confirmation_value=True,
                    ),
                    domain=domain_config.name,
                    pattern="confirmation",
                    context_type="ongoing",
                    current_datetime="2024-12-11T10:00:00",
                )
            )

            # Negative confirmation
            examples.append(
                ExampleTemplate(
                    user_message=CONFIRMATION_NEGATIVE[0],
                    conversation_context=context,
                    expected_output=NLUOutput(
                        message_type=MessageType.CONFIRMATION,
                        command="book_hotel",
                        slots=[],
                        confidence=0.95,
                        confirmation_value=False,
                    ),
                    domain=domain_config.name,
                    pattern="confirmation",
                    context_type="ongoing",
                    current_datetime="2024-12-11T10:00:00",
                )
            )

            # Unclear confirmations
            for unclear_phrase in CONFIRMATION_UNCLEAR[:3]:
                examples.append(
                    ExampleTemplate(
                        user_message=unclear_phrase,
                        conversation_context=context,
                        expected_output=NLUOutput(
                            message_type=MessageType.CONFIRMATION,
                            command="book_hotel",
                            slots=[],
                            confidence=0.7,
                            confirmation_value=None,
                        ),
                        domain=domain_config.name,
                        pattern="confirmation",
                        context_type="ongoing",
                        current_datetime="2024-12-11T10:00:00",
                    )
                )

        elif domain_config.name == "restaurant":
            from soni.dataset.domains.restaurant import (
                CONFIRMATION_NEGATIVE,
                CONFIRMATION_POSITIVE,
                CONFIRMATION_UNCLEAR,
                create_context_after_location,
            )

            context = create_context_after_location()
            context.current_slots = {"location": "Madrid", "party_size": "4", "time": "8:00 PM"}
            context.expected_slots = []

            # Positive confirmation
            examples.append(
                ExampleTemplate(
                    user_message=CONFIRMATION_POSITIVE[0],
                    conversation_context=context,
                    expected_output=NLUOutput(
                        message_type=MessageType.CONFIRMATION,
                        command="book_table",
                        slots=[],
                        confidence=0.95,
                        confirmation_value=True,
                    ),
                    domain=domain_config.name,
                    pattern="confirmation",
                    context_type="ongoing",
                    current_datetime="2024-12-11T10:00:00",
                )
            )

            # Negative confirmation
            examples.append(
                ExampleTemplate(
                    user_message=CONFIRMATION_NEGATIVE[0],
                    conversation_context=context,
                    expected_output=NLUOutput(
                        message_type=MessageType.CONFIRMATION,
                        command="book_table",
                        slots=[],
                        confidence=0.95,
                        confirmation_value=False,
                    ),
                    domain=domain_config.name,
                    pattern="confirmation",
                    context_type="ongoing",
                    current_datetime="2024-12-11T10:00:00",
                )
            )

            # Unclear confirmations
            for unclear_phrase in CONFIRMATION_UNCLEAR[:3]:
                examples.append(
                    ExampleTemplate(
                        user_message=unclear_phrase,
                        conversation_context=context,
                        expected_output=NLUOutput(
                            message_type=MessageType.CONFIRMATION,
                            command="book_table",
                            slots=[],
                            confidence=0.7,
                            confirmation_value=None,
                        ),
                        domain=domain_config.name,
                        pattern="confirmation",
                        context_type="ongoing",
                        current_datetime="2024-12-11T10:00:00",
                    )
                )

        elif domain_config.name == "ecommerce":
            from soni.dataset.domains.ecommerce import (
                CONFIRMATION_NEGATIVE,
                CONFIRMATION_POSITIVE,
                CONFIRMATION_UNCLEAR,
                create_context_after_product,
            )

            context = create_context_after_product()
            context.current_slots = {"product": "laptop", "quantity": "1"}
            context.expected_slots = []

            # Positive confirmation
            examples.append(
                ExampleTemplate(
                    user_message=CONFIRMATION_POSITIVE[0],
                    conversation_context=context,
                    expected_output=NLUOutput(
                        message_type=MessageType.CONFIRMATION,
                        command="search_product",
                        slots=[],
                        confidence=0.95,
                        confirmation_value=True,
                    ),
                    domain=domain_config.name,
                    pattern="confirmation",
                    context_type="ongoing",
                    current_datetime="2024-12-11T10:00:00",
                )
            )

            # Negative confirmation
            examples.append(
                ExampleTemplate(
                    user_message=CONFIRMATION_NEGATIVE[0],
                    conversation_context=context,
                    expected_output=NLUOutput(
                        message_type=MessageType.CONFIRMATION,
                        command="search_product",
                        slots=[],
                        confidence=0.95,
                        confirmation_value=False,
                    ),
                    domain=domain_config.name,
                    pattern="confirmation",
                    context_type="ongoing",
                    current_datetime="2024-12-11T10:00:00",
                )
            )

            # Unclear confirmations
            for unclear_phrase in CONFIRMATION_UNCLEAR[:3]:
                examples.append(
                    ExampleTemplate(
                        user_message=unclear_phrase,
                        conversation_context=context,
                        expected_output=NLUOutput(
                            message_type=MessageType.CONFIRMATION,
                            command="search_product",
                            slots=[],
                            confidence=0.7,
                            confirmation_value=None,
                        ),
                        domain=domain_config.name,
                        pattern="confirmation",
                        context_type="ongoing",
                        current_datetime="2024-12-11T10:00:00",
                    )
                )

        return examples[:count]
