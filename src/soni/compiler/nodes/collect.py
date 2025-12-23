"""CollectNodeFactory for M5 (with validation) + M8 (rephrasing)."""

from typing import Any, cast

from langgraph.runtime import Runtime

from soni.config.models import CollectStepConfig, StepConfig
from soni.core.expression import evaluate_value as interpolate
from soni.core.pending_task import collect
from soni.core.types import DialogueState, NodeFunction
from soni.core.validation import validate
from soni.flow.manager import merge_delta
from soni.runtime.context import RuntimeContext


async def collect_node(
    state: DialogueState,
    runtime: Runtime[RuntimeContext],
    config: CollectStepConfig,
) -> dict[str, Any]:
    """Collect and validate slot value from user.

    Returns PendingTask instead of internal prompt fields.
    """
    fm = runtime.context.flow_manager
    slot_name = config.slot
    validator_name = config.validator
    error_message = config.validation_error_message or f"Invalid value for {slot_name}"

    # 1. Already filled? Continue to next step
    existing_value = fm.get_slot(state, slot_name)
    if existing_value:
        return {"_branch_target": None, "_pending_task": None}

    # 2. Check for value in commands
    commands = state.get("commands", []) or []

    matching_command = None
    for cmd in commands:
        if cmd.get("type") == "set_slot" and cmd.get("slot") == slot_name:
            matching_command = cmd
            break

    if matching_command:
        value = matching_command["value"]

        # 3. Validate if validator configured
        if validator_name:
            slots = fm.get_all_slots(state)
            is_valid = await validate(value, validator_name, slots)

            if not is_valid:
                # Validation failed - re-prompt with error
                final_error = interpolate(error_message, cast(dict[str, Any], state))
                return {
                    "_pending_task": collect(
                        prompt=final_error,
                        slot=slot_name,
                        options=getattr(config, "options", None),
                        metadata={"error": final_error},
                    ),
                }

        # 4. Valid - set slot and continue
        delta = fm.set_slot(state, slot_name, value)
        updates: dict[str, Any] = {"commands": [], "_branch_target": None, "_pending_task": None}
        merge_delta(updates, delta)
        return updates

    # 5. No value provided - need input
    prompt = interpolate(config.message, cast(dict[str, Any], state))
    return {
        "_pending_task": collect(
            prompt=prompt,
            slot=slot_name,
            options=getattr(config, "options", None),
        ),
    }


class CollectNodeFactory:
    """Factory for collect step nodes (SRP: slot collection + validation)."""

    def create(
        self,
        step: StepConfig,
        all_steps: list[StepConfig] | None = None,
        step_index: int | None = None,
    ) -> NodeFunction:
        """Create a collect node function."""
        if not isinstance(step, CollectStepConfig):
            raise ValueError(f"CollectNodeFactory received wrong step type: {type(step).__name__}")

        async def _node(state: DialogueState, runtime: Runtime[RuntimeContext]) -> dict[str, Any]:
            return await collect_node(state, runtime, step)

        _node.__name__ = f"collect_{step.step}"
        return _node
