"""UnderstandNode - processes user input through NLU and updates dialogue state.

## How Understand Node Works

The understand node is the **NLU gateway** in Soni's dialogue management pipeline.
It transforms raw user input into structured commands that the Dialogue Manager
can execute deterministically.

## Two-Pass NLU Architecture

This module implements a two-pass NLU system:

**Pass 1 (Intent Detection):**
- Runs SoniDU to detect intent and generate commands
- Does NOT receive slot definitions (no context overload)
- Output: StartFlow, SetSlot (for active flows), etc.

**Pass 2 (Slot Extraction) - only if StartFlow detected:**
- Runs SlotExtractor with flow-specific slot definitions
- Extracts entities mentioned in the same message
- Output: SetSlot commands merged with Pass 1 results

```
User: "Transfer 100€ to my mom"
        |
        v
  Pass 1: Intent Detection
  Output: [StartFlow("transfer_funds")]
        |
        v
  Pass 2: Slot Extraction (with transfer_funds slots)
  Output: [SetSlot("beneficiary_name", "my mom"), SetSlot("amount", "100")]
        |
        v
  Merged: [StartFlow, SetSlot, SetSlot]
```

## Integration Points

- **Upstream**: Entry point for each dialogue turn (from RuntimeLoop)
- **Downstream**: Routes to `execute_node` which dispatches to flows
- **Dependencies**:
  - `DUProtocol` (NLU provider - typically SoniDU with DSPy)
  - `SlotExtractor` (Pass 2 extraction)
  - `FlowManager` (state mutations)
  - `SoniConfig` (flow definitions)
"""

import logging
from typing import Any

from langchain_core.runnables import RunnableConfig

from soni.core.commands import AffirmConfirmation, DenyConfirmation, SetSlot, StartFlow
from soni.core.constants import FlowState
from soni.core.types import (
    ConfigProtocol,
    DialogueState,
    RuntimeContext,
    get_runtime_context,
)
from soni.du.models import CommandInfo, DialogueContext, FlowInfo, SlotValue
from soni.du.slot_extractor import SlotExtractionInput

logger = logging.getLogger(__name__)


def get_flow_slot_definitions(
    config: ConfigProtocol,
    flow_name: str,
) -> list[SlotExtractionInput]:
    """Get slot definitions for a specific flow.

    Collects slot names from collect steps in the flow, then looks up
    each slot in config.slots to get type information for NLU extraction.

    Args:
        config: Soni configuration (via Protocol)
        flow_name: Name of the flow to get slots for

    Returns:
        List of SlotExtractionInput for Pass 2 of two-pass NLU
    """
    flow_cfg = config.flows.get(flow_name)
    if not flow_cfg:
        logger.debug(f"Flow '{flow_name}' not found in config")
        return []

    # Collect slot names from collect steps
    slot_names = {step.slot for step in flow_cfg.steps if step.type == "collect" and step.slot}

    if not slot_names:
        logger.debug(f"Flow '{flow_name}' has no collect steps")
        return []

    # Build SlotExtractionInput for each slot with definition
    slot_defs: list[SlotExtractionInput] = []
    for name in slot_names:
        slot_config = config.slots.get(name)
        if slot_config:
            slot_defs.append(
                SlotExtractionInput(
                    name=name,
                    slot_type=slot_config.type,
                    description=slot_config.description or slot_config.prompt,
                    examples=slot_config.examples,
                )
            )
        else:
            # Slot used but not defined globally - use minimal info
            logger.debug(f"Slot '{name}' used in flow but not defined in config.slots")
            slot_defs.append(
                SlotExtractionInput(
                    name=name,
                    slot_type="string",
                    description=f"Value for {name}",
                )
            )

    logger.debug(f"Built {len(slot_defs)} slot definitions for flow '{flow_name}'")
    return slot_defs


def build_du_context(state: DialogueState, context: RuntimeContext) -> DialogueContext:
    """Construct NLU context from current dialogue state.

    Builds a comprehensive DialogueContext object containing all information
    the NLU needs to understand user intent: available flows, commands,
    current slots, and expected slot.

    Note: This does NOT include flow_slots for Pass 1 to avoid context overload.
    Slot extraction happens in Pass 2 if StartFlow is detected.

    Args:
        state: Current dialogue state from LangGraph
        context: Runtime context with config and managers

    Returns:
        DialogueContext ready for NLU processing
    """
    config = context.config
    fm = context.flow_manager

    # 1. Available flows from config
    available_flows = []
    if hasattr(config, "flows"):
        for name, flow_cfg in config.flows.items():
            # Use trigger_intents from YAML or fallback to heuristic
            trigger_intents = flow_cfg.trigger_intents or [f"start {name}", name]
            available_flows.append(
                FlowInfo(
                    name=name,
                    description=flow_cfg.description,
                    trigger_intents=trigger_intents,
                )
            )

    # 2. Available commands
    # Include required_fields so LLM knows what to provide
    available_commands = [
        CommandInfo(
            command_type="start_flow",
            description="Start a new flow. flow_name must match one of available_flows.name",
            required_fields=["flow_name"],
            example='{"type": "start_flow", "flow_name": "check_balance"}',
        ),
        CommandInfo(
            command_type="set_slot",
            description="Set a slot value when user provides information",
            required_fields=["slot", "value"],
            example='{"type": "set_slot", "slot": "account_type", "value": "checking"}',
        ),
    ]

    # 3. Active flow and expected slot
    curr_ctx = fm.get_active_context(state)
    active_flow = curr_ctx["flow_name"] if curr_ctx else None
    expected_slot = state.get("waiting_for_slot")  # Set by collect/confirm nodes

    # 4. Current slots - convert from dict to SlotValue list
    current_slots: list[SlotValue] = []
    if curr_ctx:
        flow_id = curr_ctx["flow_id"]
        slot_dict = state.get("flow_slots", {}).get(flow_id, {})
        for slot_name, slot_value in slot_dict.items():
            # Skip internal slots (prefixed with __)
            if not slot_name.startswith("__"):
                # NOTE: Converting to string to maintain consistency with NLU expectations
                # Type coercion happens in validators, not here
                current_slots.append(
                    SlotValue(name=slot_name, value=str(slot_value) if slot_value else None)
                )

    return DialogueContext(
        available_flows=available_flows,
        available_commands=available_commands,
        active_flow=active_flow,
        current_slots=current_slots,
        expected_slot=expected_slot,
        conversation_state="idle" if not active_flow else "collecting",
    )


async def understand_node(
    state: DialogueState,
    config: RunnableConfig,
) -> dict[str, Any]:
    """Process user input via NLU and update state with extracted commands.

    This is the main entry point for understanding user intent. It coordinates
    between the NLU module and the FlowManager to transform raw input into
    structured state changes.

    Implements two-pass NLU:
    - Pass 1: Intent detection via SoniDU
    - Pass 2: Slot extraction via SlotExtractor (only if StartFlow detected)

    Args:
        state: Current dialogue state
        config: LangGraph runnable config (contains RuntimeContext)

    Returns:
        Dictionary with updated state keys (flow_stack, flow_slots, commands, etc.)
    """
    # 1. Get Context
    runtime_ctx = get_runtime_context(config)
    du = runtime_ctx.du  # DUProtocol
    fm = runtime_ctx.flow_manager
    slot_extractor = runtime_ctx.slot_extractor  # NEW: SlotExtractor

    # 2. Build DU Context & Run NLU (Pass 1: Intent Detection)
    du_ctx = build_du_context(state, runtime_ctx)
    user_message = state.get("user_message") or ""
    nlu_out = await du.acall(user_message, du_ctx)

    # 3. Check for StartFlow and run Pass 2 (Slot Extraction) if needed
    commands = list(nlu_out.commands)  # Make mutable copy

    start_flow_cmd = next(
        (c for c in commands if isinstance(c, StartFlow)),
        None,
    )

    if start_flow_cmd and slot_extractor:
        # Pass 2: Extract slots for the new flow
        flow_name = start_flow_cmd.flow_name
        slot_defs = get_flow_slot_definitions(runtime_ctx.config, flow_name)

        if slot_defs:
            logger.debug(f"Running Pass 2 slot extraction for flow '{flow_name}'")
            extracted_slots = await slot_extractor.acall(user_message, slot_defs)

            if extracted_slots:
                logger.info(
                    f"Pass 2 extracted {len(extracted_slots)} slots: "
                    f"{[s.slot for s in extracted_slots]}"
                )
                # Append extracted SetSlot commands
                commands.extend(extracted_slots)

    # 4. Process Commands (Update State)
    # Commands are typed Pydantic models - use isinstance() for type narrowing
    expected_slot = state.get("waiting_for_slot")
    should_reset_flow_state = False

    for cmd in commands:
        # Use isinstance() for proper type narrowing (SOLID compliance)
        if isinstance(cmd, StartFlow):
            # Handle intent change (pushes flow)
            await fm.handle_intent_change(state, cmd.flow_name)

        elif isinstance(cmd, SetSlot):
            await fm.set_slot(state, cmd.slot, cmd.value)
            # Check if this is the slot we were waiting for
            if cmd.slot == expected_slot:
                should_reset_flow_state = True

        elif isinstance(cmd, (AffirmConfirmation, DenyConfirmation)):
            # Confirmation commands should also allow flow to continue
            # The confirm node will process the actual affirm/deny logic
            should_reset_flow_state = True

        # NOTE: Other command types (clarify, chitchat, etc.) are handled
        # by routing logic in subsequent nodes, not here
        else:
            logger.warning(f"Unhandled command type in understand_node: {cmd.type}")

    # 5. Reset flow state if we received relevant input
    # This allows the subgraph to continue executing instead of immediately returning
    new_flow_state = state.get("flow_state")
    new_waiting_for_slot = state.get("waiting_for_slot")

    if should_reset_flow_state:
        new_flow_state = FlowState.ACTIVE
        # Only clear waiting_for_slot for SetSlot commands
        # Confirmation commands need waiting_for_slot to identify which slot to update
        has_confirmation_cmd = any(
            isinstance(cmd, (AffirmConfirmation, DenyConfirmation)) for cmd in commands
        )
        if not has_confirmation_cmd:
            new_waiting_for_slot = None

    # 6. Return updates
    # Must return keys that changed so LangGraph keeps them
    # FlowManager modifies flow_stack and flow_slots in place
    return {
        "flow_state": new_flow_state,
        "waiting_for_slot": new_waiting_for_slot,
        "flow_slots": state.get("flow_slots"),
        "flow_stack": state.get("flow_stack"),
        "commands": [cmd.model_dump() for cmd in commands],
        "metadata": state.get("metadata", {}),
    }
