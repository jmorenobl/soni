"""Orchestrator node - thin coordinator using RuntimeContext."""

from typing import Any, cast

from langgraph.runtime import Runtime

from soni.core.types import DialogueState, FlowContext, _merge_flow_slots
from soni.dm.orchestrator.command_processor import CommandProcessor
from soni.dm.orchestrator.commands import DEFAULT_HANDLERS
from soni.dm.orchestrator.task_handler import PendingTaskHandler, TaskAction
from soni.flow.manager import merge_delta as fm_merge_delta
from soni.runtime.context import RuntimeContext

# Safety limit to prevent infinite loops
MAX_FLOW_ITERATIONS = 50


async def orchestrator_node(
    state: DialogueState,
    runtime: Runtime[RuntimeContext],
) -> dict[str, Any]:
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

    # Initialize components
    handlers = ctx.command_handlers or tuple(DEFAULT_HANDLERS)
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
    working_state = _merge_state(dict(state), updates)

    # 3. Main execution loop
    iteration = 0
    final_output: dict[str, Any] = {}

    while iteration < MAX_FLOW_ITERATIONS:
        iteration += 1

        # Get active flow
        active_ctx = fm.get_active_context(cast(DialogueState, working_state))
        if not active_ctx:
            # No active flow → done
            # If this is the first iteration and no response generated, return help message
            if iteration == 1 and not updates.get("response"):
                updates["response"] = "How can I help?"
            break

        # Track stack before execution
        stack_before = cast(list[FlowContext], working_state.get("flow_stack") or [])
        stack_size_before = len(stack_before)

        # Execute subgraph
        subgraph = ctx.subgraph_registry.get(active_ctx["flow_name"])
        subgraph_state = _build_subgraph_state(working_state)
        subgraph_output: dict[str, Any] = {}

        async for event in subgraph.astream(subgraph_state, stream_mode="updates"):
            for _node_name, output in event.items():
                pending_task = output.get("_pending_task")

                if pending_task:
                    result = await task_handler.handle(pending_task)

                    if result.action == TaskAction.INTERRUPT:
                        # Interrupt → return to user immediately
                        _merge_outputs(final_output, subgraph_output)
                        _merge_outputs(final_output, output)

                        # Merge with deep slot merge (same as final return)
                        return _build_merged_return(updates, final_output, result.task)

                    if result.action == TaskAction.CONTINUE:
                        output["_pending_task"] = None

                _merge_outputs(subgraph_output, output)

        # Subgraph completed → analyze what happened
        final_stack = cast(
            list[FlowContext],
            subgraph_output.get("flow_stack", working_state.get("flow_stack") or []),
        )
        final_stack_size = len(final_stack)

        if final_stack_size > stack_size_before:
            # Link/Call: stack grew → new flow was pushed
            # Update working state and continue loop to execute new flow
            working_state = _merge_state(working_state, subgraph_output)
            _merge_outputs(final_output, subgraph_output)
            continue

        elif final_stack_size == stack_size_before:
            # Flow completed normally → pop it from stack
            try:
                _, pop_delta = fm.pop_flow(cast(DialogueState, working_state))
                fm_merge_delta(updates, pop_delta)
                working_state["flow_stack"] = pop_delta.flow_stack or []
            except Exception:
                # Stack already empty or error
                break

            _merge_outputs(final_output, subgraph_output)

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

    return _build_merged_return(updates, final_output, updates.get("_pending_task"))


def _build_merged_return(
    updates: dict[str, Any],
    final_output: dict[str, Any],
    pending_task: Any = None,
) -> dict[str, Any]:
    """Build return dict with deep merge for flow_slots.

    Critical: Prevents subgraph output from overwriting NLU-derived slots.
    """
    transformed_output = _transform_result(final_output)

    if "flow_slots" in transformed_output:
        nlu_slots = updates.get("flow_slots") or {}
        subgraph_slots = transformed_output["flow_slots"]

        merged_slots = dict(nlu_slots)
        for f_id, f_slots in subgraph_slots.items():
            if f_id in merged_slots:
                merged_slots[f_id] = {**merged_slots[f_id], **f_slots}
            else:
                merged_slots[f_id] = f_slots

        updates["flow_slots"] = merged_slots
        del transformed_output["flow_slots"]

    result = {**updates, **transformed_output}

    # Set pending_task (None to clear, or value to set)
    result["_pending_task"] = pending_task

    return result


def _merge_state(base: dict[str, Any], delta: dict[str, Any]) -> dict[str, Any]:
    """Merge delta into base state, handling flow_slots and _executed_steps specially."""
    result = dict(base)
    result.update(delta)

    if "flow_slots" in delta:
        result["flow_slots"] = _merge_flow_slots(base.get("flow_slots") or {}, delta["flow_slots"])

    # Merge _executed_steps additively
    if "_executed_steps" in delta:
        base_steps = dict(base.get("_executed_steps") or {})
        for flow_id, steps in (delta["_executed_steps"] or {}).items():
            if steps is None:
                # Removal signal
                base_steps.pop(flow_id, None)
            else:
                existing = base_steps.get(flow_id) or set()
                base_steps[flow_id] = existing | steps
        result["_executed_steps"] = base_steps

    return result


def _build_subgraph_state(state: dict[str, Any]) -> dict[str, Any]:
    """Build state for subgraph invocation."""
    return {
        "flow_stack": state.get("flow_stack", []),
        "flow_slots": state.get("flow_slots", {}),
        "user_message": state.get("user_message"),
        "commands": state.get("commands", []),
        "messages": state.get("messages", []),
        "_executed_steps": state.get("_executed_steps", {}),
    }


def _transform_result(result: dict[str, Any]) -> dict[str, Any]:
    """Transform subgraph result to parent state updates."""
    # Keep relevant updates, preserve flow_stack, _pending_task, _executed_steps
    keep_fields = {"flow_stack", "flow_slots", "_pending_task", "_executed_steps"}
    result_dict = {k: v for k, v in result.items() if not k.startswith("_") or k in keep_fields}

    return result_dict


def _merge_outputs(target: dict[str, Any], source: dict[str, Any]) -> None:
    """Merge source output into target with deep merge for flow_slots."""
    for k, v in source.items():
        if k == "flow_slots" and isinstance(v, dict):
            # Deep merge flow_slots to prevent overwrite of sibling keys
            target_slots = target.get("flow_slots", {})
            for flow_id, slots in v.items():
                if flow_id in target_slots:
                    target_slots[flow_id] = {**target_slots[flow_id], **slots}
                else:
                    target_slots[flow_id] = slots
            target["flow_slots"] = target_slots
        else:
            target[k] = v
