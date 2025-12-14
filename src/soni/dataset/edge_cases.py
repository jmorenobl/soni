"""Edge case examples for improving NLU robustness.

This module provides boundary examples for difficult classification cases:
- DIGRESSION vs INTERRUPTION boundaries
- CORRECTION vs MODIFICATION boundaries
- Ambiguous CONFIRMATION responses
- Compound intents

These examples are critical for teaching the NLU system to distinguish
between semantically similar but functionally different user intents.
"""

import dspy

from soni.dataset.base import ConversationContext, ExampleTemplate
from soni.du.models import MessageType, NLUOutput, SlotValue

# =============================================================================
# DIGRESSION vs INTERRUPTION Boundary Examples
# =============================================================================


def generate_digression_vs_interruption_edges() -> list[ExampleTemplate]:
    """Generate boundary examples between DIGRESSION and INTERRUPTION.

    Key distinction:
    - INTERRUPTION: User wants to start a DIFFERENT flow (available in context)
    - DIGRESSION: User asks a question but wants to STAY in current flow

    Returns:
        List of edge case examples.
    """
    examples = []

    # =========================================================================
    # INTERRUPTION cases - User wants to switch to a different available flow
    # =========================================================================

    # Case 1: Asking about balance during transfer → INTERRUPTION
    # "What's my balance?" semantically matches "check_balance" flow
    examples.append(
        ExampleTemplate(
            user_message="What's my balance?",
            conversation_context=ConversationContext(
                history=dspy.History(
                    messages=[
                        {"role": "user", "content": "I want to transfer money"},
                        {"role": "assistant", "content": "How much would you like to transfer?"},
                    ]
                ),
                current_slots={},
                current_flow="transfer_funds",
                expected_slots=["amount"],
                conversation_state="waiting_for_slot",
            ),
            expected_output=NLUOutput(
                message_type=MessageType.INTERRUPTION,
                command="check_balance",
                slots=[],
                confidence=0.90,
            ),
            domain="banking",
            pattern="interruption",
            context_type="ongoing",
            current_datetime="2024-12-11T10:00:00",
        )
    )

    # Case 2: "How much do I have?" - implicit balance check
    examples.append(
        ExampleTemplate(
            user_message="How much do I have?",
            conversation_context=ConversationContext(
                history=dspy.History(
                    messages=[
                        {"role": "user", "content": "Send money to mom"},
                        {"role": "assistant", "content": "How much?"},
                    ]
                ),
                current_slots={"recipient": "mom"},
                current_flow="transfer_funds",
                expected_slots=["amount"],
                conversation_state="waiting_for_slot",
            ),
            expected_output=NLUOutput(
                message_type=MessageType.INTERRUPTION,
                command="check_balance",
                slots=[],
                confidence=0.90,
            ),
            domain="banking",
            pattern="interruption",
            context_type="ongoing",
            current_datetime="2024-12-11T10:00:00",
        )
    )

    # Case 3: "First, check my account" - explicit flow switch
    examples.append(
        ExampleTemplate(
            user_message="First, check my account",
            conversation_context=ConversationContext(
                history=dspy.History(
                    messages=[
                        {"role": "user", "content": "I need to block my card"},
                        {"role": "assistant", "content": "What are the last 4 digits?"},
                    ]
                ),
                current_slots={},
                current_flow="block_card",
                expected_slots=["card_last_4"],
                conversation_state="waiting_for_slot",
            ),
            expected_output=NLUOutput(
                message_type=MessageType.INTERRUPTION,
                command="check_balance",
                slots=[],
                confidence=0.85,
            ),
            domain="banking",
            pattern="interruption",
            context_type="ongoing",
            current_datetime="2024-12-11T10:00:00",
        )
    )

    # Case 4: "Let me see my funds first"
    examples.append(
        ExampleTemplate(
            user_message="Let me see my funds first",
            conversation_context=ConversationContext(
                history=dspy.History(
                    messages=[
                        {"role": "user", "content": "Transfer 500 to dad"},
                        {"role": "assistant", "content": "In which currency?"},
                    ]
                ),
                current_slots={"amount": "500", "recipient": "dad"},
                current_flow="transfer_funds",
                expected_slots=["currency"],
                conversation_state="waiting_for_slot",
            ),
            expected_output=NLUOutput(
                message_type=MessageType.INTERRUPTION,
                command="check_balance",
                slots=[],
                confidence=0.88,
            ),
            domain="banking",
            pattern="interruption",
            context_type="ongoing",
            current_datetime="2024-12-11T10:00:00",
        )
    )

    # Case 5: Asking about booking during check → switch to booking
    examples.append(
        ExampleTemplate(
            user_message="Actually, I want to book a flight",
            conversation_context=ConversationContext(
                history=dspy.History(
                    messages=[
                        {"role": "user", "content": "Check my booking status"},
                    ]
                ),
                current_slots={},
                current_flow="check_booking",
                expected_slots=["booking_reference"],
            ),
            expected_output=NLUOutput(
                message_type=MessageType.INTERRUPTION,
                command="book_flight",
                slots=[],
                confidence=0.90,
            ),
            domain="flight_booking",
            pattern="interruption",
            context_type="ongoing",
            current_datetime="2024-12-11T10:00:00",
        )
    )

    # =========================================================================
    # DIGRESSION cases - User asks question but wants to stay in current flow
    # =========================================================================

    # Case 6: Asking about fees during transfer → DIGRESSION (no fee_info flow)
    examples.append(
        ExampleTemplate(
            user_message="What are the fees?",
            conversation_context=ConversationContext(
                history=dspy.History(
                    messages=[
                        {"role": "user", "content": "Transfer 100 to Alice"},
                    ]
                ),
                current_slots={"amount": "100", "recipient": "Alice"},
                current_flow="transfer_funds",
                expected_slots=["currency"],
            ),
            expected_output=NLUOutput(
                message_type=MessageType.DIGRESSION,
                command="transfer_funds",  # Stay in current flow
                slots=[],
                confidence=0.85,
            ),
            domain="banking",
            pattern="digression",
            context_type="ongoing",
            current_datetime="2024-12-11T10:00:00",
        )
    )

    # Case 7: "Is this secure?" - general question, not a flow
    examples.append(
        ExampleTemplate(
            user_message="Is this secure?",
            conversation_context=ConversationContext(
                history=dspy.History(
                    messages=[
                        {"role": "user", "content": "Send 1000 to Bob"},
                    ]
                ),
                current_slots={"amount": "1000", "recipient": "Bob"},
                current_flow="transfer_funds",
                expected_slots=["currency"],
            ),
            expected_output=NLUOutput(
                message_type=MessageType.DIGRESSION,
                command="transfer_funds",
                slots=[],
                confidence=0.85,
            ),
            domain="banking",
            pattern="digression",
            context_type="ongoing",
            current_datetime="2024-12-11T10:00:00",
        )
    )

    # Case 8: "Do you have direct flights?" - question about options
    examples.append(
        ExampleTemplate(
            user_message="Do you have direct flights?",
            conversation_context=ConversationContext(
                history=dspy.History(
                    messages=[
                        {"role": "user", "content": "Book a flight to Paris"},
                    ]
                ),
                current_slots={"destination": "Paris"},
                current_flow="book_flight",
                expected_slots=["origin", "departure_date"],
            ),
            expected_output=NLUOutput(
                message_type=MessageType.DIGRESSION,
                command="book_flight",
                slots=[],
                confidence=0.85,
            ),
            domain="flight_booking",
            pattern="digression",
            context_type="ongoing",
            current_datetime="2024-12-11T10:00:00",
        )
    )

    # Case 9: "What airlines fly that route?" - information question
    examples.append(
        ExampleTemplate(
            user_message="What airlines fly that route?",
            conversation_context=ConversationContext(
                history=dspy.History(
                    messages=[
                        {"role": "user", "content": "Flight from Madrid to Barcelona"},
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
            domain="flight_booking",
            pattern="digression",
            context_type="ongoing",
            current_datetime="2024-12-11T10:00:00",
        )
    )

    # Case 10: "How long will the transfer take?" - info about current flow
    examples.append(
        ExampleTemplate(
            user_message="How long will the transfer take?",
            conversation_context=ConversationContext(
                history=dspy.History(
                    messages=[
                        {"role": "user", "content": "Transfer 50 EUR to Charlie"},
                    ]
                ),
                current_slots={"amount": "50", "currency": "EUR", "recipient": "Charlie"},
                current_flow="transfer_funds",
                expected_slots=[],
                conversation_state="confirming",
            ),
            expected_output=NLUOutput(
                message_type=MessageType.DIGRESSION,
                command="transfer_funds",
                slots=[],
                confidence=0.85,
            ),
            domain="banking",
            pattern="digression",
            context_type="ongoing",
            current_datetime="2024-12-11T10:00:00",
        )
    )

    return examples


# =============================================================================
# CORRECTION vs MODIFICATION Boundary Examples
# =============================================================================


def generate_correction_vs_modification_edges() -> list[ExampleTemplate]:
    """Generate boundary examples between CORRECTION and MODIFICATION.

    Key distinction:
    - CORRECTION: Reactive - user realizes they made a mistake
    - MODIFICATION: Proactive - user explicitly requests a change

    Returns:
        List of edge case examples.
    """
    examples = []

    # =========================================================================
    # CORRECTION cases - Reactive fixes
    # =========================================================================

    # Case 1: "No, I meant X not Y" - classic correction pattern
    examples.append(
        ExampleTemplate(
            user_message="No, I meant Denver not Chicago",
            conversation_context=ConversationContext(
                history=dspy.History(
                    messages=[
                        {"role": "user", "content": "Book a flight"},
                        {"role": "user", "content": "Chicago"},
                    ]
                ),
                current_slots={"origin": "Chicago"},
                current_flow="book_flight",
                expected_slots=["destination"],
            ),
            expected_output=NLUOutput(
                message_type=MessageType.CORRECTION,
                command="book_flight",
                slots=[SlotValue(name="origin", value="Denver", confidence=0.95)],
                confidence=0.95,
            ),
            domain="flight_booking",
            pattern="correction",
            context_type="ongoing",
            current_datetime="2024-12-11T10:00:00",
        )
    )

    # Case 2: "Wait, I said 50 not 500" - numeric correction
    examples.append(
        ExampleTemplate(
            user_message="Wait, I said 50 not 500",
            conversation_context=ConversationContext(
                history=dspy.History(
                    messages=[
                        {"role": "user", "content": "Transfer 500 to mom"},
                    ]
                ),
                current_slots={"amount": "500", "recipient": "mom"},
                current_flow="transfer_funds",
                expected_slots=["currency"],
            ),
            expected_output=NLUOutput(
                message_type=MessageType.CORRECTION,
                command="transfer_funds",
                slots=[SlotValue(name="amount", value="50", confidence=0.95)],
                confidence=0.95,
            ),
            domain="banking",
            pattern="correction",
            context_type="ongoing",
            current_datetime="2024-12-11T10:00:00",
        )
    )

    # Case 3: "Sorry, I meant euros" - implicit correction
    examples.append(
        ExampleTemplate(
            user_message="Sorry, I meant euros",
            conversation_context=ConversationContext(
                history=dspy.History(
                    messages=[
                        {"role": "user", "content": "Transfer 100 dollars"},
                    ]
                ),
                current_slots={"amount": "100", "currency": "dollars"},
                current_flow="transfer_funds",
                expected_slots=["recipient"],
            ),
            expected_output=NLUOutput(
                message_type=MessageType.CORRECTION,
                command="transfer_funds",
                slots=[SlotValue(name="currency", value="euros", confidence=0.90)],
                confidence=0.90,
            ),
            domain="banking",
            pattern="correction",
            context_type="ongoing",
            current_datetime="2024-12-11T10:00:00",
        )
    )

    # =========================================================================
    # MODIFICATION cases - Proactive changes
    # =========================================================================

    # Case 4: "Change the destination" - explicit modification request
    examples.append(
        ExampleTemplate(
            user_message="Change the destination",
            conversation_context=ConversationContext(
                history=dspy.History(
                    messages=[
                        {"role": "user", "content": "Book flight to Paris"},
                    ]
                ),
                current_slots={"destination": "Paris"},
                current_flow="book_flight",
                expected_slots=["origin", "departure_date"],
                conversation_state="confirming",
            ),
            expected_output=NLUOutput(
                message_type=MessageType.MODIFICATION,
                command="book_flight",
                slots=[],  # No new value provided yet
                confidence=0.90,
            ),
            domain="flight_booking",
            pattern="modification",
            context_type="ongoing",
            current_datetime="2024-12-11T10:00:00",
        )
    )

    # Case 5: "No, change the destination to London" - modification with value
    examples.append(
        ExampleTemplate(
            user_message="No, change the destination to London",
            conversation_context=ConversationContext(
                history=dspy.History(
                    messages=[
                        {"role": "user", "content": "Book flight to Paris"},
                        {
                            "role": "assistant",
                            "content": "Confirm: Flight to Paris, departing tomorrow?",
                        },
                    ]
                ),
                current_slots={"destination": "Paris", "departure_date": "tomorrow"},
                current_flow="book_flight",
                expected_slots=[],
                conversation_state="confirming",
            ),
            expected_output=NLUOutput(
                message_type=MessageType.MODIFICATION,
                command="book_flight",
                slots=[SlotValue(name="destination", value="London", confidence=0.95)],
                confirmation_value=False,
                confidence=0.95,
            ),
            domain="flight_booking",
            pattern="modification",
            context_type="ongoing",
            current_datetime="2024-12-11T10:00:00",
        )
    )

    # Case 6: "Can I update the amount?" - question-form modification
    examples.append(
        ExampleTemplate(
            user_message="Can I update the amount?",
            conversation_context=ConversationContext(
                history=dspy.History(
                    messages=[
                        {"role": "user", "content": "Transfer 100 to mom"},
                    ]
                ),
                current_slots={"amount": "100", "recipient": "mom"},
                current_flow="transfer_funds",
                expected_slots=["currency"],
            ),
            expected_output=NLUOutput(
                message_type=MessageType.MODIFICATION,
                command="transfer_funds",
                slots=[],
                confidence=0.85,
            ),
            domain="banking",
            pattern="modification",
            context_type="ongoing",
            current_datetime="2024-12-11T10:00:00",
        )
    )

    return examples


# =============================================================================
# Ambiguous CONFIRMATION Examples
# =============================================================================


def generate_confirmation_ambiguous_edges() -> list[ExampleTemplate]:
    """Generate examples for unclear confirmation responses.

    These are cases where the user's response is ambiguous and should
    result in confirmation_value=None to trigger re-prompting.

    Returns:
        List of edge case examples.
    """
    examples = []

    ambiguous_responses = [
        ("hmm", 0.65),
        ("I guess", 0.70),
        ("maybe", 0.65),
        ("I'm not sure", 0.60),
        ("let me think", 0.60),
        ("probably", 0.70),
        ("um...", 0.55),
        ("well...", 0.60),
        ("I don't know", 0.55),
        ("if you say so", 0.70),
        ("kind of", 0.65),
        ("perhaps", 0.65),
        ("hmm, I'm not sure", 0.60),
        ("what were the details again?", 0.50),
        ("can you repeat that?", 0.50),
    ]

    for response, confidence in ambiguous_responses:
        examples.append(
            ExampleTemplate(
                user_message=response,
                conversation_context=ConversationContext(
                    history=dspy.History(
                        messages=[
                            {"role": "user", "content": "Book flight to Paris tomorrow"},
                            {
                                "role": "assistant",
                                "content": "Confirm: Flight to Paris, departing tomorrow?",
                            },
                        ]
                    ),
                    current_slots={
                        "destination": "Paris",
                        "departure_date": "tomorrow",
                    },
                    current_flow="book_flight",
                    expected_slots=[],
                    conversation_state="confirming",
                ),
                expected_output=NLUOutput(
                    message_type=MessageType.CONFIRMATION,
                    command="book_flight",
                    slots=[],
                    confidence=confidence,
                    confirmation_value=None,  # CRITICAL: Ambiguous = None
                ),
                domain="flight_booking",
                pattern="confirmation",
                context_type="ongoing",
                current_datetime="2024-12-11T10:00:00",
            )
        )

    # Add a few clear confirmations for contrast during training
    # Clear YES
    examples.append(
        ExampleTemplate(
            user_message="Yes, that's correct",
            conversation_context=ConversationContext(
                history=dspy.History(
                    messages=[
                        {"role": "user", "content": "Transfer 100 to mom"},
                        {
                            "role": "assistant",
                            "content": "Confirm: Send $100 to mom?",
                        },
                    ]
                ),
                current_slots={"amount": "100", "recipient": "mom"},
                current_flow="transfer_funds",
                expected_slots=[],
                conversation_state="confirming",
            ),
            expected_output=NLUOutput(
                message_type=MessageType.CONFIRMATION,
                command="transfer_funds",
                slots=[],
                confidence=0.95,
                confirmation_value=True,
            ),
            domain="banking",
            pattern="confirmation",
            context_type="ongoing",
            current_datetime="2024-12-11T10:00:00",
        )
    )

    # Clear NO
    examples.append(
        ExampleTemplate(
            user_message="No, that's wrong",
            conversation_context=ConversationContext(
                history=dspy.History(
                    messages=[
                        {"role": "user", "content": "Transfer 100 to mom"},
                        {
                            "role": "assistant",
                            "content": "Confirm: Send $100 to mom?",
                        },
                    ]
                ),
                current_slots={"amount": "100", "recipient": "mom"},
                current_flow="transfer_funds",
                expected_slots=[],
                conversation_state="confirming",
            ),
            expected_output=NLUOutput(
                message_type=MessageType.CONFIRMATION,
                command="transfer_funds",
                slots=[],
                confidence=0.95,
                confirmation_value=False,
            ),
            domain="banking",
            pattern="confirmation",
            context_type="ongoing",
            current_datetime="2024-12-11T10:00:00",
        )
    )

    return examples


# =============================================================================
# Compound Intent Examples (for robustness)
# =============================================================================


def generate_compound_intent_examples() -> list[ExampleTemplate]:
    """Generate examples with multiple intents in one message.

    These teach the NLU to prioritize the primary intent.

    Returns:
        List of edge case examples.
    """
    examples = []

    # Case 1: Two actions - prioritize first
    examples.append(
        ExampleTemplate(
            user_message="Book a flight and also check hotel prices",
            conversation_context=ConversationContext(
                history=dspy.History(messages=[]),
                current_slots={},
                current_flow="none",
                expected_slots=[],
            ),
            expected_output=NLUOutput(
                message_type=MessageType.INTERRUPTION,
                command="book_flight",  # Primary intent
                slots=[],
                confidence=0.85,
            ),
            domain="flight_booking",
            pattern="interruption",
            context_type="cold_start",
            current_datetime="2024-12-11T10:00:00",
        )
    )

    # Case 2: Action with question - prioritize action
    examples.append(
        ExampleTemplate(
            user_message="Transfer 100 to mom, is that safe?",
            conversation_context=ConversationContext(
                history=dspy.History(messages=[]),
                current_slots={},
                current_flow="none",
                expected_slots=[],
            ),
            expected_output=NLUOutput(
                message_type=MessageType.INTERRUPTION,
                command="transfer_funds",
                slots=[
                    SlotValue(name="amount", value="100", confidence=0.95),
                    SlotValue(name="recipient", value="mom", confidence=0.95),
                ],
                confidence=0.90,
            ),
            domain="banking",
            pattern="interruption",
            context_type="cold_start",
            current_datetime="2024-12-11T10:00:00",
        )
    )

    return examples


# =============================================================================
# Main function to get all edge cases
# =============================================================================


def get_all_edge_cases() -> list[ExampleTemplate]:
    """Get all edge case examples combined.

    Returns:
        Complete list of all edge case examples.
    """
    return (
        generate_digression_vs_interruption_edges()
        + generate_correction_vs_modification_edges()
        + generate_confirmation_ambiguous_edges()
        + generate_compound_intent_examples()
    )
