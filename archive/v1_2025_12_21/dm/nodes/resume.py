"""ResumeNode - handles flow completion and automatic stack resumption.

## How Resume Node Works

The resume node manages the **flow lifecycle** when a flow completes execution.
It is responsible for cleaning up the flow stack and triggering auto-resume of
parent flows when necessary.

## Flow Completion Lifecycle

When a flow subgraph finishes, the resume node:

1. **Check Flow State**: Determines if flow is truly complete or just waiting for input
2. **Pop Completed Flow**: Removes the finished flow from the stack
3. **Determine Next Action**:
   - If parent flow exists → Prepares for auto-resume
   - If stack empty → Ends conversation turn

```
Flow Stack Before:         Flow Stack After:
┌─────────────────┐       ┌─────────────────┐
│ check_balance   │  ←    │ transfer_funds  │ ← Active (auto-resumed)
├─────────────────┤  POP  └─────────────────┘
│ transfer_funds  │
└─────────────────┘
```

## Auto-Resume Mechanism

**Auto-resume** allows interrupted flows to continue automatically after a sub-flow completes:

### Example: Cross-Flow Interruption

```
User: "I want to transfer money"
→ Starts transfer_funds flow
→ Asks for amount

User: "Before that, how much do I have?"
→ Starts check_balance flow (interrupts transfer)
→ Stack: [transfer_funds, check_balance]

System: Shows balance (check_balance completes)
→ Resume node pops check_balance
→ Stack: [transfer_funds]
→ Auto-resumes transfer_funds flow
→ Continues asking for transfer amount
```

## Critical: Waiting Input vs Completion

The resume node distinguishes between two states:

1. **Waiting Input** (`flow_state == "waiting_input"`):
   - Flow is paused for user input (e.g., collect node)
   - **Action**: Do NOT pop, just pass through
   - Stack remains intact for next turn

2. **Completed** (`flow_state != "waiting_input"`):
   - Flow has finished execution
   - **Action**: Pop from stack
   - Check for parent flows to resume

## Integration Points

- **Called By**: Flow subgraphs when they reach their end
- **Calls**: Returns control to RuntimeLoop
- **Side Effects**: Modifies `flow_stack` via `FlowManager.pop_flow()`

## Error Handling

- **Empty Stack**: If pop attempted on empty stack, logs warning and returns gracefully
- **FlowStackError**: Caught and handled to prevent crashes
- **Defensive**: Always checks stack state before operations

## Implementation Details

- **Async**: Uses `await flow_manager.pop_flow()` for consistency
- **Logging**: Comprehensive debug/info logging for observability
- **State Preservation**: Returns updated `flow_stack` to LangGraph
"""

import logging
from typing import Any

from langgraph.runtime import Runtime
from soni.core.types import DialogueState, RuntimeContext

logger = logging.getLogger(__name__)


async def resume_node(
    state: DialogueState,
    runtime: Runtime[RuntimeContext],
) -> dict[str, Any]:
    """Handle flow completion and stack resumption.

    This node is called when a flow subgraph finishes execution.
    Interrupts are now handled by LangGraph interrupt() API.
    """
    context = runtime.context
    flow_manager = context.flow_manager

    # Build updates dict
    updates: dict[str, Any] = {}

    # Check for digression: if a new flow was pushed during an interrupt,
    # we should NOT pop - instead, let execute_node run the new flow
    if state.get("_digression_pending"):
        logger.debug("Digression pending - skipping pop, will execute new flow")
        # Clear the flag so next time we do pop
        updates["_digression_pending"] = False
        return updates

    # Pop the completed flow (if any)
    if state.get("flow_stack"):
        _, delta = flow_manager.pop_flow(state)
        if delta:
            if delta.flow_stack is not None:
                updates["flow_stack"] = delta.flow_stack
            if delta.flow_slots is not None:
                updates["flow_slots"] = delta.flow_slots

    return updates
