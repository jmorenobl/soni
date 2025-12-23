"""Orchestrator node - thin coordinator using RuntimeContext."""

from typing import Any

from langgraph.runtime import Runtime

from soni.core.types import DialogueState, _merge_flow_slots
from soni.dm.orchestrator.command_processor import CommandProcessor
from soni.dm.orchestrator.commands import DEFAULT_HANDLERS
from soni.dm.orchestrator.task_handler import PendingTaskHandler, TaskAction
from soni.runtime.context import RuntimeContext


async def orchestrator_node(
    state: DialogueState,
    runtime: Runtime[RuntimeContext],
) -> dict[str, Any]:
    """Orchestrator node - thin coordinator delegating to specialized components.

    Accesses dependencies via runtime.context (LangGraph pattern).
    """
    ctx = runtime.context

    # Initialize components
    handlers = ctx.command_handlers or tuple(DEFAULT_HANDLERS)
    command_processor = CommandProcessor(list(handlers))
    task_handler = PendingTaskHandler(ctx.message_sink)

    # 1. Process NLU commands
    commands = state.get("commands") or []
    delta = await command_processor.process(
        commands=commands,
        state=state,
        flow_manager=ctx.flow_manager,
    )
    updates = delta.to_dict()

    # 2. Get active flow
    # Build local state for subgraph - MERGE slots, don't overwrite!
    merged_state = dict(state)
    merged_state.update(updates)

    if "flow_slots" in updates:
        merged_state["flow_slots"] = _merge_flow_slots(
            state.get("flow_slots") or {}, updates["flow_slots"]
        )
    # typeddict cast for mypy if needed, but dict merge is fine for reading
    from typing import cast

    active_ctx = ctx.flow_manager.get_active_context(cast(DialogueState, merged_state))

    if not active_ctx:
        return {**updates, "response": "How can I help?", "_pending_task": None}

    # 3. Stream subgraph execution
    subgraph = ctx.subgraph_registry.get(active_ctx["flow_name"])
    subgraph_state = _build_subgraph_state(merged_state)
    final_output: dict[str, Any] = {}

    async for event in subgraph.astream(subgraph_state, stream_mode="updates"):
        for _node_name, output in event.items():
            pending_task = output.get("_pending_task")

            if pending_task:
                result = await task_handler.handle(pending_task)

                if result.action == TaskAction.INTERRUPT:
                    # Return orchestrator updates + the pending task to interrupt
                    return {**updates, "_pending_task": result.task}

                if result.action == TaskAction.CONTINUE:
                    continue

            final_output.update(output)

    # 4. Return merged result (transform subgraph output to parent state)
    return {**updates, **_transform_result(final_output)}


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
    # Keep relevant updates, ignore internal fields properties
    result_dict = {k: v for k, v in result.items() if not k.startswith("_") or k == "_pending_task"}

    # Explicitly clear pending task if not returned by subgraph (i.e. task completed)
    if "_pending_task" not in result_dict:
        result_dict["_pending_task"] = None

    return result_dict
