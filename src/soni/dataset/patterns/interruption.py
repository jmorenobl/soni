"""INTERRUPTION pattern generator.

User starts new task mid-conversation or at conversation start.

Examples:
    Cold start: "I want to book a flight"
    Ongoing: "Actually, check hotel prices first"
"""

from typing import Literal

import dspy

from soni.core.commands import StartFlow
from soni.dataset.base import (
    ConversationContext,
    DomainConfig,
    ExampleTemplate,
    PatternGenerator,
)
from soni.du.models import NLUOutput


class InterruptionGenerator(PatternGenerator):
    """Generates INTERRUPTION pattern examples."""

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
                        commands=[
                            StartFlow(flow_name="book_flight"),
                        ],
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
                        commands=[
                            StartFlow(flow_name="book_hotel"),
                        ],
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
                        commands=[
                            StartFlow(flow_name="book_table"),
                        ],
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
                        commands=[
                            StartFlow(flow_name="search_product"),
                        ],
                        confidence=0.9,
                    ),
                    domain=domain_config.name,
                    pattern="interruption",
                    context_type="cold_start",
                    current_datetime="2024-12-11T10:00:00",
                )
            )

        elif domain_config.name == "banking":
            from soni.dataset.domains.banking import TRANSFER_UTTERANCES

            examples.append(
                ExampleTemplate(
                    user_message=TRANSFER_UTTERANCES[0],
                    conversation_context=ConversationContext(
                        history=dspy.History(messages=[]),
                        current_slots={},
                        current_flow="none",
                        expected_slots=[],
                    ),
                    expected_output=NLUOutput(
                        commands=[
                            StartFlow(flow_name="transfer_funds"),
                        ],
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
                        commands=[
                            StartFlow(flow_name="search_hotels"),
                        ],
                        confidence=0.85,
                    ),
                    domain=domain_config.name,
                    pattern="interruption",
                    context_type="ongoing",
                    current_datetime="2024-12-11T10:00:00",
                )
            )

            # Follow-up with slot extraction: "and what about a return on Dec 20?"
            examples.append(
                ExampleTemplate(
                    user_message="and what about a return on December 20th?",
                    conversation_context=ConversationContext(
                        history=dspy.History(
                            messages=[
                                {"role": "assistant", "content": "When would you like to return?"},
                                {"role": "user", "content": "December 15th"},
                                {
                                    "role": "assistant",
                                    "content": "Found flights for December 15th.",
                                },
                            ]
                        ),
                        current_slots={
                            "origin": "Madrid",
                            "destination": "Paris",
                            "departure_date": "2025-12-15",
                        },
                        current_flow="book_flight",
                        expected_slots=["return_date"],
                        current_prompted_slot="return_date",
                        conversation_state="waiting_for_slot",
                    ),
                    expected_output=NLUOutput(
                        commands=[
                            StartFlow(
                                flow_name="book_flight",
                                slots={"return_date": "December 20th"},
                            ),
                        ],
                        confidence=0.95,
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
                        commands=[
                            StartFlow(flow_name="search_flights"),
                        ],
                        confidence=0.85,
                    ),
                    domain=domain_config.name,
                    pattern="interruption",
                    context_type="ongoing",
                    current_datetime="2024-12-11T10:00:00",
                )
            )

            # Follow-up with slot extraction: "and for next week?"
            examples.append(
                ExampleTemplate(
                    user_message="and what about next week?",
                    conversation_context=ConversationContext(
                        history=dspy.History(
                            messages=[
                                {
                                    "role": "assistant",
                                    "content": "When would you like to check in?",
                                },
                                {"role": "user", "content": "December 15th"},
                                {
                                    "role": "assistant",
                                    "content": "Found rooms available for December 15th.",
                                },
                            ]
                        ),
                        current_slots={"location": "Paris", "checkin_date": "2025-12-15"},
                        current_flow="book_hotel",
                        expected_slots=["checkout_date"],
                        current_prompted_slot="checkout_date",
                        conversation_state="waiting_for_slot",
                    ),
                    expected_output=NLUOutput(
                        commands=[
                            StartFlow(
                                flow_name="book_hotel",
                                slots={"checkin_date": "next week"},
                            ),
                        ],
                        confidence=0.95,
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
                        commands=[
                            StartFlow(flow_name="book_flight"),
                        ],
                        confidence=0.85,
                    ),
                    domain=domain_config.name,
                    pattern="interruption",
                    context_type="ongoing",
                    current_datetime="2024-12-11T10:00:00",
                )
            )

            # Follow-up with slot extraction: "and for 8 PM?"
            examples.append(
                ExampleTemplate(
                    user_message="and what about for 8 PM?",
                    conversation_context=ConversationContext(
                        history=dspy.History(
                            messages=[
                                {"role": "assistant", "content": "What time would you prefer?"},
                                {"role": "user", "content": "7 PM"},
                                {
                                    "role": "assistant",
                                    "content": "Reserved for 7 PM.",
                                },
                            ]
                        ),
                        current_slots={"location": "Madrid", "date": "2025-12-15", "time": "7 PM"},
                        current_flow="book_table",
                        expected_slots=["party_size"],
                        current_prompted_slot="party_size",
                        conversation_state="waiting_for_slot",
                    ),
                    expected_output=NLUOutput(
                        commands=[
                            StartFlow(
                                flow_name="book_table",
                                slots={"time": "8 PM"},
                            ),
                        ],
                        confidence=0.95,
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
                        commands=[
                            StartFlow(flow_name="search_flights"),
                        ],
                        confidence=0.85,
                    ),
                    domain=domain_config.name,
                    pattern="interruption",
                    context_type="ongoing",
                    current_datetime="2024-12-11T10:00:00",
                )
            )

            # Follow-up with slot extraction: "what about in blue?"
            examples.append(
                ExampleTemplate(
                    user_message="what about in blue?",
                    conversation_context=ConversationContext(
                        history=dspy.History(
                            messages=[
                                {"role": "assistant", "content": "What color would you prefer?"},
                                {"role": "user", "content": "black"},
                                {
                                    "role": "assistant",
                                    "content": "Found black laptops starting at $999.",
                                },
                            ]
                        ),
                        current_slots={"product": "laptop", "color": "black"},
                        current_flow="search_product",
                        expected_slots=["quantity"],
                        current_prompted_slot="quantity",
                        conversation_state="waiting_for_slot",
                    ),
                    expected_output=NLUOutput(
                        commands=[
                            StartFlow(
                                flow_name="search_product",
                                slots={"color": "blue"},
                            ),
                        ],
                        confidence=0.95,
                    ),
                    domain=domain_config.name,
                    pattern="interruption",
                    context_type="ongoing",
                    current_datetime="2024-12-11T10:00:00",
                )
            )

        elif domain_config.name == "banking":
            # Example 1: Explicit switch - "check my balance instead"
            examples.append(
                ExampleTemplate(
                    user_message="Actually, check my balance instead",
                    conversation_context=ConversationContext(
                        history=dspy.History(
                            messages=[
                                {"role": "user", "content": "I want to transfer money"},
                                {
                                    "role": "assistant",
                                    "content": "How much would you like to transfer?",
                                },
                            ]
                        ),
                        current_slots={},
                        current_flow="transfer_funds",
                        expected_slots=["amount"],
                        conversation_state="waiting_for_slot",
                    ),
                    expected_output=NLUOutput(
                        commands=[
                            StartFlow(flow_name="check_balance"),
                        ],
                        confidence=0.85,
                    ),
                    domain=domain_config.name,
                    pattern="interruption",
                    context_type="ongoing",
                    current_datetime="2024-12-11T10:00:00",
                )
            )

            # Example 2: Implicit switch - "How much do I have?" (matches check_balance description)
            examples.append(
                ExampleTemplate(
                    user_message="How much do I have?",
                    conversation_context=ConversationContext(
                        history=dspy.History(
                            messages=[
                                {"role": "user", "content": "I want to transfer money"},
                                {
                                    "role": "assistant",
                                    "content": "How much would you like to transfer?",
                                },
                            ]
                        ),
                        current_slots={},
                        current_flow="transfer_funds",
                        expected_slots=["amount"],
                        conversation_state="waiting_for_slot",
                    ),
                    expected_output=NLUOutput(
                        commands=[
                            StartFlow(flow_name="check_balance"),
                        ],
                        confidence=0.90,
                    ),
                    domain=domain_config.name,
                    pattern="interruption",
                    context_type="ongoing",
                    current_datetime="2024-12-11T10:00:00",
                )
            )

            # Example 3: Implicit switch - "What's my balance?"
            examples.append(
                ExampleTemplate(
                    user_message="What's my balance?",
                    conversation_context=ConversationContext(
                        history=dspy.History(
                            messages=[
                                {"role": "user", "content": "I want to send money to mom"},
                                {"role": "assistant", "content": "How much?"},
                            ]
                        ),
                        current_slots={"recipient": "mom"},
                        current_flow="transfer_funds",
                        expected_slots=["amount", "currency"],
                        conversation_state="waiting_for_slot",
                    ),
                    expected_output=NLUOutput(
                        commands=[
                            StartFlow(flow_name="check_balance"),
                        ],
                        confidence=0.90,
                    ),
                    domain=domain_config.name,
                    pattern="interruption",
                    context_type="ongoing",
                    current_datetime="2024-12-11T10:00:00",
                )
            )

            # Example 4: Implicit switch during block_card - asking about balance
            examples.append(
                ExampleTemplate(
                    user_message="First, how much money is in my account?",
                    conversation_context=ConversationContext(
                        history=dspy.History(
                            messages=[
                                {"role": "user", "content": "I need to block my card"},
                                {
                                    "role": "assistant",
                                    "content": "What are the last 4 digits of your card?",
                                },
                            ]
                        ),
                        current_slots={},
                        current_flow="block_card",
                        expected_slots=["card_last_4"],
                        conversation_state="waiting_for_slot",
                    ),
                    expected_output=NLUOutput(
                        commands=[
                            StartFlow(flow_name="check_balance"),
                        ],
                        confidence=0.85,
                    ),
                    domain=domain_config.name,
                    pattern="interruption",
                    context_type="ongoing",
                    current_datetime="2024-12-11T10:00:00",
                )
            )

            # Example 5: Implicit switch from check_balance to transfer
            examples.append(
                ExampleTemplate(
                    user_message="I want to send some to my sister",
                    conversation_context=ConversationContext(
                        history=dspy.History(
                            messages=[
                                {"role": "user", "content": "Check my balance"},
                                {
                                    "role": "assistant",
                                    "content": "Which account (checking or savings)?",
                                },
                            ]
                        ),
                        current_slots={},
                        current_flow="check_balance",
                        expected_slots=["account_type"],
                        conversation_state="waiting_for_slot",
                    ),
                    expected_output=NLUOutput(
                        commands=[
                            StartFlow(
                                flow_name="transfer_funds",
                                slots={"recipient": "sister"},
                            ),
                        ],
                        confidence=0.85,
                    ),
                    domain=domain_config.name,
                    pattern="interruption",
                    context_type="ongoing",
                    current_datetime="2024-12-11T10:00:00",
                )
            )

            # Example 6: Follow-up interruption WITH slot extraction
            examples.append(
                ExampleTemplate(
                    user_message="and in my credit account?",
                    conversation_context=ConversationContext(
                        history=dspy.History(
                            messages=[
                                {"role": "assistant", "content": "Which account?"},
                                {"role": "user", "content": "debit account"},
                                {
                                    "role": "assistant",
                                    "content": "Your debit balance is USD 0.00.",
                                },
                            ]
                        ),
                        current_slots={"recipient": "mom"},
                        current_flow="transfer_funds",
                        expected_slots=["amount"],
                        current_prompted_slot="amount",
                        conversation_state="waiting_for_slot",
                    ),
                    expected_output=NLUOutput(
                        commands=[
                            StartFlow(
                                flow_name="check_balance",
                                slots={"account_type": "credit"},
                            ),
                        ],
                        confidence=0.95,
                    ),
                    domain=domain_config.name,
                    pattern="interruption",
                    context_type="ongoing",
                    current_datetime="2024-12-11T10:00:00",
                )
            )

            # Example 7: Alternative phrasing - "What about my savings?"
            examples.append(
                ExampleTemplate(
                    user_message="and what about my savings account?",
                    conversation_context=ConversationContext(
                        history=dspy.History(
                            messages=[
                                {"role": "assistant", "content": "Which account?"},
                                {"role": "user", "content": "checking"},
                                {
                                    "role": "assistant",
                                    "content": "Your checking balance is $5,000.",
                                },
                            ]
                        ),
                        current_slots={"recipient": "mom"},
                        current_flow="transfer_funds",
                        expected_slots=["amount"],
                        current_prompted_slot="amount",
                        conversation_state="waiting_for_slot",
                    ),
                    expected_output=NLUOutput(
                        commands=[
                            StartFlow(
                                flow_name="check_balance",
                                slots={"account_type": "savings"},
                            ),
                        ],
                        confidence=0.95,
                    ),
                    domain=domain_config.name,
                    pattern="interruption",
                    context_type="ongoing",
                    current_datetime="2024-12-11T10:00:00",
                )
            )

            # Example 8: Direct account check during transfer - "Check my checking account"
            examples.append(
                ExampleTemplate(
                    user_message="Check my checking account",
                    conversation_context=ConversationContext(
                        history=dspy.History(
                            messages=[
                                {
                                    "role": "assistant",
                                    "content": "How much would you like to send?",
                                },
                            ]
                        ),
                        current_slots={"recipient": "Mom"},
                        current_flow="transfer_funds",
                        expected_slots=["amount"],
                        current_prompted_slot="amount",
                        conversation_state="waiting_for_slot",
                    ),
                    expected_output=NLUOutput(
                        commands=[
                            StartFlow(
                                flow_name="check_balance",
                                slots={"account_type": "checking"},
                            ),
                        ],
                        confidence=0.95,
                    ),
                    domain=domain_config.name,
                    pattern="interruption",
                    context_type="ongoing",
                    current_datetime="2024-12-11T10:00:00",
                )
            )

        return examples[:count]
