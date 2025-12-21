"""Execute node for M4 (NLU integration)."""

from typing import Any

from langgraph.runtime import Runtime
from langgraph.types import interrupt

from soni.core.types import DialogueState
from soni.flow.manager import merge_delta
from soni.runtime.context import RuntimeContext


async def execute_node(
    state: DialogueState,
    runtime: Runtime[RuntimeContext],
) -> dict[str, Any]:
    """Execute flows based on NLU commands.
    
    Processes commands from understand_node:
    - StartFlow: Push flow onto stack and execute
    - ChitChat: Return chitchat response (no flow needed)
    - CancelFlow: Pop current flow
    - SetSlot: Apply slot value (handled by subgraph)
    """
    subgraph = runtime.context.subgraph
    flow_manager = runtime.context.flow_manager
    config = runtime.context.config

    # Process NLU commands
    commands = state.get("commands", []) or []
    updates: dict[str, Any] = {}
    
    for cmd in commands:
        cmd_type = cmd.get("type")
        
        if cmd_type == "start_flow":
            flow_name = cmd.get("flow_name")
            if flow_name and flow_name in config.flows:
                _, delta = flow_manager.push_flow(state, flow_name)
                merge_delta(updates, delta)
                # Apply to state for subgraph execution
                if delta.flow_stack:
                    state["flow_stack"] = delta.flow_stack
                if delta.flow_slots:
                    state["flow_slots"] = delta.flow_slots
        
        elif cmd_type == "chitchat":
            # ChitChat: return message without executing flow
            message = cmd.get("message", "I'm here to help!")
            return {"response": message, "commands": []}
        
        elif cmd_type == "cancel_flow":
            # Cancel: pop current flow
            if state.get("flow_stack"):
                _, delta = flow_manager.pop_flow(state)
                merge_delta(updates, delta)
                return {**updates, "response": "Flow cancelled.", "commands": []}

    # No flow to execute?
    if not state.get("flow_stack"):
        return {"response": "I can help you. What would you like to do?", "commands": []}

    # Execute subgraph
    subgraph_state = dict(state)
    subgraph_state["_need_input"] = False

    while True:
        result = await subgraph.ainvoke(subgraph_state)

        if not result.get("_need_input"):
            # Merge updates and return response
            return {**updates, "response": result.get("response"), "commands": []}

        # Interrupt and get user response
        prompt = result["_pending_prompt"]
        user_response = interrupt(prompt)

        # Update state with result (flow_slots, etc.)
        subgraph_state.update(result)

        # Inject as command for next iteration
        message = (
            user_response if isinstance(user_response, str) else user_response.get("message", "")
        )
        subgraph_state["commands"] = [
            {"type": "set_slot", "slot": prompt["slot"], "value": message}
        ]

        # Clear flags
        subgraph_state["_need_input"] = False

