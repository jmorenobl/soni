"""BranchNodeFactory - generates conditional branching nodes."""

from typing import Any

from langchain_core.runnables import RunnableConfig
from langgraph.types import Command

from soni.compiler.nodes.base import NodeFunction
from soni.core.config import StepConfig
from soni.core.types import DialogueState


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
        # Note: 'jump_to' could be used as a default fallback if implemented

        async def branch_node(
            state: DialogueState,
            config: RunnableConfig,
        ) -> Command[Any] | dict[str, Any]:
            context = config["configurable"]["runtime_context"]
            flow_manager = context.flow_manager
            value = flow_manager.get_slot(state, slot_name)

            # Convert value to string for matching cases keys
            str_value = str(value) if value is not None else ""

            if str_value in cases:
                target = cases[str_value]
                # Return Command to jump to the target node
                return Command(goto=target)

            # If no match, return empty dict to proceed to next node in sequence
            return {}

        branch_node.__name__ = f"branch_{step.step}"
        return branch_node
