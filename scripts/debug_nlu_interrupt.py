#!/usr/bin/env python
"""Debug script to see what NLU emits during an interrupt scenario.

Simulates the exact conversation flow to diagnose the bug.
"""

import asyncio
import logging

import dspy

from soni.config.loader import ConfigLoader
from soni.core.commands import StartFlow, parse_command
from soni.core.state import create_empty_dialogue_state
from soni.core.types import RuntimeContext
from soni.du.modules import SoniDU
from soni.du.service import NLUService, build_du_context
from soni.du.slot_extractor import SlotExtractor
from soni.flow.manager import FlowManager

# Enable logging
logging.basicConfig(level=logging.INFO, format="%(name)s - %(message)s")


async def main():
    # Load config
    config = ConfigLoader.load("examples/banking/domain")

    # Setup DSPy
    dspy.configure(lm=dspy.LM("openai/gpt-4o-mini"))

    # Create components
    du = SoniDU()
    slot_extractor = SlotExtractor()
    flow_manager = FlowManager()

    # Create a mock action handler
    class MockActionHandler:
        async def execute(self, action_name: str, inputs: dict):
            return {}

    # Create runtime context
    runtime_ctx = RuntimeContext(
        config=config,
        flow_manager=flow_manager,
        action_handler=MockActionHandler(),
        du=du,
        slot_extractor=slot_extractor,
    )

    # Simulate state: in transfer flow, waiting for amount slot
    state = create_empty_dialogue_state()

    # Push transfer flow to stack (simulating flow started)
    flow_id, delta = flow_manager.push_flow(state, "transfer_funds")
    if delta.flow_stack:
        state["flow_stack"] = delta.flow_stack
    if delta.flow_slots:
        state["flow_slots"] = delta.flow_slots

    # Simulate already collected slots
    state["flow_slots"][flow_id]["beneficiary_name"] = "mom"
    state["flow_slots"][flow_id]["iban"] = "353454"

    # Set waiting for slot (like collect node does)
    state["waiting_for_slot"] = "amount"

    # Create NLU service
    nlu_service = NLUService(du, slot_extractor)

    # Test message - the one that should trigger check_balance
    test_message = "how much do I have?"

    print("=" * 60)
    print(f"Test message: '{test_message}'")
    print("Active flow: transfer_funds")
    print("Waiting for slot: amount")
    print(f"Current slots: {state['flow_slots'][flow_id]}")
    print("=" * 60)

    # Build context to see what NLU receives
    du_context = build_du_context(state, runtime_ctx)
    print(f"Conversation state: {du_context.conversation_state}")
    print(f"Available flows: {[f.name for f in du_context.available_flows]}")
    print(f"Expected slot: {du_context.expected_slot}")
    print("=" * 60)

    # Process message (simulates what RuntimeLoop does)
    commands = await nlu_service.process_message(test_message, state, runtime_ctx)

    print(f"\n1. NLU emitted {len(commands)} commands:")
    for cmd in commands:
        if hasattr(cmd, "model_dump"):
            print(f"   - {cmd.model_dump()}")
        else:
            print(f"   - {cmd}")

    # Serialize commands (like RuntimeLoop does)
    serialized = nlu_service.serialize_commands(commands)
    print("\n2. Serialized commands (what goes into resume_payload):")
    for s in serialized:
        print(f"   - {s}")

    # Deserialize commands (like collect_node does)
    print("\n3. Deserialized commands (what collect_node sees):")
    deserialized = [parse_command(cmd) for cmd in serialized]
    for cmd in deserialized:
        print(f"   - {cmd} (type: {type(cmd).__name__})")
        print(f"     isinstance(StartFlow): {isinstance(cmd, StartFlow)}")

    # Check StartFlow identity
    print("\n4. StartFlow class check:")
    from soni.core.commands import StartFlow as LocalStartFlow

    print(f"   StartFlow id: {id(StartFlow)}")
    print(f"   LocalStartFlow id: {id(LocalStartFlow)}")
    print(f"   Same class: {StartFlow is LocalStartFlow}")


if __name__ == "__main__":
    asyncio.run(main())
