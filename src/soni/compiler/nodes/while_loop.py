"""WhileNodeFactory - generates loop guard nodes."""

from typing import Any, Literal

from langchain_core.runnables import RunnableConfig
from langgraph.types import Command

from soni.compiler.nodes.base import NodeFunction
from soni.core.config import StepConfig
from soni.core.types import DialogueState


class WhileNodeFactory:
    """Factory for while loop nodes."""

    def create(self, step: StepConfig) -> NodeFunction:
        """Create a node that acts as a while loop guard."""
        if not step.condition:
            raise ValueError(f"Step {step.step} of type 'while' missing required field 'condition'")
        if not step.do:
            raise ValueError(f"Step {step.step} of type 'while' missing required field 'do'")

        condition = step.condition
        loop_body_start = step.do[0]  # The first step in the 'do' block

        # NOTE: This assumes the subgraph builder will wire loop_body_start correctly

        async def while_node(
            state: DialogueState,
            config: RunnableConfig,
        ) -> Command[Literal[loop_body_start]] | dict[str, Any]:  # type: ignore
            # TODO: Implement actual condition evaluation logic (e.g. using simple eval or expression parser)
            # For now, we assume simple slot truthiness check if condition is just a slot name
            # Or always false to prevent infinite loops in initial implementation if complex

            # Simple condition parser: "slot_name == value" or just "slot_name"
            # This is a placeholder for real logic
            is_true = False

            parts = condition.split("==")

            context = config["configurable"]["runtime_context"]
            flow_manager = context.flow_manager

            if len(parts) == 2:
                slot = parts[0].strip()
                val = parts[1].strip().strip("'").strip('"')
                actual = str(flow_manager.get_slot(state, slot))
                is_true = actual == val
            else:
                # Existence check
                slot = condition.strip()
                is_true = flow_manager.get_slot(state, slot) is not None

            if is_true:
                return Command(goto=loop_body_start)

            # If false, proceed to next node (exit loop)
            return {}

        while_node.__name__ = f"while_{step.step}"
        return while_node
