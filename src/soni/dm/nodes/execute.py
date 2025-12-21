from typing import Any

from langgraph.runtime import Runtime
from langgraph.types import interrupt

from soni.core.types import DialogueState
from soni.runtime.context import RuntimeContext


async def execute_node(
    state: DialogueState,
    runtime: Runtime[RuntimeContext],
) -> dict[str, Any]:
    """Execute the active flow's subgraph with interrupt handling."""
    subgraph = runtime.context.subgraph
    flow_manager = runtime.context.flow_manager

    # Auto-push first flow if stack empty (Temporary for M2/M3 until NLU)
    if not state.get("flow_stack"):
        # Default to "greet" for M2 test
        _, delta = flow_manager.push_flow(state, "greet")
        # Apply delta to local state copy
        if delta.flow_stack:
            state["flow_stack"] = delta.flow_stack
        if delta.flow_slots:
            state["flow_slots"] = delta.flow_slots

    subgraph_state = dict(state)
    subgraph_state["_need_input"] = False

    while True:
        result = await subgraph.ainvoke(subgraph_state)

        if not result.get("_need_input"):
            return {"response": result.get("response")}

        # Interrupt and get user response
        prompt = result["_pending_prompt"]
        user_response = interrupt(prompt)

        # Update state with result (flow_slots, etc.)
        subgraph_state.update(result)

        # Inject as command for next iteration
        message = (
            user_response if isinstance(user_response, str) else user_response.get("message", "")
        )
        # FIX: Ensure it is a valid list of dicts
        subgraph_state["commands"] = [
            {"type": "set_slot", "slot": prompt["slot"], "value": message}
        ]

        # Clear flags
        subgraph_state["_need_input"] = False
