"""CollectNodeFactory for M2."""

from typing import Any

from langgraph.runtime import Runtime

from soni.config.models import CollectStepConfig, StepConfig
from soni.core.types import DialogueState, NodeFunction
from soni.flow.manager import merge_delta
from soni.runtime.context import RuntimeContext


class CollectNodeFactory:
    """Factory for collect step nodes (SRP: slot collection only)."""

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

        async def collect_node(
            state: DialogueState,
            runtime: Runtime[RuntimeContext],
        ) -> dict[str, Any]:
            """Collect slot value from user."""
            # ISP: Use SlotProvider interface (FlowManager)
            fm = runtime.context.flow_manager

            # 1. Already filled?
            if fm.get_slot(state, slot_name):
                return {}

            # 2. Command provides value?
            commands = state.get("commands", []) or []

            for cmd in commands:
                if cmd.get("type") == "set_slot" and cmd.get("slot") == slot_name:
                    delta = fm.set_slot(state, slot_name, cmd["value"])
                    updates: dict[str, Any] = {"commands": []}  # Consume command
                    merge_delta(updates, delta)
                    return updates

            # 3. Need input
            return {
                "_need_input": True,
                "_pending_prompt": {"slot": slot_name, "prompt": prompt},
                "response": prompt,
            }

        collect_node.__name__ = f"collect_{step.step}"
        return collect_node
