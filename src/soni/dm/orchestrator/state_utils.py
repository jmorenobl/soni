"""State manipulation utilities for orchestrator.

This module provides pure functions for merging and transforming
state dictionaries during orchestration.
"""

from typing import Any, cast

from soni.core.slot_utils import deep_merge_flow_slots
from soni.core.types import DialogueState


def merge_state(base: DialogueState | dict[str, Any], delta: dict[str, Any]) -> DialogueState:
    """Merge delta into base state, handling flow_slots and _executed_steps specially."""
    result = dict(base)
    result.update(delta)

    if "flow_slots" in delta:
        result["flow_slots"] = deep_merge_flow_slots(
            base.get("flow_slots") or {}, delta["flow_slots"]
        )

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

    return cast(DialogueState, result)


def build_subgraph_state(state: DialogueState) -> dict[str, Any]:
    """Build state for subgraph invocation."""
    return {
        "flow_stack": state.get("flow_stack", []),
        "flow_slots": state.get("flow_slots", {}),
        "user_message": state.get("user_message"),
        "commands": state.get("commands", []),
        "messages": state.get("messages", []),
        "_executed_steps": state.get("_executed_steps", {}),
    }


def transform_result(result: dict[str, Any]) -> dict[str, Any]:
    """Transform subgraph result to parent state updates."""
    # Keep relevant updates, preserve flow_stack, _pending_task, _executed_steps
    keep_fields = {"flow_stack", "flow_slots", "_pending_task", "_executed_steps"}
    result_dict = {k: v for k, v in result.items() if not k.startswith("_") or k in keep_fields}

    return result_dict


def merge_outputs(target: dict[str, Any], source: dict[str, Any]) -> None:
    """Merge source output into target with deep merge for flow_slots."""
    for k, v in source.items():
        if k == "flow_slots" and isinstance(v, dict):
            # Deep merge flow_slots to prevent overwrite of sibling keys
            target_slots = target.get("flow_slots", {})
            target["flow_slots"] = deep_merge_flow_slots(target_slots, v)
        else:
            target[k] = v


def build_merged_return(
    updates: DialogueState | dict[str, Any],
    final_output: dict[str, Any],
    pending_task: Any = None,
) -> DialogueState:
    """Build return dict with deep merge for flow_slots.

    Critical: Prevents subgraph output from overwriting NLU-derived slots.
    """
    transformed_output = transform_result(final_output)

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

    return cast(DialogueState, result)
