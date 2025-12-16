"""Execute node - routes to active flow."""
from typing import Any, Literal

from langgraph.runtime import Runtime
from langgraph.types import Command

from soni.core.types import DialogueState, RuntimeContext


async def execute_node(
    state: DialogueState,
    runtime: Runtime[RuntimeContext],
) -> Command[Literal["respond", "understand"]] | dict[str, Any]: # type: ignore
    """Determine execution path based on stack."""

    flow_manager = runtime.context.flow_manager
    active_ctx = flow_manager.get_active_context(state)

    if active_ctx:
        # Route to the subgraph node for this flow
        # Node name convention: flow_{flow_name}
        target = f"flow_{active_ctx['flow_name']}"
        return Command(goto=target)

    # If no active flow, go to respond (or handle idle state)
    return Command(goto="respond")
