# Soni Framework - Flow Management

## Overview

Soni supports complex conversation patterns through a robust flow stack architecture managed by a dedicated `FlowManager`. In the command-driven architecture (v2.0), **Commands trigger flow operations** - the FlowManager is called by CommandHandlers, not directly by routing logic.

**Key Capabilities**:
- Multiple concurrent flow instances (e.g., comparing two bookings)
- Flow interruption and resumption with preserved state
- Explicit data transfer between flows via inputs/outputs
- Command-driven operations (StartFlow, CancelFlow commands)
- Strategy-based stack depth limiting
- Automatic memory management

## Command-Driven Flow Operations

In v2.0, Commands trigger FlowManager operations:

| Command | FlowManager Operation |
|---------|----------------------|
| `StartFlow("book_flight")` | `flow_manager.push_flow(state, "book_flight")` |
| `CancelFlow()` | `flow_manager.pop_flow(state, result="cancelled")` |
| `SetSlot("origin", "NYC")` | `flow_manager.set_slot(state, "origin", "NYC")` |
| `CorrectSlot("dest", "LA")` | `flow_manager.set_slot(state, "destination", "LA")` |

```python
# Example: StartFlowHandler calls FlowManager
class StartFlowHandler:
    async def execute(self, cmd: StartFlow, state, context) -> dict:
        flow_id = context.flow_manager.push_flow(
            state,
            cmd.flow_name,
            cmd.slots
        )
        return {"active_flow_id": flow_id}
```

## Flow Stack Architecture

### Core Principles (SOLID)

1.  **Single Responsibility (SRP)**: Flow state manipulation is encapsulated in `FlowManager`, separate from the orchestration logic in `RuntimeLoop`.
2.  **Open/Closed (OCP)**: Stack depth limiting uses a strategy pattern, allowing new behaviors (e.g., "ask_user") without modifying core logic.
3.  **Instance Identity**: Flows are tracked by unique `flow_id` to allow concurrency.
4.  **Pure Data**: State is stored as serializable `TypedDict` for LangGraph compatibility.

### Data Structures

```python
from typing import TypedDict, Any, Literal, Protocol
import time
import uuid

# Flow States
FlowState = Literal["active", "paused", "completed", "cancelled", "abandoned", "error"]

class FlowContext(TypedDict):
    """
    Context for a specific instance of a flow.
    Stored in state["flow_stack"] and state["metadata"]["completed_flows"].
    """

    flow_id: str
    """Unique instance ID (e.g., 'book_flight_3a7f'). Key for flow_slots."""

    flow_name: str
    """Name of the flow definition (e.g., 'book_flight')."""

    flow_state: FlowState
    """Current execution state."""

    current_step: str | None
    """Current step identifier in the flow definition."""

    outputs: dict[str, Any]
    """
    Final outputs produced by this flow.
    Preserved in history even after flow_slots are pruned.
    """

    started_at: float
    """Unix timestamp when flow was started."""

    paused_at: float | None
    """Unix timestamp when flow was paused (None if never paused)."""

    completed_at: float | None
    """Unix timestamp when flow completed (None if still active/paused)."""

    context: str | None
    """Human-readable reason for pause/cancel (debugging aid)."""

class DialogueState(TypedDict):
    # ... other fields (messages, conversation_state, etc.) ...

    flow_stack: list[FlowContext]
    """
    Active flow stack (LIFO).
    - Bottom: Root/oldest flow
    - Top: Currently active flow
    - Source of Truth for current flow.
    """

    flow_slots: dict[str, dict[str, Any]]
    """
    Storage for active flow data (The Heap).
    Key: flow_id (NOT flow_name)
    Value: dict of slot values
    """

    metadata: dict[str, Any]
    """
    Archive and system metadata.
    Standard keys:
        - completed_flows: list[FlowContext]
        - error: str | None
    """
```

## FlowManager (SRP Implementation)

We encapsulate all stack operations in a dedicated manager class.

```python
from soni.core.errors import FlowStackLimitError

class FlowManager:
    """
    Manages the flow execution stack and data heap.

    Responsibilities:
    - Push/Pop operations with consistency checks
    - Data access (slots) scoped to active flow
    - Stack depth enforcement
    - Memory pruning
    """

    def __init__(self, config: SoniConfig):
        self.config = config
        self._strategies = {
            "cancel_oldest": self._strategy_cancel_oldest,
            "reject_new": self._strategy_reject_new
        }

    def push_flow(
        self,
        state: DialogueState,
        flow_name: str,
        inputs: dict[str, Any] | None = None,
        reason: str | None = None
    ) -> str:
        """
        Start a new flow instance.

        Steps:
        1. Enforce stack limit via configured strategy.
        2. Pause current flow.
        3. Create and push new instance.
        4. Initialize data heap.
        """
        # 1. Enforce Stack Limit (OCP: Strategy Pattern)
        self._enforce_stack_limit(state)

        # 2. Pause current flow
        if state["flow_stack"]:
            current = state["flow_stack"][-1]
            current["flow_state"] = "paused"
            current["paused_at"] = time.time()
            current["context"] = reason

        # 3. Generate ID and Context
        flow_id = f"{flow_name}_{uuid.uuid4().hex[:8]}"

        new_context: FlowContext = {
            "flow_id": flow_id,
            "flow_name": flow_name,
            "flow_state": "active",
            "current_step": None,
            "outputs": {},
            "started_at": time.time(),
            "paused_at": None,
            "completed_at": None,
            "context": reason
        }
        state["flow_stack"].append(new_context)

        # 4. Initialize Data Heap
        state["flow_slots"][flow_id] = inputs or {}

        return flow_id

    def pop_flow(
        self,
        state: DialogueState,
        outputs: dict[str, Any] | None = None,
        result: FlowState = "completed"
    ) -> None:
        """
        Finish current flow instance.

        Steps:
        1. Pop from stack.
        2. Archive to metadata.
        3. Resume previous flow.
        """
        if not state["flow_stack"]:
            return

        # 1. Pop
        completed_flow = state["flow_stack"].pop()

        # 2. Finalize and Archive
        completed_flow["flow_state"] = result
        completed_flow["completed_at"] = time.time()
        if outputs:
            completed_flow["outputs"] = outputs

        state["metadata"].setdefault("completed_flows", []).append(completed_flow)

        # 3. Resume Previous
        if state["flow_stack"]:
            previous = state["flow_stack"][-1]
            previous["flow_state"] = "active"
            previous["paused_at"] = None

    # --- Data Access Methods ---

    def get_active_context(self, state: DialogueState) -> FlowContext | None:
        """Get the currently active flow context (top of stack)."""
        return state["flow_stack"][-1] if state["flow_stack"] else None

    def get_slot(self, state: DialogueState, slot_name: str) -> Any:
        """Get slot value from active flow."""
        ctx = self.get_active_context(state)
        if not ctx:
            return None
        return state["flow_slots"].get(ctx["flow_id"], {}).get(slot_name)

    def set_slot(self, state: DialogueState, slot_name: str, value: Any) -> None:
        """Set slot value in active flow."""
        ctx = self.get_active_context(state)
        if ctx:
            if ctx["flow_id"] not in state["flow_slots"]:
                state["flow_slots"][ctx["flow_id"]] = {}
            state["flow_slots"][ctx["flow_id"]][slot_name] = value

    # --- Strategy Implementations ---

    def _enforce_stack_limit(self, state: DialogueState) -> None:
        """Apply configured stack limit strategy."""
        max_depth = self.config.flow_management.max_stack_depth
        if len(state["flow_stack"]) < max_depth:
            return

        strategy_name = self.config.flow_management.on_limit_reached
        strategy_fn = self._strategies.get(strategy_name)

        if strategy_fn:
            strategy_fn(state)
        else:
            # Default fallback
            self._strategy_reject_new(state)

    def _strategy_cancel_oldest(self, state: DialogueState) -> None:
        """Strategy: Cancel oldest flow to make room."""
        oldest = state["flow_stack"].pop(0)
        oldest["flow_state"] = "cancelled"
        oldest["completed_at"] = time.time()
        oldest["context"] = "Cancelled: stack depth limit"

        state["metadata"].setdefault("completed_flows", []).append(oldest)
        # Clean up slots immediately
        state["flow_slots"].pop(oldest["flow_id"], None)

    def _strategy_reject_new(self, state: DialogueState) -> None:
        """Strategy: Reject new flow."""
        raise FlowStackLimitError(
            f"Maximum flow depth ({self.config.flow_management.max_stack_depth}) reached."
        )
```

## Cross-Flow Data Transfer

Data transfer is handled through **Explicit Inputs** and **Archived Outputs**. This decoupling ensures flows are independent and testable.

### Pattern

```python
# 1. check_booking finishes
outputs = {"booking_ref": "BK-123", "status": "confirmed"}
flow_manager.pop_flow(state, outputs=outputs)

# 2. Router decides to start modify_booking
# Extract data from the completed flow (now in archive)
last_completed = state["metadata"]["completed_flows"][-1]
booking_ref = last_completed["outputs"]["booking_ref"]

# 3. New flow starts with INJECTED inputs
flow_manager.push_flow(
    state,
    "modify_booking",
    inputs={"booking_ref": booking_ref}  # Explicit injection
)
```

## Digression vs Flow Interruption

**Design Rule**: Digressions are handled by a separate system (`DigressionHandler`) and **never** modify the flow stack.

| Feature | Modifies Stack? | Component | Example |
|---------|-----------------|-----------|---------|
| **Flow Interruption** | YES (`push_flow`) | `FlowManager` | "Cancel this and book a hotel" |
| **Digression** | NO | `DigressionHandler` | "What hotels do you have?" |

## Memory Management

Since `state` persists, `FlowManager` includes pruning logic.

```python
def prune_state(self, state: DialogueState) -> None:
    """
    Prune state to prevent unbounded memory growth.
    """
    # 1. Prune orphan flow slots
    active_ids = {ctx["flow_id"] for ctx in state["flow_stack"]}
    orphan_ids = [fid for fid in state["flow_slots"] if fid not in active_ids]

    for fid in orphan_ids:
        del state["flow_slots"][fid]

    # 2. Prune archive
    max_completed = self.config.memory_management.max_completed_flows
    completed = state["metadata"].get("completed_flows", [])

    if len(completed) > max_completed:
        state["metadata"]["completed_flows"] = completed[-max_completed:]
```

## Integration with LangGraph

`FlowManager` is injected into `RuntimeContext` and used by nodes.

```python
async def handle_intent_change_node(
    state: DialogueState,
    context: RuntimeContext
) -> dict[str, Any]:
    """LangGraph node for intent changes."""

    new_intent = state["nlu_result"]["command"]

    if new_intent == "cancel":
        context.flow_manager.pop_flow(state, result="cancelled")
        return {"conversation_state": "idle"}
    else:
        try:
            context.flow_manager.push_flow(
                state,
                new_intent,
                reason=f"User requested {new_intent}"
            )
            return {"conversation_state": "waiting_for_slot"}
        except FlowStackLimitError as e:
            return {"last_response": str(e)}
```

## Configuration

```yaml
settings:
  flow_management:
    max_stack_depth: 3
    on_limit_reached: "cancel_oldest" # Options: cancel_oldest, reject_new

  memory_management:
    max_completed_flows: 10
```

## Processing Multiple Slots

### Overview

Soni supports processing multiple slots provided in a single user message (e.g., "I want to fly from New York to Los Angeles"). This is handled through an iterative step advancement pattern implemented in `FlowStepManager.advance_through_completed_steps`.

### Iterative Step Advancement Pattern

When multiple slots are provided in one message:

1. **NLU extracts all slots** from the message
2. **All slots are processed and normalized** using `_process_all_slots` helper
3. **Slots are saved to state** via `flow_slots[flow_id]`
4. **Iterative advancement** through completed steps:
   - Check if current step is complete (all required slots filled)
   - If complete, advance to next step
   - Repeat until finding an incomplete step or flow completes

### Example Flow

```python
# User message: "I want to fly from New York to Los Angeles"
# NLU extracts: origin="New York", destination="Los Angeles"

# 1. Process all slots
flow_slots = await _process_all_slots(slots, state, active_ctx, normalizer)
state["flow_slots"] = flow_slots

# 2. Advance through completed steps
updates = step_manager.advance_through_completed_steps(state, context)
# Will advance:
#   - collect_origin (complete) → collect_destination
#   - collect_destination (complete) → collect_date
#   - collect_date (incomplete) → STOP

# Result: waiting_for_slot = "departure_date"
```

### Safety Mechanisms

- **Max Iterations**: Limited to 20 iterations to prevent infinite loops
- **Step Completion Check**: Each step is verified before advancement
- **Flow Completion Detection**: Stops when flow completes

### Integration Points

- **validate_slot_node**: Uses `advance_through_completed_steps` after processing slots
- **handle_intent_change_node**: Uses `advance_through_completed_steps` after activating flow with slots

## Summary

Soni's flow management architecture is built on strict software engineering principles:

1.  **Command-Driven**: FlowManager operations triggered by Commands via Handlers
2.  **SRP**: `FlowManager` handles stack logic; `FlowStepManager` handles step progression
3.  **OCP**: Stack limiting strategies are extensible
4.  **Pure Data**: State is fully serializable (TypedDict)
5.  **Explicit Dependencies**: Data transfer is explicit via inputs/outputs
6.  **Robustness**: Unique IDs prevent collisions; strategies handle limits gracefully

## Next Steps

- **[11-commands.md](11-commands.md)** - Command layer specification
- **[03-components.md](03-components.md)** - Component reference
- **[04-state-machine.md](04-state-machine.md)** - Complete DialogueState schema

---

**Design Version**: v2.0 (Command-Driven Architecture)
**Status**: Production-ready design specification
