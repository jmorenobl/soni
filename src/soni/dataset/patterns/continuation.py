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
            # Example 1
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
            # Example 2
            examples.append(
                ExampleTemplate(
                    user_message="Move on",
                    conversation_context=ConversationContext(
                        history=dspy.History(
                            messages=[
                                {"user_message": "Reserve suite"},
                            ]
                        ),
                        current_slots={"room_type": "suite"},
                        current_flow="book_hotel",
                        expected_slots=["dates"],
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
            # Example 3
            examples.append(
                ExampleTemplate(
                    user_message="Yes, please proceed",
                    conversation_context=ConversationContext(
                        history=dspy.History(
                            messages=[
                                {"user_message": "Hotel booking"},
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
                        confidence=0.95,
                    ),
                    domain=domain_config.name,
                    pattern="continuation",
                    context_type="ongoing",
                    current_datetime="2024-12-11T10:00:00",
                )
            )

        elif domain_config.name == "restaurant":
            # Example 1
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
            # Example 2
            examples.append(
                ExampleTemplate(
                    user_message="Go to next step",
                    conversation_context=ConversationContext(
                        history=dspy.History(
                            messages=[
                                {"user_message": "Table reservation"},
                            ]
                        ),
                        current_slots={},
                        current_flow="book_table",
                        expected_slots=["time"],
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
            # Example 3
            examples.append(
                ExampleTemplate(
                    user_message="Sure, continue",
                    conversation_context=ConversationContext(
                        history=dspy.History(
                            messages=[
                                {"user_message": "Dinner booking"},
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
                        confidence=0.95,
                    ),
                    domain=domain_config.name,
                    pattern="continuation",
                    context_type="ongoing",
                    current_datetime="2024-12-11T10:00:00",
                )
            )

        elif domain_config.name == "ecommerce":
            # Example 1
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
            # Example 2
            examples.append(
                ExampleTemplate(
                    user_message="Carry on",
                    conversation_context=ConversationContext(
                        history=dspy.History(
                            messages=[
                                {"user_message": "Buy headphones"},
                            ]
                        ),
                        current_slots={"product": "headphones"},
                        current_flow="search_product",
                        expected_slots=["brand"],
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
            # Example 3
            examples.append(
                ExampleTemplate(
                    user_message="Next please",
                    conversation_context=ConversationContext(
                        history=dspy.History(
                            messages=[
                                {"user_message": "Shop for shoes"},
                            ]
                        ),
                        current_slots={"product": "shoes"},
                        current_flow="search_product",
                        expected_slots=["size"],
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

        elif domain_config.name == "banking":
            from soni.dataset.domains.banking import (
                CONTINUATION_UTTERANCES,
                create_context_after_transfer,
            )

            # Example 1: Continue after transfer
            examples.append(
                ExampleTemplate(
                    user_message=CONTINUATION_UTTERANCES[1],  # "Transfer more"
                    conversation_context=create_context_after_transfer(
                        amount="100", currency="USD", recipient="mom"
                    ),
                    expected_output=NLUOutput(
                        message_type=MessageType.CONTINUATION,
                        command="transfer_funds",
                        slots=[],
                        confidence=0.9,
                    ),
                    domain=domain_config.name,
                    pattern="continuation",
                    context_type="ongoing",
                    current_datetime="2024-12-11T10:00:00",
                )
            )
            # Example 2: Go ahead
            examples.append(
                ExampleTemplate(
                    user_message=CONTINUATION_UTTERANCES[0],  # "Yes, go ahead"
                    conversation_context=create_context_after_transfer(
                        amount="50", currency="EUR", recipient="Alice"
                    ),
                    expected_output=NLUOutput(
                        message_type=MessageType.CONTINUATION,
                        command="transfer_funds",
                        slots=[],
                        confidence=0.95,
                    ),
                    domain=domain_config.name,
                    pattern="continuation",
                    context_type="ongoing",
                    current_datetime="2024-12-11T10:00:00",
                )
            )
            # Example 3: Proceed
            examples.append(
                ExampleTemplate(
                    user_message=CONTINUATION_UTTERANCES[2],  # "Please proceed"
                    conversation_context=create_context_after_transfer(
                        amount="1000", currency="USD", recipient="Bob"
                    ),
                    expected_output=NLUOutput(
                        message_type=MessageType.CONTINUATION,
                        command="transfer_funds",
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
