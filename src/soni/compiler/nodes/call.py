"""CallNodeFactory for M6 (subflow invocation with return)."""

from typing import Any

from langgraph.runtime import Runtime

from soni.config.models import CallStepConfig, StepConfig
from soni.core.types import DialogueState, NodeFunction
from soni.flow.manager import merge_delta
from soni.runtime.context import RuntimeContext


class CallNodeFactory:
    """Factory for call step nodes (SRP: subflow invocation only).

    Call pushes the target flow onto the stack while keeping the current flow.
    When the called flow completes, control returns to the caller.
    Sets _flow_changed to signal subgraph transition.
    """

    def create(
        self,
        step: StepConfig,
        all_steps: list[StepConfig] | None = None,
        step_index: int | None = None,
    ) -> NodeFunction:
        """Create a call node function."""
        if not isinstance(step, CallStepConfig):
            raise ValueError(f"CallNodeFactory received wrong step type: {type(step).__name__}")

        target_flow = step.target
        step_id = step.step

        async def call_node(
            state: DialogueState,
            runtime: Runtime[RuntimeContext],
        ) -> dict[str, Any]:
            """Call a subflow (with return)."""
            fm = runtime.context.flow_manager
            flow_id = fm.get_active_flow_id(state)

            # Idempotency check: skip if already executed to prevent infinite loops on resume
            if flow_id:
                executed = (state.get("_executed_steps") or {}).get(flow_id, set())
                if step_id in executed:
                    return {"_branch_target": None}

            # Signal flow change to exit subgraph, and mark step executed
            updates: dict[str, Any] = {
                "_flow_changed": True,
                "_branch_target": "__end__",
                "_pending_task": None,
            }
            if flow_id:
                updates["_executed_steps"] = {flow_id: {step_id}}

            # Push target flow onto stack (current stays for return)
            _, delta = fm.push_flow(state, target_flow)
            merge_delta(updates, delta)

            return updates

        call_node.__name__ = f"call_{step.step}"
        return call_node
