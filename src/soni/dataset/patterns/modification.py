"""MODIFICATION pattern generator.

Proactive modifications - user explicitly requests to change a value.

Examples:
    - "Change the destination to London"
    - "Can I modify the date?"
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


class ModificationGenerator(PatternGenerator):
    """Generates MODIFICATION pattern examples."""

    @property
    def message_type(self) -> MessageType:
        return MessageType.MODIFICATION

    def generate_examples(
        self,
        domain_config: DomainConfig,
        context_type: Literal["cold_start", "ongoing"],
        count: int = 3,
    ) -> list[ExampleTemplate]:
        """Generate MODIFICATION examples (ongoing only)."""
        if context_type == "cold_start":
            return []  # Modifications only happen in ongoing conversations

        return self._generate_ongoing_examples(domain_config, count)

    def _generate_ongoing_examples(
        self,
        domain_config: DomainConfig,
        count: int,
    ) -> list[ExampleTemplate]:
        """Generate modification examples."""
        examples = []

        if domain_config.name == "flight_booking":
            from soni.dataset.domains.flight_booking import (
                CITIES,
                DATES_RELATIVE,
                create_context_before_confirmation,
            )

            # Example 1: Explicit change request
            examples.append(
                ExampleTemplate(
                    user_message=f"Change the destination to {CITIES[6]}",
                    conversation_context=create_context_before_confirmation(
                        origin=CITIES[0],
                        destination=CITIES[1],
                        departure_date="tomorrow",
                    ),
                    expected_output=NLUOutput(
                        message_type=MessageType.MODIFICATION,
                        command="book_flight",
                        slots=[
                            SlotValue(name="destination", value=CITIES[6], confidence=0.95),
                        ],
                        confidence=0.95,
                    ),
                    domain=domain_config.name,
                    pattern="modification",
                    context_type="ongoing",
                    current_datetime="2024-12-11T10:00:00",
                )
            )

            # Example 2: "Can I modify..."
            examples.append(
                ExampleTemplate(
                    user_message=f"Can I modify the date to {DATES_RELATIVE[2]}?",
                    conversation_context=create_context_before_confirmation(
                        origin=CITIES[0],
                        destination=CITIES[1],
                        departure_date=DATES_RELATIVE[0],
                    ),
                    expected_output=NLUOutput(
                        message_type=MessageType.MODIFICATION,
                        command="book_flight",
                        slots=[
                            SlotValue(
                                name="departure_date", value=DATES_RELATIVE[2], confidence=0.9
                            ),
                        ],
                        confidence=0.9,
                    ),
                    domain=domain_config.name,
                    pattern="modification",
                    context_type="ongoing",
                    current_datetime="2024-12-11T10:00:00",
                )
            )

            # Example 3: "No, change the destination" (without new value)
            examples.append(
                ExampleTemplate(
                    user_message="No, change the destination",
                    conversation_context=create_context_before_confirmation(
                        origin="New York",
                        destination="Los Angeles",
                        departure_date="2025-12-15",
                    ),
                    expected_output=NLUOutput(
                        message_type=MessageType.MODIFICATION,
                        command="book_flight",
                        slots=[],  # No tiene el nuevo valor aún, solo solicita cambio
                        confidence=0.9,
                    ),
                    domain=domain_config.name,
                    pattern="modification",
                    context_type="ongoing",
                    current_datetime="2024-12-11T10:00:00",
                )
            )

            # Example 4: "No, change the origin" (without new value)
            examples.append(
                ExampleTemplate(
                    user_message="No, change the origin",
                    conversation_context=create_context_before_confirmation(
                        origin="New York",
                        destination="Los Angeles",
                        departure_date="2025-12-15",
                    ),
                    expected_output=NLUOutput(
                        message_type=MessageType.MODIFICATION,
                        command="book_flight",
                        slots=[],
                        confidence=0.9,
                    ),
                    domain=domain_config.name,
                    pattern="modification",
                    context_type="ongoing",
                    current_datetime="2024-12-11T10:00:00",
                )
            )

            # Example 5: "No, change the date" (without new value)
            examples.append(
                ExampleTemplate(
                    user_message="No, change the date",
                    conversation_context=create_context_before_confirmation(
                        origin="New York",
                        destination="Los Angeles",
                        departure_date="2025-12-15",
                    ),
                    expected_output=NLUOutput(
                        message_type=MessageType.MODIFICATION,
                        command="book_flight",
                        slots=[],
                        confidence=0.9,
                    ),
                    domain=domain_config.name,
                    pattern="modification",
                    context_type="ongoing",
                    current_datetime="2024-12-11T10:00:00",
                )
            )

            # Example 6: "No, change the destination to San Francisco" (with new value)
            examples.append(
                ExampleTemplate(
                    user_message="No, change the destination to San Francisco",
                    conversation_context=create_context_before_confirmation(
                        origin="New York",
                        destination="Los Angeles",
                        departure_date="2025-12-15",
                    ),
                    expected_output=NLUOutput(
                        message_type=MessageType.MODIFICATION,
                        command="book_flight",
                        slots=[
                            SlotValue(name="destination", value="San Francisco", confidence=0.95),
                        ],
                        confidence=0.95,
                    ),
                    domain=domain_config.name,
                    pattern="modification",
                    context_type="ongoing",
                    current_datetime="2024-12-11T10:00:00",
                )
            )

        elif domain_config.name == "hotel_booking":
            from soni.dataset.domains.hotel_booking import CITIES

            examples.append(
                ExampleTemplate(
                    user_message=f"I want to change the location to {CITIES[3]}",
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
                        message_type=MessageType.MODIFICATION,
                        command="book_hotel",
                        slots=[
                            SlotValue(name="location", value=CITIES[3], confidence=0.95),
                        ],
                        confidence=0.95,
                    ),
                    domain=domain_config.name,
                    pattern="modification",
                    context_type="ongoing",
                    current_datetime="2024-12-11T10:00:00",
                )
            )

        elif domain_config.name == "restaurant":
            from soni.dataset.domains.restaurant import PARTY_SIZES

            examples.append(
                ExampleTemplate(
                    user_message=f"Can I change the party size to {PARTY_SIZES[2]}?",
                    conversation_context=ConversationContext(
                        history=dspy.History(
                            messages=[
                                {"user_message": f"Table for {PARTY_SIZES[0]}"},
                            ]
                        ),
                        current_slots={"party_size": str(PARTY_SIZES[0])},
                        current_flow="book_table",
                        expected_slots=[],
                    ),
                    expected_output=NLUOutput(
                        message_type=MessageType.MODIFICATION,
                        command="book_table",
                        slots=[
                            SlotValue(name="party_size", value=str(PARTY_SIZES[2]), confidence=0.9),
                        ],
                        confidence=0.9,
                    ),
                    domain=domain_config.name,
                    pattern="modification",
                    context_type="ongoing",
                    current_datetime="2024-12-11T10:00:00",
                )
            )

        elif domain_config.name == "ecommerce":
            from soni.dataset.domains.ecommerce import SIZES

            examples.append(
                ExampleTemplate(
                    user_message=f"I want to modify the size to {SIZES[2]}",
                    conversation_context=ConversationContext(
                        history=dspy.History(
                            messages=[
                                {"user_message": f"Size {SIZES[0]}"},
                            ]
                        ),
                        current_slots={"size": SIZES[0]},
                        current_flow="search_product",
                        expected_slots=[],
                    ),
                    expected_output=NLUOutput(
                        message_type=MessageType.MODIFICATION,
                        command="search_product",
                        slots=[
                            SlotValue(name="size", value=SIZES[2], confidence=0.9),
                        ],
                        confidence=0.9,
                    ),
                    domain=domain_config.name,
                    pattern="modification",
                    context_type="ongoing",
                    current_datetime="2024-12-11T10:00:00",
                )
            )

        elif domain_config.name == "banking":
            from soni.dataset.domains.banking import (
                AMOUNTS,
                MODIFICATION_UTTERANCES,
                create_context_after_transfer,
            )

            # Example 1: Change amount explicitly
            examples.append(
                ExampleTemplate(
                    user_message=f"Change the amount to {AMOUNTS[1]}",
                    conversation_context=create_context_after_transfer(
                        amount=str(AMOUNTS[0]), currency="USD", recipient="mom"
                    ),
                    expected_output=NLUOutput(
                        message_type=MessageType.MODIFICATION,
                        command="transfer_funds",
                        slots=[
                            SlotValue(name="amount", value=str(AMOUNTS[1]), confidence=0.95),
                        ],
                        confidence=0.95,
                    ),
                    domain=domain_config.name,
                    pattern="modification",
                    context_type="ongoing",
                    current_datetime="2024-12-11T10:00:00",
                )
            )

            # Example 2: "Can I change the currency?"
            examples.append(
                ExampleTemplate(
                    user_message=MODIFICATION_UTTERANCES[2],  # "Can I change the currency?"
                    conversation_context=create_context_after_transfer(
                        amount="100", currency="USD", recipient="mom"
                    ),
                    expected_output=NLUOutput(
                        message_type=MessageType.MODIFICATION,
                        command="transfer_funds",
                        slots=[],  # Intent to change, but no new value provided
                        confidence=0.9,
                    ),
                    domain=domain_config.name,
                    pattern="modification",
                    context_type="ongoing",
                    current_datetime="2024-12-11T10:00:00",
                )
            )

        return examples[:count]
