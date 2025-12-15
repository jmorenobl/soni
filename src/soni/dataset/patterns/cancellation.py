"""CANCELLATION pattern generator.

User abandons current task.

Examples:
    - "Cancel"
    - "Never mind"
    - "Forget it"
"""

from typing import Literal

import dspy

from soni.core.commands import CancelFlow
from soni.dataset.base import (
    ConversationContext,
    DomainConfig,
    ExampleTemplate,
    PatternGenerator,
)
from soni.du.models import NLUOutput


class CancellationGenerator(PatternGenerator):
    """Generates CANCELLATION pattern examples."""

    def generate_examples(
        self,
        domain_config: DomainConfig,
        context_type: Literal["cold_start", "ongoing"],
        count: int = 3,
    ) -> list[ExampleTemplate]:
        """Generate CANCELLATION examples (ongoing only)."""
        if context_type == "cold_start":
            return []  # Cancellations only happen in ongoing conversations

        return self._generate_ongoing_examples(domain_config, count)

    def _generate_ongoing_examples(
        self,
        domain_config: DomainConfig,
        count: int,
    ) -> list[ExampleTemplate]:
        """Generate cancellation examples."""
        examples = []

        if domain_config.name == "flight_booking":
            from soni.dataset.domains.flight_booking import CANCELLATION_UTTERANCES

            examples.append(
                ExampleTemplate(
                    user_message=CANCELLATION_UTTERANCES[0],
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
                        commands=[
                            CancelFlow(reason="User cancelled"),
                        ],
                        confidence=0.9,
                    ),
                    domain=domain_config.name,
                    pattern="cancellation",
                    context_type="ongoing",
                    current_datetime="2024-12-11T10:00:00",
                )
            )

            examples.append(
                ExampleTemplate(
                    user_message=CANCELLATION_UTTERANCES[1],
                    conversation_context=ConversationContext(
                        history=dspy.History(
                            messages=[
                                {"user_message": "Book a flight from Madrid to Barcelona"},
                            ]
                        ),
                        current_slots={"origin": "Madrid", "destination": "Barcelona"},
                        current_flow="book_flight",
                        expected_slots=["departure_date"],
                    ),
                    expected_output=NLUOutput(
                        commands=[
                            CancelFlow(reason="User cancelled"),
                        ],
                        confidence=0.9,
                    ),
                    domain=domain_config.name,
                    pattern="cancellation",
                    context_type="ongoing",
                    current_datetime="2024-12-11T10:00:00",
                )
            )

            # Example with "Actually, cancel this"
            examples.append(
                ExampleTemplate(
                    user_message="Actually, cancel this",
                    conversation_context=ConversationContext(
                        history=dspy.History(
                            messages=[
                                {"user_message": "Book a flight please"},
                                {"user_message": "Boston"},
                            ]
                        ),
                        current_slots={"origin": "Boston"},
                        current_flow="book_flight",
                        expected_slots=["destination"],
                    ),
                    expected_output=NLUOutput(
                        commands=[
                            CancelFlow(reason="User requested cancellation"),
                        ],
                        confidence=0.9,
                    ),
                    domain=domain_config.name,
                    pattern="cancellation",
                    context_type="ongoing",
                    current_datetime="2024-12-11T10:00:00",
                )
            )

            # Additional example with "Cancel this"
            examples.append(
                ExampleTemplate(
                    user_message="Cancel this",
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
                        commands=[
                            CancelFlow(reason="User requested cancellation"),
                        ],
                        confidence=0.9,
                    ),
                    domain=domain_config.name,
                    pattern="cancellation",
                    context_type="ongoing",
                    current_datetime="2024-12-11T10:00:00",
                )
            )

        elif domain_config.name == "hotel_booking":
            # Example 1
            examples.append(
                ExampleTemplate(
                    user_message="Cancel",
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
                            CancelFlow(reason="User cancelled"),
                        ],
                        confidence=0.9,
                    ),
                    domain=domain_config.name,
                    pattern="cancellation",
                    context_type="ongoing",
                    current_datetime="2024-12-11T10:00:00",
                )
            )
            # Example 2
            examples.append(
                ExampleTemplate(
                    user_message="Stop booking",
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
                        commands=[
                            CancelFlow(reason="User stopped booking"),
                        ],
                        confidence=0.9,
                    ),
                    domain=domain_config.name,
                    pattern="cancellation",
                    context_type="ongoing",
                    current_datetime="2024-12-11T10:00:00",
                )
            )
            # Example 3
            examples.append(
                ExampleTemplate(
                    user_message="Forget about it",
                    conversation_context=ConversationContext(
                        history=dspy.History(
                            messages=[
                                {"user_message": "Hotel in Paris"},
                            ]
                        ),
                        current_slots={"location": "Paris"},
                        current_flow="book_hotel",
                        expected_slots=["dates"],
                    ),
                    expected_output=NLUOutput(
                        commands=[
                            CancelFlow(reason="User cancelled"),
                        ],
                        confidence=0.9,
                    ),
                    domain=domain_config.name,
                    pattern="cancellation",
                    context_type="ongoing",
                    current_datetime="2024-12-11T10:00:00",
                )
            )

        elif domain_config.name == "restaurant":
            # Example 1
            examples.append(
                ExampleTemplate(
                    user_message="Never mind",
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
                            CancelFlow(reason="User changed mind"),
                        ],
                        confidence=0.9,
                    ),
                    domain=domain_config.name,
                    pattern="cancellation",
                    context_type="ongoing",
                    current_datetime="2024-12-11T10:00:00",
                )
            )
            # Example 2
            examples.append(
                ExampleTemplate(
                    user_message="Cancel reservation",
                    conversation_context=ConversationContext(
                        history=dspy.History(
                            messages=[
                                {"user_message": "Table for two"},
                            ]
                        ),
                        current_slots={"party_size": "2"},
                        current_flow="book_table",
                        expected_slots=["time"],
                    ),
                    expected_output=NLUOutput(
                        commands=[
                            CancelFlow(reason="User cancelled"),
                        ],
                        confidence=0.9,
                    ),
                    domain=domain_config.name,
                    pattern="cancellation",
                    context_type="ongoing",
                    current_datetime="2024-12-11T10:00:00",
                )
            )
            # Example 3
            examples.append(
                ExampleTemplate(
                    user_message="Abort",
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
                        commands=[
                            CancelFlow(reason="User aborted"),
                        ],
                        confidence=0.95,
                    ),
                    domain=domain_config.name,
                    pattern="cancellation",
                    context_type="ongoing",
                    current_datetime="2024-12-11T10:00:00",
                )
            )

        elif domain_config.name == "ecommerce":
            # Example 1
            examples.append(
                ExampleTemplate(
                    user_message="Forget it",
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
                        commands=[
                            CancelFlow(reason="User cancelled"),
                        ],
                        confidence=0.9,
                    ),
                    domain=domain_config.name,
                    pattern="cancellation",
                    context_type="ongoing",
                    current_datetime="2024-12-11T10:00:00",
                )
            )
            # Example 2
            examples.append(
                ExampleTemplate(
                    user_message="Cancel search",
                    conversation_context=ConversationContext(
                        history=dspy.History(
                            messages=[
                                {"user_message": "Look for shoes"},
                            ]
                        ),
                        current_slots={"product": "shoes"},
                        current_flow="search_product",
                        expected_slots=["size"],
                    ),
                    expected_output=NLUOutput(
                        commands=[
                            CancelFlow(reason="User cancelled"),
                        ],
                        confidence=0.9,
                    ),
                    domain=domain_config.name,
                    pattern="cancellation",
                    context_type="ongoing",
                    current_datetime="2024-12-11T10:00:00",
                )
            )
            # Example 3
            examples.append(
                ExampleTemplate(
                    user_message="Stop",
                    conversation_context=ConversationContext(
                        history=dspy.History(
                            messages=[
                                {"user_message": "Shopping"},
                            ]
                        ),
                        current_slots={},
                        current_flow="search_product",
                        expected_slots=["product"],
                    ),
                    expected_output=NLUOutput(
                        commands=[
                            CancelFlow(reason="User stopped"),
                        ],
                        confidence=0.95,
                    ),
                    domain=domain_config.name,
                    pattern="cancellation",
                    context_type="ongoing",
                    current_datetime="2024-12-11T10:00:00",
                )
            )

        elif domain_config.name == "banking":
            from soni.dataset.domains.banking import CANCELLATION_UTTERANCES

            # Example 1
            examples.append(
                ExampleTemplate(
                    user_message=CANCELLATION_UTTERANCES[0],
                    conversation_context=ConversationContext(
                        history=dspy.History(
                            messages=[
                                {"user_message": "I want to transfer money"},
                            ]
                        ),
                        current_slots={},
                        current_flow="transfer_funds",
                        expected_slots=["amount"],
                    ),
                    expected_output=NLUOutput(
                        commands=[
                            CancelFlow(reason="User cancelled"),
                        ],
                        confidence=0.9,
                    ),
                    domain=domain_config.name,
                    pattern="cancellation",
                    context_type="ongoing",
                    current_datetime="2024-12-11T10:00:00",
                )
            )
            # Example 2: Stop
            examples.append(
                ExampleTemplate(
                    user_message=CANCELLATION_UTTERANCES[
                        1
                    ],  # "Stop the transfer" (assuming based on standard list)
                    conversation_context=ConversationContext(
                        history=dspy.History(
                            messages=[
                                {"user_message": "Transfer 100"},
                            ]
                        ),
                        current_slots={"amount": "100"},
                        current_flow="transfer_funds",
                        expected_slots=["recipient"],
                    ),
                    expected_output=NLUOutput(
                        commands=[
                            CancelFlow(reason="User stopped transfer"),
                        ],
                        confidence=0.95,
                    ),
                    domain=domain_config.name,
                    pattern="cancellation",
                    context_type="ongoing",
                    current_datetime="2024-12-11T10:00:00",
                )
            )
            # Example 3: Nevermind
            examples.append(
                ExampleTemplate(
                    user_message=CANCELLATION_UTTERANCES[3],  # "Nevermind"
                    conversation_context=ConversationContext(
                        history=dspy.History(
                            messages=[
                                {"user_message": "Send money"},
                            ]
                        ),
                        current_slots={},
                        current_flow="transfer_funds",
                        expected_slots=["amount"],
                    ),
                    expected_output=NLUOutput(
                        commands=[
                            CancelFlow(reason="User changed mind"),
                        ],
                        confidence=0.9,
                    ),
                    domain=domain_config.name,
                    pattern="cancellation",
                    context_type="ongoing",
                    current_datetime="2024-12-11T10:00:00",
                )
            )

        return examples[:count]
