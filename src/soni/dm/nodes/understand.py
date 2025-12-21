"""Understand node for NLU processing."""

from typing import Any

from langgraph.runtime import Runtime

from soni.core.types import DialogueState
from soni.runtime.context import RuntimeContext


async def understand_node(
    state: DialogueState,
    runtime: Runtime[RuntimeContext],
) -> dict[str, Any]:
    """Process user message through NLU.
    
    Uses SoniDU (DSPy) to extract commands from user message.
    Commands are serialized to state for consumption by execute_node.
    """
    du = runtime.context.du
    config = runtime.context.config
    fm = runtime.context.flow_manager
    
    user_message = state.get("user_message", "")
    if not user_message:
        return {"commands": []}
    
    # Build dialogue context for NLU
    from soni.du.models import CommandInfo, DialogueContext, FlowInfo
    
    # Format available flows as FlowInfo objects
    flows_info = []
    for name, flow in config.flows.items():
        flows_info.append(FlowInfo(
            name=name,
            description=flow.description or name,
            trigger_intents=[],
        ))
    
    # Available commands (static list for now)
    commands_info = [
        CommandInfo(command_type="start_flow", description="Start a new flow"),
        CommandInfo(command_type="set_slot", description="Set a slot value"),
        CommandInfo(command_type="cancel_flow", description="Cancel current flow"),
        CommandInfo(command_type="chitchat", description="Off-topic message"),
    ]
    
    # Get active flow info
    active_ctx = fm.get_active_context(state)
    active_flow = active_ctx["flow_name"] if active_ctx else None
    
    # Get expected slot if waiting for input
    expected_slot = None
    pending = state.get("_pending_prompt")
    if pending:
        expected_slot = pending.get("slot")
    
    context = DialogueContext(
        available_flows=flows_info,
        available_commands=commands_info,
        active_flow=active_flow,
        expected_slot=expected_slot,
    )
    
    # Get commands from NLU
    try:
        nlu_result = await du.acall(user_message, context)
        # Serialize commands for state storage
        serialized = [cmd.model_dump() for cmd in nlu_result.commands]
        return {"commands": serialized}
    except Exception:
        # On NLU failure, return empty commands
        return {"commands": []}
