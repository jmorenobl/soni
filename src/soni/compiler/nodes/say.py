import re
from typing import Any

from langgraph.runtime import Runtime

from soni.compiler.nodes.base import rephrase_if_enabled
from soni.config.models import SayStepConfig, StepConfig
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
            """Return the message as response."""
            fm = runtime.context.flow_manager
            flow_id = fm.get_active_flow_id(state)

            # Idempotency check (ADR-002 requirement)
            if flow_id:
                executed = (state.get("_executed_steps") or {}).get(flow_id, set())
                if step_id in executed:
                    # Already executed - skip to prevent duplicate messages
                    return {"_branch_target": None}

            # Interpolate slots
            def replace_slot(match: re.Match) -> str:
                slot_name = match.group(1)
                value = fm.get_slot(state, slot_name)
                return str(value) if value is not None else match.group(0)

            interpolated_message = re.sub(r"\{(\w+)\}", replace_slot, message)

            # M8: Rephrase if enabled
            final_message = await rephrase_if_enabled(
                interpolated_message, state, runtime.context, rephrase_step
            )

            from soni.core.pending_task import inform

            # Build response with idempotency tracking
            # UPDATED: Use InformTask for display (M5/M7 compatibility)
            result: dict[str, Any] = {
                "_pending_task": inform(prompt=final_message),
                "_branch_target": None,
            }

            # Mark as executed
            if flow_id:
                result["_executed_steps"] = {flow_id: {step_id}}

            return result

        say_node.__name__ = f"say_{step.step}"
        return say_node
