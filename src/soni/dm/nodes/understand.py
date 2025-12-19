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
from typing import Any, cast

from langgraph.runtime import Runtime

from soni.core.commands import (
    AffirmConfirmation,
    DenyConfirmation,
)
from soni.core.constants import FlowState
from soni.core.types import (
    DialogueState,
    RuntimeContext,
)
from soni.dm.nodes.command_registry import get_command_registry

logger = logging.getLogger(__name__)


def create_state_view(
    base_state: DialogueState, accumulated_updates: dict[str, Any]
) -> DialogueState:
    """Create an immutable view of state with accumulated updates applied.

    This allows subsequent command handlers to see the effect of previous
    commands without mutating the original state.
    """
    # Create shallow copy with updates overlaid
    # We use cast because TypedDict doesn't support **kwargs dict expansion safely in Mypy
    view = cast(
        DialogueState,
        {
            **base_state,
            **{k: v for k, v in accumulated_updates.items() if k in base_state},
        },
    )
    return view


async def understand_node(
    state: DialogueState,
    runtime: Runtime[RuntimeContext],
) -> dict[str, Any]:
    """Process user input via NLU and update state with extracted commands.

    This is the main entry point for understanding user intent. It coordinates
    between the NLU module and the FlowManager to transform raw input into
    structured state changes.

    Implements two-pass NLU via NLUService:
    - Pass 1: Intent detection via SoniDU
    - Pass 2: Slot extraction via SlotExtractor (only if StartFlow detected)

    Args:
        state: Current dialogue state
        runtime: LangGraph runtime (provides RuntimeContext)

    Returns:
        Dictionary with updated state keys (flow_stack, flow_slots, commands, etc.)
    """
    # 1. Get Context
    runtime_ctx = runtime.context
    user_message = state.get("user_message") or ""

    # 2. Get Commands: either pre-populated (resume case) or via NLU
    # During interrupt resume, RuntimeLoop populates state.commands before routing here
    pre_existing_commands = state.get("commands", [])

    if pre_existing_commands:
        # Resume case: commands already processed by RuntimeLoop before goto
        # Deserialize dict commands back to Command objects
        from soni.core.commands import parse_command

        commands = [parse_command(cmd) for cmd in pre_existing_commands]
    else:
        # Normal case: Run NLU via NLUService (centralized 2-pass processing)
        from soni.du.service import NLUService

        nlu_service = NLUService(runtime_ctx.du, runtime_ctx.slot_extractor)
        commands = await nlu_service.process_message(user_message, state, runtime_ctx)

    # 4. Process Commands via Registry (SRP compliance)
    expected_slot = state.get("waiting_for_slot")
    should_reset_flow_state = False
    response_messages = []
    accumulated_updates: dict[str, Any] = {}

    registry = get_command_registry()

    for cmd in commands:
        # Create view with accumulated updates for this handler
        # This keeps the original 'state' immutable while allowing
        # handlers to see effects of previous commands in this turn.
        state_view = create_state_view(state, accumulated_updates)

        result = await registry.dispatch(cmd, state_view, runtime_ctx, expected_slot)
        if result:
            # Accumulate updates from handler without mutating original state
            accumulated_updates.update(result.updates)
            response_messages.extend(result.messages)
            if result.should_reset_flow_state:
                should_reset_flow_state = True

    # 5. Reset flow state if we received relevant input
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

    # Calculate last request if messages were generated
    last_response = response_messages[-1].content if response_messages else None

    # 6. Build final return dict
    # Start with accumulated updates
    updates: dict[str, Any] = accumulated_updates.copy()

    # Preserve pre-existing commands (from resume) so collect_node can access them
    # Only clear if we generated new commands via NLU (which have been processed)
    final_commands = pre_existing_commands if pre_existing_commands else []

    updates.update(
        {
            "flow_state": new_flow_state,
            "waiting_for_slot": new_waiting_for_slot,
            "commands": final_commands,  # Preserve for collect_node if from resume
            "messages": response_messages,
            "last_response": last_response,
            "metadata": state.get("metadata", {}),
        }
    )

    # Note: We do NOT need to force flow_stack/flow_slots into updates if they never changed.
    # LangGraph merges updates into existing state.
    # If they were in accumulated_updates, they are already in 'updates'.

    return updates
