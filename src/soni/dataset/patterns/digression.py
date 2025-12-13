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

            # Example 1
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
            # Example 2
            examples.append(
                ExampleTemplate(
                    user_message=digression_questions[1],  # "Do you have direct flights?"
                    conversation_context=ConversationContext(
                        history=dspy.History(
                            messages=[
                                {"user_message": "Flights to Paris"},
                            ]
                        ),
                        current_slots={"destination": "Paris"},
                        current_flow="book_flight",
                        expected_slots=["origin"],
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
            # Example 3
            examples.append(
                ExampleTemplate(
                    user_message="Can I bring my pet?",
                    conversation_context=ConversationContext(
                        history=dspy.History(
                            messages=[
                                {"user_message": "Book a flight"},
                            ]
                        ),
                        current_slots={},
                        current_flow="book_flight",
                        expected_slots=["origin"],
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

            # Example 4: "What airports do you support?" - key test case pattern
            examples.append(
                ExampleTemplate(
                    user_message="What airports do you support?",
                    conversation_context=ConversationContext(
                        history=dspy.History(
                            messages=[
                                {"user_message": "I want to book a flight"},
                                {"user_message": "San Francisco"},
                            ]
                        ),
                        current_slots={"origin": "San Francisco"},
                        current_flow="book_flight",
                        expected_slots=["destination"],
                    ),
                    expected_output=NLUOutput(
                        message_type=MessageType.DIGRESSION,
                        command="book_flight",
                        slots=[],
                        confidence=0.9,
                    ),
                    domain=domain_config.name,
                    pattern="digression",
                    context_type="ongoing",
                    current_datetime="2024-12-11T10:00:00",
                )
            )

            # Example 5: "What destinations do you fly to?"
            examples.append(
                ExampleTemplate(
                    user_message="What destinations do you fly to?",
                    conversation_context=ConversationContext(
                        history=dspy.History(
                            messages=[
                                {"user_message": "Book a flight from Boston"},
                            ]
                        ),
                        current_slots={"origin": "Boston"},
                        current_flow="book_flight",
                        expected_slots=["destination"],
                    ),
                    expected_output=NLUOutput(
                        message_type=MessageType.DIGRESSION,
                        command="book_flight",
                        slots=[],
                        confidence=0.9,
                    ),
                    domain=domain_config.name,
                    pattern="digression",
                    context_type="ongoing",
                    current_datetime="2024-12-11T10:00:00",
                )
            )

            # Example 6: "What cities can I fly to?"
            examples.append(
                ExampleTemplate(
                    user_message="What cities can I fly to?",
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
                        message_type=MessageType.DIGRESSION,
                        command="book_flight",
                        slots=[],
                        confidence=0.9,
                    ),
                    domain=domain_config.name,
                    pattern="digression",
                    context_type="ongoing",
                    current_datetime="2024-12-11T10:00:00",
                )
            )

        elif domain_config.name == "hotel_booking":
            # Example 1
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
            # Example 2
            examples.append(
                ExampleTemplate(
                    user_message="Is breakfast included?",
                    conversation_context=ConversationContext(
                        history=dspy.History(
                            messages=[
                                {"user_message": "Reserve a room"},
                            ]
                        ),
                        current_slots={},
                        current_flow="book_hotel",
                        expected_slots=["location"],
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
            # Example 3
            examples.append(
                ExampleTemplate(
                    user_message="Is there a gym?",
                    conversation_context=ConversationContext(
                        history=dspy.History(
                            messages=[
                                {"user_message": "Hotel in Tokyo"},
                            ]
                        ),
                        current_slots={"location": "Tokyo"},
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
            # Example 1
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
            # Example 2
            examples.append(
                ExampleTemplate(
                    user_message="Do you have parking?",
                    conversation_context=ConversationContext(
                        history=dspy.History(
                            messages=[
                                {"user_message": "Reserve dinner"},
                            ]
                        ),
                        current_slots={},
                        current_flow="book_table",
                        expected_slots=["time"],
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
            # Example 3
            examples.append(
                ExampleTemplate(
                    user_message="Do you have outdoor seating?",
                    conversation_context=ConversationContext(
                        history=dspy.History(
                            messages=[
                                {"user_message": "Table for 4"},
                            ]
                        ),
                        current_slots={"party_size": "4"},
                        current_flow="book_table",
                        expected_slots=["location"],
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
            # Example 1
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
            # Example 2
            examples.append(
                ExampleTemplate(
                    user_message="What is the return policy?",
                    conversation_context=ConversationContext(
                        history=dspy.History(
                            messages=[
                                {"user_message": "Buy shoes"},
                            ]
                        ),
                        current_slots={"product": "shoes"},
                        current_flow="search_product",
                        expected_slots=["size"],
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
            # Example 3
            examples.append(
                ExampleTemplate(
                    user_message="Do you ship internationally?",
                    conversation_context=ConversationContext(
                        history=dspy.History(
                            messages=[
                                {"user_message": "Search for cameras"},
                            ]
                        ),
                        current_slots={"product": "camera"},
                        current_flow="search_product",
                        expected_slots=["brand"],
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

        elif domain_config.name == "banking":
            from soni.dataset.domains.banking import (
                DIGRESSION_UTTERANCES,
                create_context_after_transfer,
            )

            # Example 1: Ask about fees during transfer
            examples.append(
                ExampleTemplate(
                    user_message=DIGRESSION_UTTERANCES[0],  # "What are your fees?"
                    conversation_context=create_context_after_transfer(
                        amount="100", currency="USD", recipient="mom"
                    ),
                    expected_output=NLUOutput(
                        message_type=MessageType.DIGRESSION,
                        command="transfer_funds",
                        slots=[],
                        confidence=0.85,
                    ),
                    domain=domain_config.name,
                    pattern="digression",
                    context_type="ongoing",
                    current_datetime="2024-12-11T10:00:00",
                )
            )
            # Example 2: Safety
            examples.append(
                ExampleTemplate(
                    user_message=DIGRESSION_UTTERANCES[1],  # "Is it safe?"
                    conversation_context=create_context_after_transfer(
                        amount="1000", currency="EUR", recipient="Bob"
                    ),
                    expected_output=NLUOutput(
                        message_type=MessageType.DIGRESSION,
                        command="transfer_funds",
                        slots=[],
                        confidence=0.85,
                    ),
                    domain=domain_config.name,
                    pattern="digression",
                    context_type="ongoing",
                    current_datetime="2024-12-11T10:00:00",
                )
            )
            # Example 3: Branch
            examples.append(
                ExampleTemplate(
                    user_message=DIGRESSION_UTTERANCES[2],  # "Do you have a branch nearby?"
                    conversation_context=create_context_after_transfer(
                        amount="50", currency="USD", recipient="Alice"
                    ),
                    expected_output=NLUOutput(
                        message_type=MessageType.DIGRESSION,
                        command="transfer_funds",
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
