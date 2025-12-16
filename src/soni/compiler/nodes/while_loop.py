"""WhileNodeFactory - generates loop guard nodes.

Uses expression evaluator for complex conditions like:
- age > 18
- status == 'approved' AND amount < 5000
- items (truthiness check)
"""

from typing import Any

from langchain_core.runnables import RunnableConfig
from langgraph.types import Command

from soni.compiler.nodes.base import NodeFunction
from soni.core.config import StepConfig
from soni.core.expression import evaluate_condition
from soni.core.types import DialogueState, get_runtime_context


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

        async def while_node(
            state: DialogueState,
            config: RunnableConfig,
        ) -> Command[Any] | dict[str, Any]:
            """Evaluate condition and route to loop body or exit."""
            context = get_runtime_context(config)
            flow_manager = context.flow_manager

            # Get all slots for condition evaluation
            slots = flow_manager.get_all_slots(state)

            # Evaluate condition using expression evaluator
            is_true = evaluate_condition(condition, slots)

            if is_true:
                return Command(goto=loop_body_start)

            # If false, proceed to next node (exit loop)
            return {}

        while_node.__name__ = f"while_{step.step}"
        return while_node
