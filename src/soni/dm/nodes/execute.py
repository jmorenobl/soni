from typing import Any

from langgraph.runtime import Runtime

from soni.core.types import DialogueState
from soni.runtime.context import RuntimeContext


async def execute_node(
    state: DialogueState,
    runtime: Runtime[RuntimeContext],
) -> dict[str, Any]:
    """Execute the active flow's subgraph."""
    subgraph = runtime.context.subgraph
    result = await subgraph.ainvoke(state)
    return {"response": result.get("response")}
