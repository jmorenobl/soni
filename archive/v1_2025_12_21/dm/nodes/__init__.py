"""DM Nodes - Core dialogue management nodes for the RuntimeLoop.

This package contains the fundamental nodes that form Soni's dialogue
management orchestration layer. These nodes work together to process
user input, route to appropriate flows, execute actions, and generate
responses.

## Node Responsibilities

### understand_node
**NLU Gateway** - Entry point for each dialogue turn. Transforms raw user
input into structured commands via DSPy-optimized NLU, then updates state
(flow stack, slots) based on extracted commands.

### execute_node
**Routing Hub** - Examines flow stack and routes to active flow subgraph
or respond node. Uses dynamic LangGraph Command(goto=...) for runtime
dispatch to compiled flow nodes.

### resume_node
**Flow Lifecycle Manager** - Handles flow completion and auto-resume
logic. Pops completed flows from stack and prepares parent flow
resumption for cross-flow interruptions.

### respond_node
**Response Generator** - Final output stage that extracts the assistant's
response from message history and populates `last_response` for the
application to display to the user.

## Execution Flow

```
User Message
    ↓
understand_node (NLU → Commands → State Updates)
    ↓
execute_node (Route to Flow or Respond)
    ↓
[Flow Subgraph Execution]
    ↓
resume_node (Pop & Resume Logic)
    ↓
respond_node (Extract Final Response)
    ↓
User Sees Response
```

## Architecture Principles

- **Single Responsibility**: Each node has one clear purpose
- **Async-First**: All nodes use `async def` for consistency
- **Dependency Injection**: Nodes receive RuntimeContext via config
- **Type Safety**: Leverages Pydantic models and type hints throughout
- **Observable**: Comprehensive logging at each stage
"""

from soni.dm.nodes.execute import execute_node
from soni.dm.nodes.respond import respond_node
from soni.dm.nodes.resume import resume_node
from soni.dm.nodes.understand import understand_node

__all__ = ["execute_node", "respond_node", "understand_node", "resume_node"]
