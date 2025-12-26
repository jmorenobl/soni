"""ConfirmNodeFactory for M7 + M8 (ADR-002 compliant)."""

from typing import Any

from langgraph.runtime import Runtime

from soni.config.models import ConfirmStepConfig, StepConfig
from soni.core.expression import evaluate_value as interpolate
from soni.core.pending_task import confirm
from soni.core.types import DialogueState, NodeFunction
from soni.flow.manager import apply_delta_to_dict
from soni.runtime.context import RuntimeContext


async def confirm_node(
    state: DialogueState,
    runtime: Runtime[RuntimeContext],
    config: ConfirmStepConfig,
) -> dict[str, Any]:
    """Ask user for confirmation (ADR-002 compliant).

    Returns ConfirmTask instead of internal prompt fields.
    """
    fm = runtime.context.flow_manager
    slot_name = config.slot
    flow_id = fm.get_active_flow_id(state)
    step_id = config.step

    # Idempotency check (ADR-002 requirement)
    if flow_id:
        executed = (state.get("_executed_steps") or {}).get(flow_id, set())
        if step_id in executed:
            return {"_branch_target": None, "_pending_task": None}

    # 1. Check for confirmation response in commands
    commands = state.get("commands") or []
    for cmd in commands:
        cmd_type = cmd.get("type")

        if cmd_type == "affirm":
            # Confirmed - go to success path
            result: dict[str, Any] = {
                "commands": [],
                "_branch_target": config.on_confirm,
                "_pending_task": None,
            }
            if flow_id:
                result["_executed_steps"] = {flow_id: {step_id}}
            return result

        if cmd_type == "deny":
            # Denied - go to rejection path
            result = {
                "commands": [],
                "_branch_target": config.on_deny,
                "_pending_task": None,
            }
            if flow_id:
                result["_executed_steps"] = {flow_id: {step_id}}
            return result

        if cmd_type == "correct_slot":
            # Correction - update slot and show confirmation with new value
            slot = cmd["slot"]
            value = cmd["new_value"]
            delta = fm.set_slot(state, slot, value)

            # Build prompt with new value
            prompt_template = config.message or f"Please confirm {slot_name}"
            formatted_prompt = prompt_template
            try:
                formatted_prompt = prompt_template.format(**{slot_name: value})
            except KeyError:
                pass

            # Prepare slots for interpolation with the new value
            interpolation_slots = fm.get_all_slots(state)
            interpolation_slots[slot] = value

            result = {
                "commands": [],
                "_pending_task": confirm(
                    prompt=interpolate(formatted_prompt, interpolation_slots),
                    options=getattr(config, "options", ["yes", "no"]),
                ),
            }
            apply_delta_to_dict(result, delta)
            return result

    # 2. Prompt needed - show confirmation message
    slot_value = fm.get_slot(state, slot_name)
    prompt_template = config.message or f"Please confirm {slot_name}"

    # Format message with slot value
    formatted_prompt = prompt_template
    if slot_value is not None:
        try:
            formatted_prompt = prompt_template.format(**{slot_name: slot_value})
        except KeyError:
            pass

    prompt = interpolate(formatted_prompt, fm.get_all_slots(state))
    return {
        "_pending_task": confirm(
            prompt=prompt,
            options=getattr(config, "options", ["yes", "no"]),
        ),
    }


class ConfirmNodeFactory:
    """Factory for confirm step nodes (SRP: confirmation handling only)."""

    def create(
        self,
        step: StepConfig,
        all_steps: list[StepConfig] | None = None,
        step_index: int | None = None,
    ) -> NodeFunction:
        """Create a confirm node function."""
        if not isinstance(step, ConfirmStepConfig):
            raise ValueError(f"ConfirmNodeFactory received wrong step type: {type(step).__name__}")

        async def _node(state: DialogueState, runtime: Runtime[RuntimeContext]) -> dict[str, Any]:
            return await confirm_node(state, runtime, step)

        _node.__name__ = f"confirm_{step.step}"
        return _node
