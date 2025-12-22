"""ConfirmNodeFactory for M7 + M8 (rephrasing)."""

from typing import Any

from langgraph.runtime import Runtime

from soni.compiler.nodes.base import rephrase_if_enabled
from soni.config.models import ConfirmStepConfig, StepConfig
from soni.core.types import DialogueState, NodeFunction
from soni.runtime.context import RuntimeContext


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

        slot_name = step.slot
        prompt = step.message or f"Please confirm {slot_name}"
        on_confirm = step.on_confirm
        on_deny = step.on_deny
        rephrase_step = step.rephrase  # M8: Step-level rephrasing flag

        async def confirm_node(
            state: DialogueState,
            runtime: Runtime[RuntimeContext],
        ) -> dict[str, Any]:
            """Confirm slot value with user."""
            fm = runtime.context.flow_manager

            # Check for confirmation response in commands
            # Commands are dicts in state
            commands = state.get("commands") or []
            for cmd in commands:
                cmd_type = cmd.get("type")

                if cmd_type == "affirm":
                    # Confirmed -> execute on_confirm or continue (default)
                    # Returning empty commands to consume them
                    return {"commands": [], "_branch_target": on_confirm}

                if cmd_type == "deny":
                    # Denied -> execute on_deny
                    # If on_deny is None, what happens?
                    # Usually deny implies stopping or re-asking.
                    # If on_deny is None, we might loop or continue?
                    # Spec says "If denied without -> jump to on_deny target"
                    # If on_deny is None, maybe default to END? Or continue?
                    # Logic: return _branch_target=on_deny. If None, it continues flow... which means 'proceed'?
                    # No, deny usually means "don't proceed".
                    # But if user configures on_deny=None, maybe they handle it next step?
                    # We will just respect the config.
                    return {"commands": [], "_branch_target": on_deny}

                # Correction handling inside confirm node?
                # M7 spec 5.2 includes:
                # if cmd.get("type") == "correction": ...
                # Wait, "correction" vs "correct_slot".
                # commands.py has "correct_slot".
                # We should handle "correct_slot".
                if cmd_type == "correct_slot":
                    slot = cmd["slot"]
                    value = cmd["new_value"]
                    # Usually we only accept correction for THE slot we are confirming?
                    # Or any slot?
                    # If we confirm "amount", and user says "change destination", that's a correction for dest.
                    # M7 spec logic (line 173): `if cmd.get("type") == "correction": ... set_slot ... return`
                    # It updates slot and RE-PROMPTS (returns update but logic continues next loop iter?)
                    # If we return updates, execute_node updates state.
                    # Does it re-execute THIS node?
                    # Yes, if we don't set _executed_steps?
                    # Wait, idempotency.
                    # confirm_node is basically a prompt loop.
                    # If we return updates, the flow stays on this step?
                    # We need to make sure we don't advance step index.
                    # Returning {flow_slots...} without commands... wait, we MUST consume the command.
                    # return {"flow_slots": ..., "commands": []}
                    # And since we don't set _branch_target or _executed_steps (wait, usually implicit?)
                    # LangGraph loop:
                    # Node executes -> returns update.
                    # If we don't move to next step, we stay here?
                    # No, LangGraph edges move to next step UNLESS we signal loop?
                    # Our graph is linear unless branch.
                    # ConfirmNode is a node.
                    # If we perform correction, we want to STAY on ConfirmNode (re-prompt with new value).
                    # But if we return, the graph moves edge -> next node?
                    # Ah, we need a mechanism to Loop.
                    # Or ConfirmNode is a "while needed" node?
                    # The subgraph structure (lines 60-66 in subgraph.py) is linear.
                    # If confirm_node returns, edge goes to next node.
                    # UNLESS we use `_branch_target`.
                    # To stay on same node, we can target `step.step`.
                    # BUT `_branch_target` targets a step NAME.
                    # So `return {..., "_branch_target": step.step}`.

                    delta = fm.set_slot(state, slot, value)
                    return {
                        "flow_slots": delta.flow_slots if delta else {},
                        "commands": [],
                        "_branch_target": step.step,  # Loop back to self
                    }

            # If we are here, no relevant command found. Prompt needed.

            # Get current value to confirm
            slot_value = fm.get_slot(state, slot_name)

            # Format message
            formatted_prompt = prompt
            if slot_value is not None:
                try:
                    formatted_prompt = prompt.format(**{slot_name: slot_value})
                except KeyError:
                    pass  # Keep raw prompt if format fails

            # M8: Rephrase prompt if enabled
            final_prompt = await rephrase_if_enabled(
                formatted_prompt, state, runtime.context, rephrase_step
            )

            return {
                "_need_input": True,
                "_pending_prompt": {
                    "type": "confirm",
                    "slot": slot_name,
                    "value": slot_value,
                    "prompt": final_prompt,
                },
                "_pending_responses": [final_prompt],
            }

        confirm_node.__name__ = f"confirm_{step.step}"
        return confirm_node
