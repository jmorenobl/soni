"""ExecuteNode - main routing hub for dialogue execution.

## How Execute Node Works

The execute node is the **central dispatcher** in Soni's dialogue management system.
It acts as the main entry point after the understand node processes user input, and
determines where execution should flow next based on the current flow stack state.

## Execution Flow

1. **Check Flow Stack**: Examines the `flow_stack` to determine if there's an active flow
2. **Route to Subgraph**: If active flow exists → jumps to that flow's subgraph node
3. **Route to Respond**: If no active flow → jumps to respond node (idle state)

```
User Input → Understand → Execute → ?
                                    ├─ flow_booking (active flow detected)
                                    ├─ flow_transfer (active flow detected)
                                    └─ respond (no active flow, idle state)
```

## Flow Subgraph Naming Convention

Each compiled flow creates a dedicated subgraph node following this pattern:

- **Convention**: `flow_{flow_name}`
- **Example**: Flow "book_flight" → Node "flow_booking"
- **Dynamic Routing**: Uses LangGraph's `Command(goto=target)` for runtime dispatch

## State Management

The execute node relies on `FlowManager` to:
- **Get Active Context**: Retrieves current flow information from stack
- **Determine Routing**: Uses flow name to construct target subgraph identifier

## Integration Points

- **Upstream**: Receives control from `understand_node` after NLU processing
- **Downstream**:
  - Flow subgraphs (for active flows)
  - `respond_node` (for idle state)
- **Resume Flow**: After a flow completes, `resume_node` may loop back to execute

## Implementation Details

- **No State Mutation**: This node is read-only, it only routes based on current state
- **Fallback Behavior**: If no active flow, defaults to respond node
- **Dynamic Dispatch**: Uses LangGraph Command API for runtime routing decisions
"""

from typing import Any

from langchain_core.runnables import RunnableConfig
from langgraph.types import Command

from soni.core.constants import get_flow_node_name
from soni.core.types import DialogueState, get_runtime_context


async def execute_node(
    state: DialogueState,
    config: RunnableConfig,
) -> Command[Any] | dict[str, Any]:
    """Determine execution path based on stack.

    Uses dynamic goto for flow subgraphs.
    """
    context = get_runtime_context(config)
    flow_manager = context.flow_manager
    # Check if we have an active flow
    active_ctx = flow_manager.get_active_context(state)
    if active_ctx:
        # Route to the subgraph node for this flow
        # Node name convention: flow_{flow_name}
        target = get_flow_node_name(active_ctx["flow_name"])
        return Command(goto=target)

    # If no active flow, go to respond (or handle idle state)
    return Command(goto="respond")
