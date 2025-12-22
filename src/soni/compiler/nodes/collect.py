"""CollectNodeFactory for M5 (with validation) + M8 (rephrasing)."""

from typing import Any

from langgraph.runtime import Runtime

from soni.compiler.nodes.base import rephrase_if_enabled
from soni.config.models import CollectStepConfig, StepConfig
from soni.core.types import DialogueState, NodeFunction
from soni.core.validation import validate
from soni.flow.manager import merge_delta
from soni.runtime.context import RuntimeContext


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

        slot_name = step.slot
        prompt = step.message
        validator_name = step.validator
        error_message = step.validation_error_message or f"Invalid value for {slot_name}"
        rephrase_step = step.rephrase  # M8: Step-level rephrasing flag

        async def collect_node(
            state: DialogueState,
            runtime: Runtime[RuntimeContext],
        ) -> dict[str, Any]:
            """Collect and validate slot value from user."""
            fm = runtime.context.flow_manager

            # 1. Already filled? Continue to next step
            existing_value = fm.get_slot(state, slot_name)
            if existing_value:
                return {"_branch_target": None}

            # 2. Check for value in commands
            commands = state.get("commands", []) or []

            matching_command = None
            for cmd in commands:
                if cmd.get("type") == "set_slot" and cmd.get("slot") == slot_name:
                    value = cmd["value"]
                    matching_command = cmd
                    break

            if matching_command:
                value = matching_command["value"]

                # 3. Validate if validator configured
                if validator_name:
                    slots = fm.get_all_slots(state)
                    is_valid = await validate(value, validator_name, slots)

                    if not is_valid:
                        # M8: Rephrase error message if enabled
                        final_error = await rephrase_if_enabled(
                            error_message, state, runtime.context, rephrase_step
                        )
                        # Validation failed - re-prompt with error
                        return {
                            "_need_input": True,
                            "_pending_prompt": {
                                "slot": slot_name,
                                "prompt": prompt,
                                "error": final_error,
                            },
                            "_pending_responses": [final_error],
                            "_branch_target": None,
                        }

                # 4. Valid - set slot and continue
                delta = fm.set_slot(state, slot_name, value)
                updates: dict[str, Any] = {"commands": [], "_branch_target": None}
                merge_delta(updates, delta)
                return updates

            # 5. No value provided - need input
            # M8: Rephrase prompt if enabled
            final_prompt = await rephrase_if_enabled(prompt, state, runtime.context, rephrase_step)
            ret = {
                "_need_input": True,
                "_pending_prompt": {"slot": slot_name, "prompt": final_prompt},
                "_pending_responses": [final_prompt],
                "_branch_target": None,
            }
            return ret

        collect_node.__name__ = f"collect_{step.step}"
        return collect_node
