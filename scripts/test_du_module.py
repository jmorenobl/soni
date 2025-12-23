#!/usr/bin/env python3
"""Test script for the Dialogue Understanding (DU) module.

This script demonstrates how the DU module works by testing it against
various user messages and showing the extracted commands.
"""

import asyncio
import logging

import dspy

# Configure minimal logging
logging.basicConfig(level=logging.INFO, format="%(levelname)s: %(message)s")

# Suppress verbose DSPy logs
logging.getLogger("httpx").setLevel(logging.WARNING)
logging.getLogger("dspy").setLevel(logging.WARNING)


async def test_du_module() -> None:
    """Test the DU module with various user messages."""
    from soni.du.models import (
        CommandInfo,
        DialogueContext,
        FlowInfo,
        SlotDefinition,
        SlotValue,
    )
    from soni.du.modules import SoniDU
    from soni.du.slot_extractor import SlotExtractionInput, SlotExtractor

    # Configure DSPy with a cheap/fast model for testing
    lm = dspy.LM("openai/gpt-4o-mini", temperature=0.0)
    dspy.configure(lm=lm)

    print("\n" + "=" * 60)
    print("Dialogue Understanding (DU) Module Test")
    print("=" * 60)

    # 1. Create the modules
    print("\n📦 Creating SoniDU and SlotExtractor modules...")
    du = SoniDU(use_cot=True)  # With Chain of Thought reasoning
    slot_extractor = SlotExtractor(use_cot=False)  # Simpler, faster

    # 2. Build a test context (simulating the banking domain)
    context = DialogueContext(
        available_flows=[
            FlowInfo(
                name="transfer_funds",
                description="Transfer money between accounts",
                trigger_intents=["transfer money", "send funds", "make a transfer"],
            ),
            FlowInfo(
                name="check_balance",
                description="Check account balance",
                trigger_intents=["check my balance", "how much money do I have"],
            ),
        ],
        available_commands=[
            CommandInfo(
                command_type="start_flow",
                description="Start a new flow/task",
                required_fields=["flow"],
                example="I want to transfer money",
            ),
            CommandInfo(
                command_type="set_slot",
                description="Set a slot value when user provides information",
                required_fields=["slot", "value"],
                example="100 euros",
            ),
            CommandInfo(
                command_type="chitchat",
                description="Handle off-topic conversation or greetings",
                required_fields=[],
                example="Hello!",
            ),
            CommandInfo(
                command_type="affirm",
                description="User confirms/agrees",
                required_fields=[],
                example="Yes, that's correct",
            ),
            CommandInfo(
                command_type="deny",
                description="User declines/disagrees",
                required_fields=[],
                example="No, that's wrong",
            ),
        ],
        active_flow=None,
        flow_slots=[],
        current_slots=[],
        expected_slot=None,
        conversation_state="idle",
    )

    # Define test cases
    test_cases = [
        # Case 1: Intent detection (start a flow)
        {
            "description": "Detect intent to start transfer flow",
            "message": "I want to transfer 100 euros to my mom",
            "context": context,
            "history": [],
        },
        # Case 2: Chitchat (no flow active)
        {
            "description": "Handle greeting (chitchat)",
            "message": "Hello! How are you today?",
            "context": context,
            "history": [],
        },
        # Case 3: Slot filling (during active flow)
        {
            "description": "Fill expected slot during active flow",
            "message": "100 euros",
            "context": DialogueContext(
                available_flows=context.available_flows,
                available_commands=context.available_commands,
                active_flow="transfer_funds",
                flow_slots=[
                    SlotDefinition(
                        name="amount",
                        slot_type="currency",
                        description="Amount to transfer",
                        required=True,
                    ),
                    SlotDefinition(
                        name="beneficiary_name",
                        slot_type="string",
                        description="Recipient's name",
                        required=True,
                    ),
                ],
                current_slots=[],
                expected_slot="amount",
                conversation_state="collecting",
            ),
            "history": [],
        },
        # Case 4: Confirmation
        {
            "description": "Affirm confirmation",
            "message": "Yes, that looks correct",
            "context": DialogueContext(
                available_flows=context.available_flows,
                available_commands=context.available_commands,
                active_flow="transfer_funds",
                flow_slots=[],
                current_slots=[
                    SlotValue(name="amount", value="100", expected_type="currency"),
                    SlotValue(name="beneficiary_name", value="mom", expected_type="string"),
                ],
                expected_slot=None,
                conversation_state="confirming",
            ),
            "history": [],
        },
    ]

    # Run test cases for SoniDU (Pass 1)
    print("\n" + "-" * 60)
    print("🧠 Testing SoniDU (Pass 1 - Intent & Command Detection)")
    print("-" * 60)

    for i, test in enumerate(test_cases, 1):
        print(f"\n{'=' * 50}")
        print(f"Test {i}: {test['description']}")
        print(f"{'=' * 50}")
        print(f'📝 User message: "{test["message"]}"')
        print(f"🔄 Conversation state: {test['context'].conversation_state}")
        if test["context"].active_flow:
            print(f"📂 Active flow: {test['context'].active_flow}")
        if test["context"].expected_slot:
            print(f"❓ Expected slot: {test['context'].expected_slot}")

        try:
            # Call the DU module
            result = await du.acall(
                user_message=test["message"],
                context=test["context"],
                history=test["history"],
            )

            print(f"\n✅ Result (confidence: {result.confidence:.2f}):")
            print(f"   Commands ({len(result.commands)}):")
            for cmd in result.commands:
                print(f"   - {cmd}")

        except Exception as e:
            print(f"\n❌ Error: {e}")

    # Test SlotExtractor (Pass 2)
    print("\n" + "-" * 60)
    print("🎯 Testing SlotExtractor (Pass 2 - Slot Value Extraction)")
    print("-" * 60)

    slot_definitions = [
        SlotExtractionInput(
            name="amount",
            slot_type="currency",
            description="Amount to transfer in euros",
            examples=["100", "50.50", "1000"],
        ),
        SlotExtractionInput(
            name="beneficiary_name",
            slot_type="string",
            description="Name of the person to send money to",
            examples=["John", "my mom", "Sarah"],
        ),
        SlotExtractionInput(
            name="iban",
            slot_type="string",
            description="IBAN of the destination account",
            examples=["ES1234567890123456789012", "DE89370400440532013000"],
        ),
    ]

    slot_test_messages = [
        "I want to send 250 euros to Maria",
        "Transfer money to account ES7921000813610123456789",
        "Send 50 bucks to my brother",
        "I need to make a transfer",  # No slots
    ]

    for msg in slot_test_messages:
        print(f'\n📝 Message: "{msg}"')

        try:
            slots = await slot_extractor.acall(
                user_message=msg,
                slot_definitions=slot_definitions,
            )

            if slots:
                print("   ✅ Extracted slots:")
                for slot in slots:
                    print(f"      - {slot}")
            else:
                print("   ℹ️  No slots extracted")

        except Exception as e:
            print(f"   ❌ Error: {e}")

    print("\n" + "=" * 60)
    print("Test completed!")
    print("=" * 60)


if __name__ == "__main__":
    asyncio.run(test_du_module())
