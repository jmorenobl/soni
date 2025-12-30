"""Orchestrator node - thin coordinator using RuntimeContext."""

from typing import Any

from langgraph.runtime import Runtime

from soni.core.types import DialogueState
from soni.dm.orchestrator import (
    build_merged_return,
    build_subgraph_state,
    merge_outputs,
    merge_state,
)
from soni.dm.orchestrator.command_processor import CommandProcessor
from soni.dm.orchestrator.commands import (
    CancelFlowHandler,
    SetSlotHandler,
    StartFlowHandler,
)
from soni.dm.orchestrator.task_handler import PendingTaskHandler, TaskAction
from soni.flow.manager import apply_delta_to_dict
from soni.runtime.context import RuntimeContext

# Safety limit to prevent infinite loops
MAX_FLOW_ITERATIONS = 50


async def orchestrator_node(
    state: DialogueState,
    runtime: Runtime[RuntimeContext],
) -> DialogueState | dict[str, Any]:
    """Orchestrator node - executes flows in a loop until interrupt or completion.

    Loop Pattern:
    1. Execute active flow's subgraph
    2. If INTERRUPT → return to user
    3. If flow changed (link/call) → continue loop with new flow
    4. If flow completed → pop, continue loop if parent exists
    5. If stack empty → done
    """
    ctx = runtime.context
    fm = ctx.flow_manager

    # Initialize components with config-aware handlers
    handlers = ctx.command_handlers or (
        StartFlowHandler(ctx.config),
        CancelFlowHandler(),
        SetSlotHandler(),
    )
    command_processor = CommandProcessor(list(handlers))
    task_handler = PendingTaskHandler(ctx.message_sink)

    # 1. Process NLU commands
    commands = state.get("commands") or []
    delta = await command_processor.process(
        commands=commands,
        state=state,
        flow_manager=fm,
    )
    updates = delta.to_dict()

    # 2. Build working state
    working_state = merge_state(dict(state), updates)

    # 3. Main execution loop
    iteration = 0
    final_output: dict[str, Any] = {}

    while iteration < MAX_FLOW_ITERATIONS:
        iteration += 1

        # Get active flow
        active_ctx = fm.get_active_context(working_state)
        if not active_ctx:
            # No active flow → done
            # If this is the first iteration and no response generated, return help message
            if iteration == 1 and not updates.get("response"):
                updates["response"] = "How can I help?"
            break

        # Track stack before execution
        stack_before = working_state.get("flow_stack") or []
        stack_size_before = len(stack_before)

        # Execute subgraph
        subgraph = ctx.subgraph_registry.get(active_ctx["flow_name"])
        subgraph_state = build_subgraph_state(working_state)
        subgraph_output: dict[str, Any] = {}

        async for event in subgraph.astream(subgraph_state, stream_mode="updates"):
            for _node_name, output in event.items():
                pending_task = output.get("_pending_task")

                if pending_task:
                    result = await task_handler.handle(pending_task)

                    if result.action == TaskAction.INTERRUPT:
                        # Interrupt → return to user immediately
                        merge_outputs(final_output, subgraph_output)
                        merge_outputs(final_output, output)

                        # Merge with deep slot merge (same as final return)
                        return build_merged_return(updates, final_output, result.task)

                    if result.action == TaskAction.CONTINUE:
                        output["_pending_task"] = None

                merge_outputs(subgraph_output, output)

        # Subgraph completed → analyze what happened
        final_stack = subgraph_output.get("flow_stack", working_state.get("flow_stack") or [])
        final_stack_size = len(final_stack)

        if final_stack_size > stack_size_before:
            # Link/Call: stack grew → new flow was pushed
            # Update working state and continue loop to execute new flow
            working_state = merge_state(working_state, subgraph_output)
            merge_outputs(final_output, subgraph_output)
            continue

        elif final_stack_size == stack_size_before:
            # Flow completed normally → pop it from stack
            try:
                _, pop_delta = fm.pop_flow(working_state)
                apply_delta_to_dict(updates, pop_delta)
                working_state["flow_stack"] = pop_delta.flow_stack or []
            except Exception:
                # Stack already empty or error
                break

            merge_outputs(final_output, subgraph_output)

            # Check if parent flow exists to continue
            if working_state.get("flow_stack"):
                continue  # Resume parent flow
            else:
                break  # Stack empty, done

        else:
            # Stack shrunk (cancel already popped) → continue or exit
            working_state["flow_stack"] = final_stack
            final_output.update(subgraph_output)
            if final_stack:
                continue
            else:
                break

    pending_task = updates.get("_pending_task") or final_output.get("_pending_task")
    return build_merged_return(updates, final_output, pending_task)
