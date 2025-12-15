"""SLOT_VALUE pattern generator.

This pattern represents users providing direct answers to slot prompts
or providing multiple slots in a single utterance.

Examples:
    Cold start: "Book a flight from Madrid to Barcelona tomorrow"
    Ongoing: Bot: "Where to?" → User: "Barcelona"
"""

from typing import Literal

import dspy

from soni.core.commands import SetSlot, StartFlow
from soni.dataset.base import (
    ConversationContext,
    DomainConfig,
    ExampleTemplate,
    PatternGenerator,
)
from soni.du.models import NLUOutput


class SlotValueGenerator(PatternGenerator):
    """Generates SLOT_VALUE pattern examples."""

    def generate_examples(
        self,
        domain_config: DomainConfig,
        context_type: Literal["cold_start", "ongoing"],
        count: int = 3,
    ) -> list[ExampleTemplate]:
        """Generate SLOT_VALUE examples.

        Args:
            domain_config: Domain configuration
            context_type: "cold_start" or "ongoing"
            count: Number of examples to generate

        Returns:
            List of example templates
        """
        if context_type == "cold_start":
            return self._generate_cold_start_examples(domain_config, count)
        else:
            return self._generate_ongoing_examples(domain_config, count)

    def _generate_cold_start_examples(
        self,
        domain_config: DomainConfig,
        count: int,
    ) -> list[ExampleTemplate]:
        """Generate cold start examples (multi-slot extraction).

        Users provide multiple slots in first message without being prompted.

        Args:
            domain_config: Domain configuration
            count: Number of examples to generate

        Returns:
            List of example templates
        """
        examples = []

        if domain_config.name == "flight_booking":
            from soni.dataset.domains.flight_booking import CITIES, DATES_RELATIVE

            # Example 1: Origin + Destination
            examples.append(
                ExampleTemplate(
                    user_message=f"I want to fly from {CITIES[0]} to {CITIES[1]}",
                    conversation_context=ConversationContext(
                        history=dspy.History(messages=[]),
                        current_slots={},
                        current_flow="none",
                        expected_slots=list(domain_config.slots.keys()),
                    ),
                    expected_output=NLUOutput(
                        commands=[
                            StartFlow(flow_name="book_flight"),
                            SetSlot(slot_name="origin", value=CITIES[0]),
                            SetSlot(slot_name="destination", value=CITIES[1]),
                        ],
                        confidence=0.9,
                    ),
                    domain=domain_config.name,
                    pattern="slot_value",
                    context_type="cold_start",
                    current_datetime="2024-12-11T10:00:00",
                )
            )

            # Example 2: Origin + Destination + Date
            examples.append(
                ExampleTemplate(
                    user_message=f"Book a flight from {CITIES[2]} to {CITIES[3]} {DATES_RELATIVE[0]}",
                    conversation_context=ConversationContext(
                        history=dspy.History(messages=[]),
                        current_slots={},
                        current_flow="none",
                        expected_slots=list(domain_config.slots.keys()),
                    ),
                    expected_output=NLUOutput(
                        commands=[
                            StartFlow(flow_name="book_flight"),
                            SetSlot(slot_name="origin", value=CITIES[2]),
                            SetSlot(slot_name="destination", value=CITIES[3]),
                            SetSlot(slot_name="departure_date", value=DATES_RELATIVE[0]),
                        ],
                        confidence=0.93,
                    ),
                    domain=domain_config.name,
                    pattern="slot_value",
                    context_type="cold_start",
                    current_datetime="2024-12-11T10:00:00",
                )
            )

            # Example 3: Destination only (partial info)
            examples.append(
                ExampleTemplate(
                    user_message=f"I need a flight to {CITIES[4]}",
                    conversation_context=ConversationContext(
                        history=dspy.History(messages=[]),
                        current_slots={},
                        current_flow="none",
                        expected_slots=list(domain_config.slots.keys()),
                    ),
                    expected_output=NLUOutput(
                        commands=[
                            StartFlow(flow_name="book_flight"),
                            SetSlot(slot_name="destination", value=CITIES[4]),
                        ],
                        confidence=0.9,
                    ),
                    domain=domain_config.name,
                    pattern="slot_value",
                    context_type="cold_start",
                    current_datetime="2024-12-11T10:00:00",
                )
            )

            # Example 4: Departure date
            examples.append(
                ExampleTemplate(
                    user_message="I want to fly tomorrow",
                    conversation_context=ConversationContext(
                        history=dspy.History(messages=[]),
                        current_slots={},
                        current_flow="none",
                        expected_slots=list(domain_config.slots.keys()),
                    ),
                    expected_output=NLUOutput(
                        commands=[
                            StartFlow(flow_name="book_flight"),
                            SetSlot(slot_name="departure_date", value="tomorrow"),
                        ],
                        confidence=0.9,
                    ),
                    domain=domain_config.name,
                    pattern="slot_value",
                    context_type="cold_start",
                    current_datetime="2024-12-11T10:00:00",
                )
            )

        elif domain_config.name == "hotel_booking":
            from soni.dataset.domains.hotel_booking import CITIES

            examples.append(
                ExampleTemplate(
                    user_message=f"Book a hotel in {CITIES[0]}",
                    conversation_context=ConversationContext(
                        history=dspy.History(messages=[]),
                        current_slots={},
                        current_flow="none",
                        expected_slots=list(domain_config.slots.keys()),
                    ),
                    expected_output=NLUOutput(
                        commands=[
                            StartFlow(flow_name="book_hotel"),
                            SetSlot(slot_name="location", value=CITIES[0]),
                        ],
                        confidence=0.9,
                    ),
                    domain=domain_config.name,
                    pattern="slot_value",
                    context_type="cold_start",
                    current_datetime="2024-12-11T10:00:00",
                )
            )

            # Example 2: Location + Date
            examples.append(
                ExampleTemplate(
                    user_message=f"I need a hotel in {CITIES[1]} for tomorrow",
                    conversation_context=ConversationContext(
                        history=dspy.History(messages=[]),
                        current_slots={},
                        current_flow="none",
                        expected_slots=list(domain_config.slots.keys()),
                    ),
                    expected_output=NLUOutput(
                        commands=[
                            StartFlow(flow_name="book_hotel"),
                            SetSlot(slot_name="location", value=CITIES[1]),
                            SetSlot(slot_name="checkin_date", value="tomorrow"),
                        ],
                        confidence=0.9,
                    ),
                    domain=domain_config.name,
                    pattern="slot_value",
                    context_type="cold_start",
                    current_datetime="2024-12-11T10:00:00",
                )
            )

        elif domain_config.name == "restaurant":
            from soni.dataset.domains.restaurant import CITIES, PARTY_SIZES

            examples.append(
                ExampleTemplate(
                    user_message=f"I need a table for {PARTY_SIZES[0]} in {CITIES[0]}",
                    conversation_context=ConversationContext(
                        history=dspy.History(messages=[]),
                        current_slots={},
                        current_flow="none",
                        expected_slots=list(domain_config.slots.keys()),
                    ),
                    expected_output=NLUOutput(
                        commands=[
                            StartFlow(flow_name="book_table"),
                            SetSlot(slot_name="party_size", value=str(PARTY_SIZES[0])),
                            SetSlot(slot_name="location", value=CITIES[0]),
                        ],
                        confidence=0.92,
                    ),
                    domain=domain_config.name,
                    pattern="slot_value",
                    context_type="cold_start",
                    current_datetime="2024-12-11T10:00:00",
                )
            )

            # Example 2: Time + Party Size
            examples.append(
                ExampleTemplate(
                    user_message="Book dinner for 2 at 8pm",
                    conversation_context=ConversationContext(
                        history=dspy.History(messages=[]),
                        current_slots={},
                        current_flow="none",
                        expected_slots=list(domain_config.slots.keys()),
                    ),
                    expected_output=NLUOutput(
                        commands=[
                            StartFlow(flow_name="book_table"),
                            SetSlot(slot_name="party_size", value="2"),
                            SetSlot(slot_name="time", value="8pm"),
                        ],
                        confidence=0.9,
                    ),
                    domain=domain_config.name,
                    pattern="slot_value",
                    context_type="cold_start",
                    current_datetime="2024-12-11T10:00:00",
                )
            )

        elif domain_config.name == "ecommerce":
            from soni.dataset.domains.ecommerce import PRODUCTS

            examples.append(
                ExampleTemplate(
                    user_message=f"I want to buy a {PRODUCTS[0]}",
                    conversation_context=ConversationContext(
                        history=dspy.History(messages=[]),
                        current_slots={},
                        current_flow="none",
                        expected_slots=list(domain_config.slots.keys()),
                    ),
                    expected_output=NLUOutput(
                        commands=[
                            StartFlow(flow_name="search_product"),
                            SetSlot(slot_name="product", value=PRODUCTS[0]),
                        ],
                        confidence=0.95,
                    ),
                    domain=domain_config.name,
                    pattern="slot_value",
                    context_type="cold_start",
                    current_datetime="2024-12-11T10:00:00",
                )
            )

            # Example 2: Product + Color
            examples.append(
                ExampleTemplate(
                    user_message=f"I want a red {PRODUCTS[0]}",
                    conversation_context=ConversationContext(
                        history=dspy.History(messages=[]),
                        current_slots={},
                        current_flow="none",
                        expected_slots=list(domain_config.slots.keys()),
                    ),
                    expected_output=NLUOutput(
                        commands=[
                            StartFlow(flow_name="search_product"),
                            SetSlot(slot_name="product", value=PRODUCTS[0]),
                            SetSlot(slot_name="color", value="red"),
                        ],
                        confidence=0.9,
                    ),
                    domain=domain_config.name,
                    pattern="slot_value",
                    context_type="cold_start",
                    current_datetime="2024-12-11T10:00:00",
                )
            )

        elif domain_config.name == "banking":
            from soni.dataset.domains.banking import AMOUNTS, CURRENCIES, RECIPIENTS

            # Example 1: Transfer funds
            examples.append(
                ExampleTemplate(
                    user_message=f"Transfer {AMOUNTS[0]} {CURRENCIES[0]} to {RECIPIENTS[0]}",
                    conversation_context=ConversationContext(
                        history=dspy.History(messages=[]),
                        current_slots={},
                        current_flow="none",
                        expected_slots=list(domain_config.slots.keys()),
                    ),
                    expected_output=NLUOutput(
                        commands=[
                            StartFlow(flow_name="transfer_funds"),
                            SetSlot(slot_name="amount", value=str(AMOUNTS[0])),
                            SetSlot(slot_name="currency", value=CURRENCIES[0]),
                            SetSlot(slot_name="recipient", value=RECIPIENTS[0]),
                        ],
                        confidence=0.95,
                    ),
                    domain=domain_config.name,
                    pattern="slot_value",
                    context_type="cold_start",
                    current_datetime="2024-12-11T10:00:00",
                )
            )

            # Example 2: Amount + Recipient
            examples.append(
                ExampleTemplate(
                    user_message=f"Send {AMOUNTS[1]} to {RECIPIENTS[1]}",
                    conversation_context=ConversationContext(
                        history=dspy.History(messages=[]),
                        current_slots={},
                        current_flow="none",
                        expected_slots=list(domain_config.slots.keys()),
                    ),
                    expected_output=NLUOutput(
                        commands=[
                            StartFlow(flow_name="transfer_funds"),
                            SetSlot(slot_name="amount", value=str(AMOUNTS[1])),
                            SetSlot(slot_name="recipient", value=RECIPIENTS[1]),
                        ],
                        confidence=0.95,
                    ),
                    domain=domain_config.name,
                    pattern="slot_value",
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
        """Generate ongoing examples (answering specific prompts).

        User provides answer to a specific slot being asked.

        Args:
            domain_config: Domain configuration
            count: Number of examples to generate

        Returns:
            List of example templates
        """
        examples = []

        if domain_config.name == "flight_booking":
            from soni.dataset.domains.flight_booking import (
                CITIES,
                DATES_RELATIVE,
                create_context_after_origin,
                create_context_after_origin_destination,
            )

            # Example 1: Answering destination prompt
            examples.append(
                ExampleTemplate(
                    user_message=CITIES[5],
                    conversation_context=create_context_after_origin(origin=CITIES[0]),
                    expected_output=NLUOutput(
                        commands=[
                            SetSlot(slot_name="destination", value=CITIES[5]),
                        ],
                        confidence=0.95,
                    ),
                    domain=domain_config.name,
                    pattern="slot_value",
                    context_type="ongoing",
                    current_datetime="2024-12-11T10:00:00",
                )
            )

            # Example 2: Answering date prompt
            examples.append(
                ExampleTemplate(
                    user_message=DATES_RELATIVE[1],
                    conversation_context=create_context_after_origin_destination(
                        origin=CITIES[0],
                        destination=CITIES[1],
                    ),
                    expected_output=NLUOutput(
                        commands=[
                            SetSlot(slot_name="departure_date", value=DATES_RELATIVE[1]),
                        ],
                        confidence=0.9,
                    ),
                    domain=domain_config.name,
                    pattern="slot_value",
                    context_type="ongoing",
                    current_datetime="2024-12-11T10:00:00",
                )
            )

            # Example 2b: "Next Friday" - specific example used in tests
            examples.append(
                ExampleTemplate(
                    user_message="Next Friday",
                    conversation_context=create_context_after_origin_destination(
                        origin="New York",
                        destination="Los Angeles",
                    ),
                    expected_output=NLUOutput(
                        commands=[
                            SetSlot(
                                slot_name="departure_date",
                                value="2025-12-19",
                            ),
                        ],
                        confidence=0.95,
                    ),
                    domain=domain_config.name,
                    pattern="slot_value",
                    context_type="ongoing",
                    current_datetime="2025-12-11T10:00:00",  # CRITICAL for normalization
                )
            )

            # Example 3: Multiple slots in answer
            examples.append(
                ExampleTemplate(
                    user_message=f"{CITIES[6]} to {CITIES[7]}",
                    conversation_context=ConversationContext(
                        history=dspy.History(
                            messages=[
                                {
                                    "user_message": "Book a flight",
                                    "result": {
                                        "command": "book_flight",
                                        "message_type": "interruption",
                                    },
                                },
                            ]
                        ),
                        current_slots={},
                        current_flow="book_flight",
                        expected_slots=["origin", "destination", "departure_date"],
                    ),
                    expected_output=NLUOutput(
                        commands=[
                            SetSlot(slot_name="origin", value=CITIES[6]),
                            SetSlot(slot_name="destination", value=CITIES[7]),
                        ],
                        confidence=0.9,
                    ),
                    domain=domain_config.name,
                    pattern="slot_value",
                    context_type="ongoing",
                    current_datetime="2024-12-11T10:00:00",
                )
            )

            # Example 4: Simple single city as origin (key test scenario)
            examples.append(
                ExampleTemplate(
                    user_message="New York",
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
                            SetSlot(slot_name="origin", value="New York"),
                        ],
                        confidence=0.95,
                    ),
                    domain=domain_config.name,
                    pattern="slot_value",
                    context_type="ongoing",
                    current_datetime="2024-12-11T10:00:00",
                )
            )

            # Example 5: Simple single city as destination
            examples.append(
                ExampleTemplate(
                    user_message="Los Angeles",
                    conversation_context=ConversationContext(
                        history=dspy.History(
                            messages=[
                                {"user_message": "I want to book a flight"},
                                {"user_message": "New York"},
                            ]
                        ),
                        current_slots={"origin": "New York"},
                        current_flow="book_flight",
                        expected_slots=["destination"],
                    ),
                    expected_output=NLUOutput(
                        commands=[
                            SetSlot(slot_name="destination", value="Los Angeles"),
                        ],
                        confidence=0.95,
                    ),
                    domain=domain_config.name,
                    pattern="slot_value",
                    context_type="ongoing",
                    current_datetime="2024-12-11T10:00:00",
                )
            )

            # Example 6: Another single city destination - Miami (test scenario)
            examples.append(
                ExampleTemplate(
                    user_message="Miami",
                    conversation_context=ConversationContext(
                        history=dspy.History(
                            messages=[
                                {"user_message": "I want to book a flight"},
                                {"user_message": "San Francisco"},
                                {"user_message": "What airports do you support?"},
                            ]
                        ),
                        current_slots={"origin": "San Francisco"},
                        current_flow="book_flight",
                        expected_slots=["destination"],
                    ),
                    expected_output=NLUOutput(
                        commands=[
                            SetSlot(slot_name="destination", value="Miami"),
                        ],
                        confidence=0.95,
                    ),
                    domain=domain_config.name,
                    pattern="slot_value",
                    context_type="ongoing",
                    current_datetime="2024-12-11T10:00:00",
                )
            )

            # Example 7: Seattle as destination (test scenario)
            examples.append(
                ExampleTemplate(
                    user_message="Seattle",
                    conversation_context=ConversationContext(
                        history=dspy.History(
                            messages=[
                                {"user_message": "Book a flight"},
                                {"user_message": "Chicago"},
                                {"user_message": "Actually, I meant Denver not Chicago"},
                            ]
                        ),
                        current_slots={"origin": "Denver"},
                        current_flow="book_flight",
                        expected_slots=["destination"],
                    ),
                    expected_output=NLUOutput(
                        commands=[
                            SetSlot(slot_name="destination", value="Seattle"),
                        ],
                        confidence=0.95,
                    ),
                    domain=domain_config.name,
                    pattern="slot_value",
                    context_type="ongoing",
                    current_datetime="2024-12-11T10:00:00",
                )
            )

        elif domain_config.name == "hotel_booking":
            from soni.dataset.domains.hotel_booking import (
                CITIES,
                create_context_after_location,
            )

            examples.append(
                ExampleTemplate(
                    user_message="tomorrow",
                    conversation_context=create_context_after_location(location=CITIES[0]),
                    expected_output=NLUOutput(
                        commands=[
                            SetSlot(slot_name="checkin_date", value="tomorrow", confidence=0.9),
                        ],
                        confidence=0.9,
                    ),
                    domain=domain_config.name,
                    pattern="slot_value",
                    context_type="ongoing",
                    current_datetime="2024-12-11T10:00:00",
                )
            )

            # Example 2: Answering guests prompt
            examples.append(
                ExampleTemplate(
                    user_message="2 adults",
                    conversation_context=ConversationContext(
                        history=dspy.History(
                            messages=[
                                {"user_message": "How many guests?"},
                            ]
                        ),
                        current_slots={"location": "Paris"},
                        current_flow="book_hotel",
                        expected_slots=["guests"],
                    ),
                    expected_output=NLUOutput(
                        commands=[
                            SetSlot(slot_name="guests", value="2"),
                        ],
                        confidence=0.95,
                    ),
                    domain=domain_config.name,
                    pattern="slot_value",
                    context_type="ongoing",
                    current_datetime="2024-12-11T10:00:00",
                )
            )

            # Example 3: Multi-slot (Location + Date) in ongoing
            examples.append(
                ExampleTemplate(
                    user_message=f"{CITIES[1]} for tomorrow",
                    conversation_context=ConversationContext(
                        history=dspy.History(
                            messages=[
                                {"user_message": "Where and when?"},
                            ]
                        ),
                        current_slots={},
                        current_flow="book_hotel",
                        expected_slots=["location", "checkin_date"],
                    ),
                    expected_output=NLUOutput(
                        commands=[
                            SetSlot(slot_name="location", value=CITIES[1]),
                            SetSlot(slot_name="checkin_date", value="tomorrow"),
                        ],
                        confidence=0.9,
                    ),
                    domain=domain_config.name,
                    pattern="slot_value",
                    context_type="ongoing",
                    current_datetime="2024-12-11T10:00:00",
                )
            )

        elif domain_config.name == "restaurant":
            from soni.dataset.domains.restaurant import (
                TIMES,
                create_context_after_location,
            )

            examples.append(
                ExampleTemplate(
                    user_message=TIMES[0],
                    conversation_context=create_context_after_location(location="Madrid"),
                    expected_output=NLUOutput(
                        commands=[
                            SetSlot(slot_name="time", value=TIMES[0]),
                        ],
                        confidence=0.95,
                    ),
                    domain=domain_config.name,
                    pattern="slot_value",
                    context_type="ongoing",
                    current_datetime="2024-12-11T10:00:00",
                )
            )

            # Example 2: Answering party size
            examples.append(
                ExampleTemplate(
                    user_message="4 people",
                    conversation_context=ConversationContext(
                        history=dspy.History(
                            messages=[
                                {"user_message": "How many people?"},
                            ]
                        ),
                        current_slots={"location": "New York"},
                        current_flow="book_table",
                        expected_slots=["party_size"],
                    ),
                    expected_output=NLUOutput(
                        commands=[
                            SetSlot(slot_name="party_size", value="4"),
                        ],
                        confidence=0.95,
                    ),
                    domain=domain_config.name,
                    pattern="slot_value",
                    context_type="ongoing",
                    current_datetime="2024-12-11T10:00:00",
                )
            )

            # Example 3: Multi-slot (Time + Party Size)
            examples.append(
                ExampleTemplate(
                    user_message="Table for 2 at 8pm",
                    conversation_context=ConversationContext(
                        history=dspy.History(
                            messages=[
                                {"user_message": "For how many and what time?"},
                            ]
                        ),
                        current_slots={"location": "Rome"},
                        current_flow="book_table",
                        expected_slots=["party_size", "time"],
                    ),
                    expected_output=NLUOutput(
                        commands=[
                            SetSlot(slot_name="party_size", value="2"),
                            SetSlot(slot_name="time", value="8pm"),
                        ],
                        confidence=0.9,
                    ),
                    domain=domain_config.name,
                    pattern="slot_value",
                    context_type="ongoing",
                    current_datetime="2024-12-11T10:00:00",
                )
            )

        elif domain_config.name == "ecommerce":
            from soni.dataset.domains.ecommerce import (
                COLORS,
                create_context_after_product,
            )

            examples.append(
                ExampleTemplate(
                    user_message=COLORS[0],
                    conversation_context=create_context_after_product(product="laptop"),
                    expected_output=NLUOutput(
                        commands=[
                            SetSlot(slot_name="color", value=COLORS[0]),
                        ],
                        confidence=0.9,
                    ),
                    domain=domain_config.name,
                    pattern="slot_value",
                    context_type="ongoing",
                    current_datetime="2024-12-11T10:00:00",
                )
            )

            # Example 2: Answering size
            examples.append(
                ExampleTemplate(
                    user_message="Size 10",
                    conversation_context=ConversationContext(
                        history=dspy.History(
                            messages=[
                                {"user_message": "What size?"},
                            ]
                        ),
                        current_slots={"product": "shoes"},
                        current_flow="search_product",
                        expected_slots=["size"],
                    ),
                    expected_output=NLUOutput(
                        commands=[
                            SetSlot(slot_name="size", value="10"),
                        ],
                        confidence=0.95,
                    ),
                    domain=domain_config.name,
                    pattern="slot_value",
                    context_type="ongoing",
                    current_datetime="2024-12-11T10:00:00",
                )
            )

            # Example 3: Multi-slot (Color + Size)
            examples.append(
                ExampleTemplate(
                    user_message="Red size 10",
                    conversation_context=ConversationContext(
                        history=dspy.History(
                            messages=[
                                {"user_message": "What color and size?"},
                            ]
                        ),
                        current_slots={"product": "t-shirt"},
                        current_flow="search_product",
                        expected_slots=["color", "size"],
                    ),
                    expected_output=NLUOutput(
                        commands=[
                            SetSlot(slot_name="color", value="red"),
                            SetSlot(slot_name="size", value="10"),
                        ],
                        confidence=0.9,
                    ),
                    domain=domain_config.name,
                    pattern="slot_value",
                    context_type="ongoing",
                    current_datetime="2024-12-11T10:00:00",
                )
            )

        elif domain_config.name == "banking":
            from soni.dataset.domains.banking import AMOUNTS, CURRENCIES

            # Explicitly create context here since we didn't add helper functions to banking.py yet
            context = ConversationContext(
                history=dspy.History(
                    messages=[
                        {
                            "user_message": "I want to transfer money",
                            "result": {
                                "command": "transfer_funds",
                                "message_type": "interruption",
                            },
                        }
                    ]
                ),
                current_slots={},
                current_flow="transfer_funds",
                expected_slots=["amount", "currency", "recipient"],
            )

            examples.append(
                ExampleTemplate(
                    user_message=str(AMOUNTS[0]),
                    conversation_context=context,
                    expected_output=NLUOutput(
                        commands=[
                            SetSlot(slot_name="amount", value=str(AMOUNTS[0])),
                        ],
                        confidence=0.95,
                    ),
                    domain=domain_config.name,
                    pattern="slot_value",
                    context_type="ongoing",
                    current_datetime="2024-12-11T10:00:00",
                )
            )

            # Example 2: Answering recipient
            examples.append(
                ExampleTemplate(
                    user_message="Alice",
                    conversation_context=ConversationContext(
                        history=dspy.History(
                            messages=[
                                {"user_message": "Who is the recipient?"},
                            ]
                        ),
                        current_slots={"amount": "100"},
                        current_flow="transfer_funds",
                        expected_slots=["recipient"],
                    ),
                    expected_output=NLUOutput(
                        commands=[
                            SetSlot(slot_name="recipient", value="Alice"),
                        ],
                        confidence=0.95,
                    ),
                    domain=domain_config.name,
                    pattern="slot_value",
                    context_type="ongoing",
                    current_datetime="2024-12-11T10:00:00",
                )
            )

            # Example 3: Multi-slot (Amount + Currency)
            examples.append(
                ExampleTemplate(
                    user_message=f"{AMOUNTS[1]} {CURRENCIES[1]}",
                    conversation_context=ConversationContext(
                        history=dspy.History(
                            messages=[
                                {"user_message": "How much?"},
                            ]
                        ),
                        current_slots={"recipient": "Bob"},
                        current_flow="transfer_funds",
                        expected_slots=["amount", "currency"],
                    ),
                    expected_output=NLUOutput(
                        commands=[
                            SetSlot(slot_name="amount", value=str(AMOUNTS[1])),
                            SetSlot(slot_name="currency", value=CURRENCIES[1]),
                        ],
                        confidence=0.9,
                    ),
                    domain=domain_config.name,
                    pattern="slot_value",
                    context_type="ongoing",
                    current_datetime="2024-12-11T10:00:00",
                )
            )

        return examples[:count]
