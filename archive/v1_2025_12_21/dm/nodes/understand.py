"""UnderstandNode - processes user input through NLU and stores commands.

## How Understand Node Works (Refactored)

The understand node is the **NLU gateway** in Soni's dialogue management pipeline.
It transforms raw user input into structured commands and stores them in state
for downstream nodes to consume.

## Key Responsibility: EXTRACT, DON'T PROCESS

This node ONLY:
1. Runs NLU to extract commands from user input
2. Serializes commands to `state.commands`
3. Updates basic state (messages, metadata)

Command processing is delegated to owner nodes:
- `execute_node`: StartFlow, CancelFlow
- `collect_node`: SetSlot
- `confirm_node`: AffirmConfirmation, DenyConfirmation
- `respond_node`: ChitChat

## Two-Pass NLU Architecture

**Pass 1 (Intent Detection):**
- Runs SoniDU to detect intent and generate commands
- Output: StartFlow, SetSlot (for active flows), etc.

**Pass 2 (Slot Extraction) - only if StartFlow detected:**
- Runs SlotExtractor with flow-specific slot definitions
- Output: SetSlot commands merged with Pass 1 results

## Integration Points

- **Upstream**: Entry point for each dialogue turn (from RuntimeLoop)
- **Downstream**: Routes to `execute_node` which dispatches to flows
- **Dependencies**:
  - `DUProtocol` (NLU provider - typically SoniDU with DSPy)
  - `SlotExtractor` (Pass 2 extraction)
"""

import logging
from typing import Any

from langgraph.runtime import Runtime

from soni.core.types import (
    DialogueState,
    RuntimeContext,
)

logger = logging.getLogger(__name__)


async def understand_node(
    state: DialogueState,
    runtime: Runtime[RuntimeContext],
) -> dict[str, Any]:
    """Process user input via NLU and store commands in state.

    REFACTORED: This node now only extracts commands and stores them.
    Command processing is delegated to downstream nodes (execute, collect, etc.).

    Args:
        state: Current dialogue state
        runtime: LangGraph runtime (provides RuntimeContext)

    Returns:
        Dictionary with commands and basic state updates
    """
    # 1. Get Context
    runtime_ctx = runtime.context
    user_message = state.get("user_message") or ""

    # 2. Get Commands: either pre-populated (resume case) or via NLU
    pre_existing_commands = state.get("commands", [])

    if pre_existing_commands:
        # Resume case: commands already in state (from RuntimeLoop resume payload)
        # Keep them as-is for downstream nodes
        serialized_commands = pre_existing_commands
        logger.debug(f"Using {len(serialized_commands)} pre-existing commands from resume")
    else:
        # Normal case: Run NLU via NLUService (centralized 2-pass processing)
        from soni.du.service import NLUService

        nlu_service = NLUService(runtime_ctx.du, runtime_ctx.slot_extractor)
        commands = await nlu_service.process_message(user_message, state, runtime_ctx)

        # Serialize commands for state storage
        serialized_commands = [
            cmd.model_dump() if hasattr(cmd, "model_dump") else cmd for cmd in commands
        ]
        logger.debug(
            f"NLU extracted {len(serialized_commands)} commands: {[c.get('type') for c in serialized_commands]}"
        )

    # 3. Build return dict - ONLY store commands, don't process them
    # Command processing is now delegated to:
    # - execute_node: StartFlow, CancelFlow
    # - collect_node: SetSlot
    # - confirm_node: AffirmConfirmation, DenyConfirmation
    # - respond_node: ChitChat

    updates: dict[str, Any] = {
        "commands": serialized_commands,
        "metadata": state.get("metadata", {}),
        "_pending_responses": [],  # Clear queue at start of each turn
    }

    return updates
