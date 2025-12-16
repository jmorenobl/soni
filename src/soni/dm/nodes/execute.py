"""Execute node - routes to active flow."""
from typing import Any, Literal


from langgraph.types import Command

from soni.core.types import DialogueState, RuntimeContext


from langchain_core.runnables import RunnableConfig

async def execute_node(
    state: DialogueState,
    config: RunnableConfig,
) -> Command[Literal["respond", "understand"]] | dict[str, Any]: # type: ignore
    """Determine execution path based on stack."""
    
    context: RuntimeContext = config["configurable"]["runtime_context"]
    flow_manager = context.flow_manager
    active_ctx = flow_manager.get_active_context(state)

    if active_ctx:
        # Route to the subgraph node for this flow
        # Node name convention: flow_{flow_name}
        target = f"flow_{active_ctx['flow_name']}"
        return Command(goto=target)

    # If no active flow, go to respond (or handle idle state)
    return Command(goto="respond")
