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
            # Example 3: Correcting passengers
            examples.append(
                ExampleTemplate(
                    user_message="No, for 3 passengers",
                    conversation_context=create_context_before_confirmation(
                        origin=CITIES[2],
                        destination=CITIES[3],
                        departure_date="next week",
                    ),
                    expected_output=NLUOutput(
                        message_type=MessageType.CORRECTION,
                        command="book_flight",
                        slots=[
                            SlotValue(name="passengers", value="3", confidence=0.95),
                        ],
                        confidence=0.95,
                    ),
                    domain=domain_config.name,
                    pattern="correction",
                    context_type="ongoing",
                    current_datetime="2024-12-11T10:00:00",
                )
            )

            # Example 4: "Actually, I meant X not Y" - key test case pattern
            examples.append(
                ExampleTemplate(
                    user_message="Actually, I meant Denver not Chicago",
                    conversation_context=ConversationContext(
                        history=dspy.History(
                            messages=[
                                {"user_message": "Book a flight"},
                                {"user_message": "Chicago"},
                            ]
                        ),
                        current_slots={"origin": "Chicago"},
                        current_flow="book_flight",
                        expected_slots=["destination"],
                    ),
                    expected_output=NLUOutput(
                        message_type=MessageType.CORRECTION,
                        command="book_flight",
                        slots=[
                            SlotValue(name="origin", value="Denver", confidence=0.95),
                        ],
                        confidence=0.95,
                    ),
                    domain=domain_config.name,
                    pattern="correction",
                    context_type="ongoing",
                    current_datetime="2024-12-11T10:00:00",
                )
            )

            # Example 5: "I said X, not Y" variant
            examples.append(
                ExampleTemplate(
                    user_message="I said Boston, not Austin",
                    conversation_context=ConversationContext(
                        history=dspy.History(
                            messages=[
                                {"user_message": "I want to fly from Austin"},
                            ]
                        ),
                        current_slots={"origin": "Austin"},
                        current_flow="book_flight",
                        expected_slots=["destination"],
                    ),
                    expected_output=NLUOutput(
                        message_type=MessageType.CORRECTION,
                        command="book_flight",
                        slots=[
                            SlotValue(name="origin", value="Boston", confidence=0.95),
                        ],
                        confidence=0.95,
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
            # Example 2: Correcting guests
            examples.append(
                ExampleTemplate(
                    user_message="Actually, for 2 people",
                    conversation_context=ConversationContext(
                        history=dspy.History(
                            messages=[
                                {"user_message": "Book single room"},
                            ]
                        ),
                        current_slots={"guests": "1"},
                        current_flow="book_hotel",
                        expected_slots=["checkin_date"],
                    ),
                    expected_output=NLUOutput(
                        message_type=MessageType.CORRECTION,
                        command="book_hotel",
                        slots=[
                            SlotValue(name="guests", value="2", confidence=0.95),
                        ],
                        confidence=0.95,
                    ),
                    domain=domain_config.name,
                    pattern="correction",
                    context_type="ongoing",
                    current_datetime="2024-12-11T10:00:00",
                )
            )
            # Example 3: Correcting dates
            examples.append(
                ExampleTemplate(
                    user_message="I meant next weekend",
                    conversation_context=ConversationContext(
                        history=dspy.History(
                            messages=[
                                {"user_message": "Book for this weekend"},
                            ]
                        ),
                        current_slots={"checkin_date": "this weekend"},
                        current_flow="book_hotel",
                        expected_slots=["checkout_date"],
                    ),
                    expected_output=NLUOutput(
                        message_type=MessageType.CORRECTION,
                        command="book_hotel",
                        slots=[
                            SlotValue(name="checkin_date", value="next weekend", confidence=0.9),
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
            # Example 2: Party size
            examples.append(
                ExampleTemplate(
                    user_message="No, table for 4",
                    conversation_context=ConversationContext(
                        history=dspy.History(
                            messages=[
                                {"user_message": "Table for 2"},
                            ]
                        ),
                        current_slots={"party_size": "2"},
                        current_flow="book_table",
                        expected_slots=["time"],
                    ),
                    expected_output=NLUOutput(
                        message_type=MessageType.CORRECTION,
                        command="book_table",
                        slots=[
                            SlotValue(name="party_size", value="4", confidence=0.95),
                        ],
                        confidence=0.95,
                    ),
                    domain=domain_config.name,
                    pattern="correction",
                    context_type="ongoing",
                    current_datetime="2024-12-11T10:00:00",
                )
            )
            # Example 3: Location
            examples.append(
                ExampleTemplate(
                    user_message="I meant nearby",
                    conversation_context=ConversationContext(
                        history=dspy.History(
                            messages=[
                                {"user_message": "Book restaurant in city center"},
                            ]
                        ),
                        current_slots={"location": "city center"},
                        current_flow="book_table",
                        expected_slots=["cuisine"],
                    ),
                    expected_output=NLUOutput(
                        message_type=MessageType.CORRECTION,
                        command="book_table",
                        slots=[
                            SlotValue(name="location", value="nearby", confidence=0.85),
                        ],
                        confidence=0.85,
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
            # Example 2: Size
            examples.append(
                ExampleTemplate(
                    user_message="I meant size 10",
                    conversation_context=ConversationContext(
                        history=dspy.History(
                            messages=[
                                {"user_message": "Size 9"},
                            ]
                        ),
                        current_slots={"size": "9"},
                        current_flow="search_product",
                        expected_slots=["color"],
                    ),
                    expected_output=NLUOutput(
                        message_type=MessageType.CORRECTION,
                        command="search_product",
                        slots=[
                            SlotValue(name="size", value="10", confidence=0.95),
                        ],
                        confidence=0.95,
                    ),
                    domain=domain_config.name,
                    pattern="correction",
                    context_type="ongoing",
                    current_datetime="2024-12-11T10:00:00",
                )
            )
            # Example 3: Quantity
            examples.append(
                ExampleTemplate(
                    user_message="Change to 2 items",
                    conversation_context=ConversationContext(
                        history=dspy.History(
                            messages=[
                                {"user_message": "Buy 1 laptop"},
                            ]
                        ),
                        current_slots={"quantity": "1"},
                        current_flow="search_product",
                        expected_slots=["shipping_address"],
                    ),
                    expected_output=NLUOutput(
                        message_type=MessageType.CORRECTION,
                        command="search_product",
                        slots=[
                            SlotValue(name="quantity", value="2", confidence=0.95),
                        ],
                        confidence=0.95,
                    ),
                    domain=domain_config.name,
                    pattern="correction",
                    context_type="ongoing",
                    current_datetime="2024-12-11T10:00:00",
                )
            )

        elif domain_config.name == "banking":
            from soni.dataset.domains.banking import (
                AMOUNTS,
                CORRECTION_UTTERANCES,
                create_context_after_transfer,
            )

            # Example 1: Correct amount
            examples.append(
                ExampleTemplate(
                    user_message=CORRECTION_UTTERANCES[0],  # "No, I meant 50 dollars"
                    conversation_context=create_context_after_transfer(
                        amount="500", currency="dollars", recipient="mom"
                    ),
                    expected_output=NLUOutput(
                        message_type=MessageType.CORRECTION,
                        command="transfer_funds",
                        slots=[
                            SlotValue(name="amount", value="50", confidence=0.9),
                        ],
                        confidence=0.9,
                    ),
                    domain=domain_config.name,
                    pattern="correction",
                    context_type="ongoing",
                    current_datetime="2024-12-11T10:00:00",
                )
            )

            # Example 2: Update amount (implicit correction)
            examples.append(
                ExampleTemplate(
                    user_message=CORRECTION_UTTERANCES[1],
                    conversation_context=create_context_after_transfer(
                        amount=str(AMOUNTS[0]), currency="USD", recipient="Bob"
                    ),
                    expected_output=NLUOutput(
                        message_type=MessageType.CORRECTION,
                        command="transfer_funds",
                        slots=[
                            SlotValue(name="recipient", value="Alice", confidence=0.9),
                        ],
                        confidence=0.9,
                    ),
                    domain=domain_config.name,
                    pattern="correction",
                    context_type="ongoing",
                    current_datetime="2024-12-11T10:00:00",
                )
            )

            # Example 3: Explicit change
            examples.append(
                ExampleTemplate(
                    user_message=CORRECTION_UTTERANCES[2],  # "Change the amount to 100"
                    conversation_context=create_context_after_transfer(
                        amount="50", currency="USD", recipient="Mom"
                    ),
                    expected_output=NLUOutput(
                        message_type=MessageType.CORRECTION,
                        command="transfer_funds",
                        slots=[
                            SlotValue(name="amount", value="100", confidence=0.9),
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
