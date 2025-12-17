"""UnderstandNode - processes user input through NLU and updates dialogue state.

## How Understand Node Works

The understand node is the **NLU gateway** in Soni's dialogue management pipeline.
It transforms raw user input into structured commands that the Dialogue Manager
can execute deterministically.

## Processing Pipeline

1. **Build DialogueContext**: Constructs comprehensive context from current state
2. **Run NLU**: Passes user message + context to DSPy-optimized NLU module
3. **Extract Commands**: Receives structured Pydantic commands from NLU
4. **Update State**: Applies commands to modify flow stack and slots
5. **Return Changes**: Returns modified state keys for LangGraph persistence

```
User Message → Build Context → NLU (DSPy) → Commands → State Updates
     ↓              ↓              ↓            ↓           ↓
  "Book a      Available     [StartFlow,   Push flow,  Return new
   flight"      flows,        SetSlot]     set slot     flow_stack
               current slots,
               expected slot
```

## DialogueContext Construction

The `build_du_context` helper constructs a rich context object containing:

- **Available Flows**: All flows user can start (from config)
- **Available Commands**: Command types NLU can generate
- **Active Flow**: Currently executing flow (if any)
- **Current Slots**: Already-filled slot values in active flow
- **Expected Slot**: Slot the system is currently asking for
- **Conversation State**: Current phase (idle, collecting, confirming)

## Command Processing

Commands are **typed Pydantic models** from `soni.core.commands`:

### Flow Control Commands
- **start_flow**: Push new flow onto stack
- **cancel_flow**: Cancel and pop current flow

### Slot Commands
- **set_slot**: Fill a slot with extracted value
- **correct_slot**: Update previously filled slot
- **affirm**: User confirms (yes)
- **deny**: User denies (no)

### Conversation Commands
- **clarify**: User requests clarification
- **chitchat**: Off-topic conversation

## State Management

The understand node uses **FlowManager** to:
- **handle_intent_change**: Push new flows onto stack
- **set_slot**: Update slot values in active flow context

**Critical**: Uses `flow_id` (unique instance) not `flow_name` (definition)
for data access to support multiple instances of same flow.

## Integration Points

- **Upstream**: Entry point for each dialogue turn (from RuntimeLoop)
- **Downstream**: Routes to `execute_node` which dispatches to flows
- **Dependencies**:
  - `DUProtocol` (NLU provider - typically SoniDU with DSPy)
  - `FlowManager` (state mutations)
  - `SoniConfig` (flow definitions)

## Type Safety

Commands are properly typed using Pydantic's discriminated unions:
- No `hasattr()` checks needed - use `isinstance()` for type narrowing
- Pydantic ensures required fields exist per command type
- Command structure validated at NLU output boundary

## Example Flow

```
User: "Book a flight to Paris"

1. Build Context:
   - available_flows: [book_flight, check_status, ...]
   - active_flow: None
   - expected_slot: None

2. NLU Output:
   commands: [
     StartFlow(type="start_flow", flow_name="book_flight"),
     SetSlot(type="set_slot", slot="destination", value="Paris")
   ]

3. State Updates:
   - Push book_flight flow to stack
   - Set destination="Paris" in flow slots

4. Return:
   - flow_stack: [FlowContext(flow_id="book_flight_a1b2", ...)]
   - flow_slots: {"book_flight_a1b2": {"destination": "Paris"}}
```

## Implementation Details

- **Async**: All operations use `async def` for consistency
- **Idempotent Commands**: Commands can be replayed without side effects
- **Type-Safe**: Leverages Pydantic models throughout pipeline
- **Observable**: Commands logged for debugging and auditing
"""

from typing import Any

from langchain_core.runnables import RunnableConfig

from soni.core.commands import AffirmConfirmation, DenyConfirmation, SetSlot, StartFlow
from soni.core.types import DialogueState, RuntimeContext, get_runtime_context
from soni.du.models import CommandInfo, DialogueContext, FlowInfo, SlotValue


def build_du_context(state: DialogueState, context: RuntimeContext) -> DialogueContext:
    """Construct NLU context from current dialogue state.

    Builds a comprehensive DialogueContext object containing all information
    the NLU needs to understand user intent: available flows, commands,
    current slots, and expected slot.

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

    Args:
        state: Current dialogue state
        config: LangGraph runnable config (contains RuntimeContext)

    Returns:
        Dictionary with updated state keys (flow_stack, flow_slots, commands, etc.)
    """
    # 1. Get Context
    context = get_runtime_context(config)
    du = context.du  # DUProtocol
    fm = context.flow_manager

    # 2. Build DU Context & Run NLU
    du_ctx = build_du_context(state, context)
    user_message = state.get("user_message") or ""
    nlu_out = await du.aforward(user_message, du_ctx)

    # 3. Process Commands (Update State)
    # Commands are typed Pydantic models - use isinstance() for type narrowing
    commands = nlu_out.commands

    # Track if we should reset flow state to allow continuation
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

    # 4. Reset flow state if we received relevant input
    # This allows the subgraph to continue executing instead of immediately returning
    new_flow_state = state.get("flow_state")
    new_waiting_for_slot = state.get("waiting_for_slot")

    if should_reset_flow_state:
        new_flow_state = "active"
        # Only clear waiting_for_slot for SetSlot commands
        # Confirmation commands need waiting_for_slot to identify which slot to update
        has_confirmation_cmd = any(
            isinstance(cmd, (AffirmConfirmation, DenyConfirmation)) for cmd in commands
        )
        if not has_confirmation_cmd:
            new_waiting_for_slot = None

    # 5. Return updates
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
