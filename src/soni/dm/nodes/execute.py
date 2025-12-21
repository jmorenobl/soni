from typing import Any

from langgraph.runtime import Runtime
from langgraph.types import interrupt

from soni.compiler.subgraph import build_flow_subgraph
from soni.core.types import DialogueState
from soni.flow.manager import merge_delta
from soni.runtime.context import RuntimeContext

# Response constants (facilitates i18n and testing)
RESPONSE_CHITCHAT_DEFAULT = "I'm here to help!"
RESPONSE_CANCELLED = "Flow cancelled."
RESPONSE_NO_FLOW = "I can help you. What would you like to do?"


def _get_active_flow_name(state: DialogueState) -> str | None:
    """Get the name of the currently active flow."""
    stack = state.get("flow_stack", [])
    if stack:
        return stack[-1]["flow_name"]
    return None


async def execute_node(
    state: DialogueState,
    runtime: Runtime[RuntimeContext],
) -> dict[str, Any]:
    """Execute flows based on NLU commands.

    Supports link (flow transfer) and call (subflow with return).
    Dynamically rebuilds subgraph when active flow changes.
    """
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
            message = cmd.get("message", RESPONSE_CHITCHAT_DEFAULT)
            return {"response": message, "commands": []}

        elif cmd_type == "cancel_flow":
            if state.get("flow_stack"):
                _, delta = flow_manager.pop_flow(state)
                merge_delta(updates, delta)
                return {**updates, "response": RESPONSE_CANCELLED, "commands": []}

    # No flow to execute?
    if not state.get("flow_stack"):
        return {"response": RESPONSE_NO_FLOW, "commands": []}

    # Collect all responses from potentially multiple flows
    responses: list[str] = []
    # Use copy() to preserve TypedDict type information (cleaner than dict() + cast)
    subgraph_state = state.copy()
    subgraph_state["_need_input"] = False
    processed_flows: set[str] = set()  # Track to avoid infinite loops

    while True:
        subgraph_state["response"] = None  # Clear response to avoid duplicates

        # Get current flow and build its subgraph
        current_flow_name = _get_active_flow_name(subgraph_state)
        if not current_flow_name or current_flow_name not in config.flows:
            break

        flow_config = config.flows[current_flow_name]
        subgraph = build_flow_subgraph(flow_config)

        result = await subgraph.ainvoke(subgraph_state, context=runtime.context)

        # Collect response if any
        if result.get("response"):
            responses.append(result["response"])

        # Update subgraph_state with result
        subgraph_state.update(result)

        # Check if flow changed (link/call)

        if result.get("_need_input"):
            # Interrupt for user input
            prompt = result["_pending_prompt"]
            user_response = interrupt(prompt)

            # Inject as command for next iteration
            message = (
                user_response
                if isinstance(user_response, str)
                else user_response.get("message", "")
            )
            subgraph_state["commands"] = [
                {"type": "set_slot", "slot": prompt["slot"], "value": message}
            ]
            subgraph_state["_need_input"] = False
            # Allow re-processing current flow after input
            processed_flows.discard(current_flow_name)

        elif result.get("_flow_changed"):
            # Link or call changed flow - continue with new active flow
            processed_flows.add(current_flow_name)
            subgraph_state["_flow_changed"] = False
            subgraph_state["_branch_target"] = None  # Clear so new flow runs normally
            continue

        elif len(subgraph_state.get("flow_stack", [])) > 1:
            # Subflow completed - pop and continue parent
            processed_flows.add(current_flow_name)
            _, delta = flow_manager.pop_flow(subgraph_state)
            if delta.flow_stack:
                subgraph_state["flow_stack"] = delta.flow_stack
            merge_delta(updates, delta)
            # Continue to resume parent flow
            continue

        else:
            # Single flow completed - we're done
            break

    # Join all responses
    final_response = "\n".join(responses) if responses else None
    return {**updates, "response": final_response, "commands": []}
