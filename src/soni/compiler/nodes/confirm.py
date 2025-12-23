"""ConfirmNodeFactory for M7 + M8 (rephrasing)."""

from typing import Any, cast

from langgraph.runtime import Runtime

from soni.config.models import ConfirmStepConfig, StepConfig
from soni.core.expression import evaluate_value as interpolate
from soni.core.pending_task import confirm
from soni.core.types import DialogueState, NodeFunction
from soni.runtime.context import RuntimeContext


async def confirm_node(
    state: DialogueState,
    runtime: Runtime[RuntimeContext],
    config: ConfirmStepConfig,
) -> dict[str, Any]:
    """Ask user for confirmation.

    Returns PendingTask instead of internal prompt fields.
    """
    fm = runtime.context.flow_manager
    slot_name = config.slot

    # 1. Check for confirmation response in commands
    commands = state.get("commands") or []
    for cmd in commands:
        cmd_type = cmd.get("type")

        if cmd_type == "affirm":
            # Confirmed
            return {"commands": [], "_branch_target": config.on_confirm}

        if cmd_type == "deny":
            # Denied
            return {"commands": [], "_branch_target": config.on_deny}

        if cmd_type == "correct_slot":
            slot = cmd["slot"]
            value = cmd["new_value"]
            delta = fm.set_slot(state, slot, value)
            return {
                "flow_slots": delta.flow_slots if delta else {},
                "commands": [],
                "_branch_target": config.step,  # Loop back to self
            }

    # 2. Already confirmed?
    if state.get("_confirmed"):
        return {}

    # 3. Prompt needed
    slot_value = fm.get_slot(state, slot_name)
    prompt_template = config.message or f"Please confirm {slot_name}"

    # Format message
    formatted_prompt = prompt_template
    if slot_value is not None:
        try:
            formatted_prompt = prompt_template.format(**{slot_name: slot_value})
        except KeyError:
            pass

    prompt = interpolate(formatted_prompt, cast(dict[str, Any], state))

    return {
        "_pending_task": confirm(
            prompt=prompt,
            options=getattr(config, "options", ["yes", "no"]),
        ),
        "_pending_responses": [prompt],
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
