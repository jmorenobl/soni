"""LinkNodeFactory for M6 (flow transfer without return)."""

from typing import Any

from langgraph.runtime import Runtime

from soni.config.models import LinkStepConfig, StepConfig
from soni.core.types import DialogueState, NodeFunction
from soni.flow.manager import merge_delta
from soni.runtime.context import RuntimeContext


class LinkNodeFactory:
    """Factory for link step nodes (SRP: flow transfer only).

    Link pops the current flow and pushes the target flow.
    There is no return - control is transferred permanently.
    Sets _flow_changed flag to signal early exit from subgraph.
    """

    def create(
        self,
        step: StepConfig,
        all_steps: list[StepConfig] | None = None,
        step_index: int | None = None,
    ) -> NodeFunction:
        """Create a link node function."""
        if not isinstance(step, LinkStepConfig):
            raise ValueError(f"LinkNodeFactory received wrong step type: {type(step).__name__}")

        target_flow = step.target
        step_id = step.step

        async def link_node(
            state: DialogueState,
            runtime: Runtime[RuntimeContext],
        ) -> dict[str, Any]:
            """Link to another flow (no return)."""
            fm = runtime.context.flow_manager
            flow_id = fm.get_active_flow_id(state)

            # Idempotency check
            if flow_id:
                executed = (state.get("_executed_steps") or {}).get(flow_id, set())
                if step_id in executed:
                    return {"_branch_target": None}

            # Signal flow change to exit subgraph early
            updates: dict[str, Any] = {"_flow_changed": True, "_branch_target": "__end__"}
            if flow_id:
                updates["_executed_steps"] = {flow_id: {step_id}}

            # Pop current flow
            if state.get("flow_stack"):
                _, pop_delta = fm.pop_flow(state)
                merge_delta(updates, pop_delta)
                if pop_delta.flow_stack is not None:
                    state["flow_stack"] = pop_delta.flow_stack

            # Push target flow
            _, push_delta = fm.push_flow(state, target_flow)
            merge_delta(updates, push_delta)

            return updates

        link_node.__name__ = f"link_{step.step}"
        return link_node
