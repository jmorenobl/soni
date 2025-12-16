"""Execute node - routes to active flow."""

from typing import Any

from langchain_core.runnables import RunnableConfig
from langgraph.types import Command

from soni.core.types import DialogueState, RuntimeContext


async def execute_node(
    state: DialogueState,
    config: RunnableConfig,
) -> Command[Any] | dict[str, Any]:
    """Determine execution path based on stack.

    Uses dynamic goto for flow subgraphs.
    """
    context: RuntimeContext = config["configurable"]["runtime_context"]
    flow_manager = context.flow_manager
    # Check if we have an active flow
    active_ctx = flow_manager.get_active_context(state)
    if active_ctx:
        # Route to the subgraph node for this flow
        # Node name convention: flow_{flow_name}
        target = f"flow_{active_ctx['flow_name']}"
        return Command(goto=target)

    # If no active flow, go to respond (or handle idle state)
    return Command(goto="respond")
