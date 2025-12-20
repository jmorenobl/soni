"""ExecuteNode - consumes flow commands and routes to subgraphs.

## How Execute Node Works (Refactored)

The execute node is the **command consumer** for flow-level commands and
the **central dispatcher** for routing to flow subgraphs.

## Command Ownership

This node CONSUMES:
- `StartFlow` → Push new flow onto stack, route to it
- `CancelFlow` → Pop flow(s) from stack

## Execution Flow

1. **Consume Flow Commands**: Process StartFlow/CancelFlow from state.commands
2. **Update Stack**: Push/pop flows as needed
3. **Route**: Jump to active flow subgraph or respond node

```
Commands: [StartFlow("transfer"), SetSlot("amount", 100)]
                    ↓
Execute Node:
  - Consumes StartFlow → pushes "transfer" to stack
  - Leaves SetSlot for collect_node
  - Routes to flow_transfer subgraph
```

## Integration Points

- **Upstream**: Receives control from `understand_node` after NLU extraction
- **Downstream**:
  - Flow subgraphs (for active flows)
  - `respond_node` (for idle state or chitchat)
"""

import logging
from typing import Any

from langgraph.runtime import Runtime
from langgraph.types import Command

from soni.core.commands import CancelFlow, StartFlow, parse_command
from soni.core.constants import NodeName, get_flow_node_name
from soni.core.types import DialogueState, RuntimeContext
from soni.flow.manager import FlowDelta

logger = logging.getLogger(__name__)


def _merge_delta(updates: dict[str, Any], delta: FlowDelta | None) -> None:
    """Merge FlowDelta into updates dict."""
    if delta is None:
        return
    if delta.flow_stack is not None:
        updates["flow_stack"] = delta.flow_stack
    if delta.flow_slots is not None:
        updates["flow_slots"] = delta.flow_slots


async def execute_node(
    state: DialogueState,
    runtime: Runtime[RuntimeContext],
) -> Command[Any] | dict[str, Any]:
    """Consume flow commands and route to appropriate subgraph.

    Consumes: StartFlow, CancelFlow
    Leaves: SetSlot, AffirmConfirmation, DenyConfirmation, ChitChat (for other nodes)

    Returns:
        Command with goto target and state updates
    """
    context = runtime.context
    flow_manager = context.flow_manager

    # 1. Process commands - consume only flow-related ones
    commands = state.get("commands", [])
    remaining_commands: list[Any] = []
    updates: dict[str, Any] = {}

    for cmd_data in commands:
        cmd = parse_command(cmd_data) if isinstance(cmd_data, dict) else cmd_data

        if isinstance(cmd, StartFlow):
            # CONSUME: Push new flow onto stack
            logger.info(f"StartFlow consumed: pushing '{cmd.flow_name}' onto stack")

            # Use handle_intent_change which handles push logic
            delta = flow_manager.handle_intent_change(state, cmd.flow_name)
            _merge_delta(updates, delta)

            # If StartFlow has pre-populated slots, add them
            if cmd.slots:
                for slot_name, slot_value in cmd.slots.items():
                    slot_delta = flow_manager.set_slot(state, slot_name, slot_value)
                    _merge_delta(updates, slot_delta)

            # Don't add to remaining - this command is consumed

        elif isinstance(cmd, CancelFlow):
            # CONSUME: Pop flow(s) from stack
            flow_name = cmd.flow_name if hasattr(cmd, "flow_name") else None
            logger.info(f"CancelFlow consumed: popping '{flow_name or 'active'}' from stack")

            # Pop the specified flow or active flow
            _, delta = flow_manager.pop_flow(state)
            _merge_delta(updates, delta)

            # Don't add to remaining - this command is consumed

        else:
            # PASS THROUGH: Keep for downstream nodes
            remaining_commands.append(cmd_data)

    # 2. Update commands in state (remove consumed ones)
    updates["commands"] = remaining_commands

    # 3. Clear branch target to avoid pollution from previous digressions
    updates["_branch_target"] = None

    # 4. Determine routing target based on updated stack
    # Create a view of state with our updates applied
    updated_stack = updates.get("flow_stack", state.get("flow_stack", []))

    if updated_stack:
        # Route to active flow subgraph
        active_flow = updated_stack[-1]  # Top of stack
        flow_name = active_flow.get("flow_name", active_flow.get("name", ""))
        target = get_flow_node_name(flow_name)
        logger.debug(f"Routing to flow subgraph: {target}")
        return Command(goto=target, update=updates)

    # 4. No active flow - route to respond (idle state or chitchat handling)
    logger.debug("No active flow, routing to respond node")
    return Command(goto=NodeName.RESPOND, update=updates)
