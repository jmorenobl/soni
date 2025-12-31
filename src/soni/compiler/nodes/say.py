from typing import Any

from langgraph.runtime import Runtime

from soni.compiler.nodes.base import rephrase_if_enabled
from soni.config.models import SayStepConfig, StepConfig
from soni.core.pending_task import inform
from soni.core.types import DialogueState, NodeFunction
from soni.runtime.context import RuntimeContext


class SayNodeFactory:
    """Factory for say step nodes (SRP: single responsibility)."""

    def create(
        self,
        step: StepConfig,
        all_steps: list[StepConfig] | None = None,
        step_index: int | None = None,
    ) -> NodeFunction:
        """Create a node that returns a static response."""
        if not isinstance(step, SayStepConfig):
            raise ValueError(f"SayNodeFactory received wrong step type: {type(step).__name__}")

        message = step.message
        step_id = step.step
        rephrase_step = step.rephrase  # M8: Step-level rephrasing flag

        async def say_node(
            state: DialogueState,
            runtime: Runtime[RuntimeContext],
        ) -> dict[str, Any]:
            """Return the message as response via InformTask."""
            fm = runtime.context.flow_manager
            flow_id = fm.get_active_flow_id(state)

            # Idempotency check
            if flow_id:
                executed = (state.get("_executed_steps") or {}).get(flow_id, set())
                if step_id in executed:
                    # Already executed - skip to prevent duplicate messages
                    return {"_branch_target": None, "_pending_task": None}

            # Interpolate slots
            from soni.core.expression import evaluate_value as interpolate

            interpolated_message = interpolate(message, fm.get_all_slots(state))

            # M8: Rephrase if enabled
            try:
                final_message = await rephrase_if_enabled(
                    interpolated_message, state, runtime.context, rephrase_step
                )
            except Exception:
                # Fallback to original message if rephrasing fails
                final_message = interpolated_message

            # Build result with InformTask
            result: dict[str, Any] = {
                "_branch_target": None,
            }

            # Return InformTask for orchestrator to handle (non-blocking)
            if final_message:
                result["_pending_task"] = inform(
                    prompt=final_message,
                    wait_for_ack=False,
                )
            else:
                result["_pending_task"] = None

            # Mark as executed
            if flow_id:
                result["_executed_steps"] = {flow_id: {step_id}}

            return result

        say_node.__name__ = f"say_{step.step}"
        return say_node
