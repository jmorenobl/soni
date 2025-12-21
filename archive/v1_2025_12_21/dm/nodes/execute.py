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

logger = logging.getLogger(__name__)


from langgraph.runtime import Runtime
from langgraph.types import Command, interrupt
from soni.core.commands import CancelFlow, StartFlow, parse_command
from soni.core.constants import NodeName
from soni.core.types import DialogueState, RuntimeContext
from soni.flow.manager import merge_delta


async def execute_node(
    state: DialogueState,
    runtime: Runtime[RuntimeContext],
) -> Command[Any] | dict[str, Any]:
    """Execute flow logic and coordinate subgraphs.

    Implements 'Invoke from Node' pattern:
    1. Consumes global commands (StartFlow, CancelFlow)
    2. Identifies active flow subgraph
    3. Loops:
       a. Invokes subgraph
       b. Handles _need_input via interrupt()
       c. Calls NLU on resume
       d. Appends NLU commands to state
       e. Repeats until flow finished or global command/digression
    """
    context = runtime.context
    flow_manager = context.flow_manager
    # nlu_service and subgraphs added in Phase 1
    nlu_service = context.nlu_service
    subgraphs = context.subgraphs or {}

    # Local loop for handling interactions
    while True:
        # 0. CHECK IF WE NEED TO INTERRUPT
        # If _need_input is True from previous iteration, trigger interrupt now
        # This ensures state is persisted BEFORE interrupt (two-phase pattern)
        if state.get("_need_input"):
            prompt_data = state.get("_pending_prompt")
            logger.info(f"Interrupting for input: {prompt_data}")
            user_input = interrupt(prompt_data)

            # RESUME: We got input!
            logger.info(f"Resumed with input: {user_input}")
            message = user_input.get("message") if isinstance(user_input, dict) else str(user_input)

            # Call NLU Service (uses process_message, not acall)
            if nlu_service:
                new_commands = await nlu_service.process_message(message, state, context)
            else:
                new_commands = []

            # Return Command to restart with new commands and cleared flags
            return Command(
                goto=NodeName.EXECUTE,
                update={
                    "commands": new_commands,
                    "_need_input": False,
                    "_pending_prompt": None,
                },
            )

        # 1. CONSUME GLOBAL COMMANDS
        # We process commands in current state first
        commands = state.get("commands", [])
        remaining_commands: list[Any] = []
        updates: dict[str, Any] = {}
        global_command_processed = False

        for cmd_data in commands:
            cmd = parse_command(cmd_data) if isinstance(cmd_data, dict) else cmd_data

            if isinstance(cmd, StartFlow):
                logger.info(f"StartFlow: pushing '{cmd.flow_name}'")
                delta = flow_manager.handle_intent_change(state, cmd.flow_name)
                merge_delta(updates, delta)
                global_command_processed = True

                # Apply pre-filled slots
                if cmd.slots:
                    for s_name, s_val in cmd.slots.items():
                        s_delta = flow_manager.set_slot(state, s_name, s_val)
                        merge_delta(updates, s_delta)

            elif isinstance(cmd, CancelFlow):
                logger.info("CancelFlow: popping")
                _, delta = flow_manager.pop_flow(state)
                merge_delta(updates, delta)
                global_command_processed = True
            else:
                remaining_commands.append(cmd_data)

        # Apply updates to local state variable for next iteration
        # Note: We must also return these updates to the graph eventually
        # For now we simulate state update locally
        if updates:
            # Simple merge for local logic
            if "flow_stack" in updates:
                state["flow_stack"] = updates["flow_stack"]
            if "flow_slots" in updates:
                # This needs careful merging but usually we replace stack
                # For simplicity we might just merge slots if same flow
                # But flow stack change invalidates slots reference?
                # flow_manager.handle_intent_change returns new stack
                pass
            # Update slots
            # ...
            # Actually, we should rely on returning Command to restart if global command processed?
            # If we switch flow, we must restart loop to pick new subgraph.
            pass

        # If global command changed inputs/components, we should yield updates and RESTART execute_node
        # to ensure clean slate and correct subgraph selection.
        if global_command_processed:
            updates["commands"] = remaining_commands
            # Return updates and jump to SELF to restart logic with new state
            # Return updates and jump to SELF to restart logic with new state
            return Command(goto=NodeName.EXECUTE, update=updates)

        # 2. IDENTIFY ACTIVE FLOW
        flow_id = flow_manager.get_active_flow_id(state)
        active_ctx = flow_manager.get_active_context(state)

        if not flow_id or not active_ctx:
            # No active flow -> Route to Respond
            updates["commands"] = remaining_commands
            updates["_branch_target"] = None
            return Command(goto=NodeName.RESPOND, update=updates)

        flow_name = active_ctx.get("flow_name") or active_ctx.get("name")
        # subgraphs are indexed by flow_name (unprefixed)
        subgraph = subgraphs.get(flow_name)

        if not subgraph:
            logger.error(f"Subgraph not found for flow: {flow_name}")
            # Fail safe: pop flow and retry? or error?
            # Route to respond (effectively ending turn)
            return Command(goto=NodeName.RESPOND, update=updates)

        # 3. INVOKE SUBGRAPH
        # Prepare input: commands (local only), slots, etc.
        # We pass the WHOLE state usually, but filtering is better?
        # Subgraph needs: flow_slots, commands, _executed_steps
        # We inject 'commands' (remaining) so nodes can consume them

        # Note: We are not yielding updates yet. We are running "inside" the node.
        # We must construct input from current state + updates we calculated
        # Since we didn't yield updates, 'state' is stale regarding consumed commands.
        # We should create input_state with consumed commands removed.
        input_state = dict(state)
        input_state["commands"] = remaining_commands
        if "_executed_steps" not in input_state:
            input_state["_executed_steps"] = {}

        logger.debug(f"Invoking subgraph: {flow_name}")
        result = await subgraph.ainvoke(input_state)

        # 4. HANDLE INTERRUPT / RESULT
        # Merge result back into updates
        # Result contains flow_slots, _executed_steps, commands (output), _need_input, etc.
        # We need to accumulate these

        # Check if we need input
        if result.get("_need_input"):
            prompt_data = result.get("_pending_prompt")
            logger.info(f"Subgraph requested input: {prompt_data}")

            # TWO-PHASE INTERRUPT PATTERN:
            # Instead of calling interrupt() here (which discards state updates),
            # we return Command with updates. The NEXT execution of execute_node
            # will see _need_input=True and trigger the interrupt.
            full_updates = dict(updates)
            full_updates.update(result)  # Include subgraph state (flow_slots, etc.)

            return Command(goto=NodeName.EXECUTE, update=full_updates)

        # 6. NO INPUT NEEDED -> Subgraph finished turn
        # Return final updates and route to Respond (for chitchat/safety) or just End?
        # If flow finished, it might have popped itself? (via CancelFlow in result?)
        # Let's return the updates and let the loop restart (goto self) check stack?
        # Or if we know we are done, route to Respond.

        full_updates = dict(updates)
        full_updates.update(result)

        # If subgraph produced commands (e.g. EndFlow), we should process them.
        # Returning goto="execute_node" handles this! (Step 1 will process commands)
        # Checking if commands exist is good optimization.
        if result.get("commands"):
            return Command(goto=NodeName.EXECUTE, update=full_updates)

        # No commands, no input needed.
        # Means we are executing linearly and finished?
        # Or waiting?
        # Usually checking 'messages' to see if we said something?
        # We route to RESPOND to ensure output is flushed or handled.
        return Command(goto=NodeName.RESPOND, update=full_updates)
