"""BranchNodeFactory - generates conditional branching nodes."""

from typing import Any

from langchain_core.runnables import RunnableConfig

from soni.compiler.nodes.base import NodeFunction
from soni.core.config import StepConfig
from soni.core.types import DialogueState, get_runtime_context


class BranchNodeFactory:
    """Factory for branch step nodes."""

    def create(self, step: StepConfig) -> NodeFunction:
        """Create a node that branches based on a slot value."""
        if not step.slot:
            raise ValueError(f"Step {step.step} of type 'branch' missing required field 'slot'")
        if not step.cases:
            raise ValueError(f"Step {step.step} of type 'branch' missing required field 'cases'")

        slot_name = step.slot
        cases = step.cases
        step_name = step.step

        async def branch_node(
            state: DialogueState,
            config: RunnableConfig,
        ) -> dict[str, Any]:
            """Evaluate branch condition and set target for router."""
            context = get_runtime_context(config)
            flow_manager = context.flow_manager
            value = flow_manager.get_slot(state, slot_name)

            # Convert value to string for matching cases keys
            str_value = str(value) if value is not None else ""

            if str_value in cases:
                target = cases[str_value]
                # Store branch target for the router to use
                return {"_branch_target": target}

            # No match - clear any previous target to proceed to next node
            return {"_branch_target": None}

        branch_node.__name__ = f"branch_{step_name}"
        return branch_node
