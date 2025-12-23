"""Routing functions for orchestrator graph."""

from typing import Literal

from soni.core.types import DialogueState


def route_after_orchestrator(
    state: DialogueState,
) -> Literal["pending_task", "end"]:
    """Determine next step after orchestrator.

    If there's a pending task requiring user input, loop back to human_input_gate.
    Otherwise, end the graph execution.
    """
    pending = state.get("_pending_task")
    if pending:
        return "pending_task"
    return "end"
