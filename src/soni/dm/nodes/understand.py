"""Understand node - processes input."""
from typing import Any
from langchain_core.runnables import RunnableConfig

from soni.core.types import DialogueState, RuntimeContext
from soni.du.models import DialogueContext, Command, FlowInfo, CommandInfo
from soni.du.modules import SoniDU


def build_du_context(state: DialogueState, context: RuntimeContext) -> DialogueContext:
    """Construct NLU context from state."""
    config = context.config
    fm = context.flow_manager
    
    # 1. Available flows
    # config.flows is dict[str, FlowConfig]
    # FlowInfo needs name, description, trigger_intents
    # FlowConfig has description. It doesn't have trigger_examples? 
    # Assume flow name/desc is enough for now or use placeholders
    
    available_flows = []
    if hasattr(config, "flows"):
         for name, flow_cfg in config.flows.items():
            # TODO: Add trigger examples to FlowConfig explicitly?
            # For now use description as trigger info
            available_flows.append(FlowInfo(
                name=name,
                description=flow_cfg.description,
                trigger_intents=[f"start {name}", name] # heuristic
            ))
            
    # 2. Available commands
    # Fixed list for now
    available_commands = [
        CommandInfo(command_type="start_flow", description="Start a new flow"),
        CommandInfo(command_type="set_slot", description="Set a slot value"),
    ]
    
    # 3. Active flow
    curr_ctx = fm.get_active_context(state)
    active_flow = curr_ctx["flow_name"] if curr_ctx else None
    
    # 4. Slots
    slots = []
    # TODO: add current slots
    
    return DialogueContext(
        available_flows=available_flows,
        available_commands=available_commands,
        active_flow=active_flow,
        current_slots=slots,
        conversation_state="idle" if not active_flow else "collecting",
    )


async def understand_node(
    state: DialogueState,
    config: RunnableConfig,
) -> dict[str, Any]:
    """Process user input via NLU."""
    # 1. Get Context
    context: RuntimeContext = config["configurable"]["runtime_context"]
    du: SoniDU = context.du
    fm = context.flow_manager
    
    # 2. Build DU Context & Run NLU
    du_ctx = build_du_context(state, context)
    nlu_out = await du.aforward(state.get("user_message", ""), du_ctx)
    
    # 3. Process Commands (Update State)
    # We apply them to 'state' object here, then return the Modified keys
    commands = nlu_out.commands
    
    for cmd in commands:
        if cmd.command_type == "start_flow" and cmd.flow_name:
            # Check availability logic? For now just push.
            # Handle intent change (pushes flow)
            await fm.handle_intent_change(state, cmd.flow_name)
            
        elif cmd.command_type == "set_slot" and cmd.slot_name:
            fm.set_slot(state, cmd.slot_name, cmd.slot_value)
            
    # 4. Return updates
    # Must return keys that changed so LangGraph keeps them
    # FlowManager modifies flow_stack and flow_slots in place
    return {
        "commands": commands,
        "flow_stack": state["flow_stack"],
        "flow_slots": state["flow_slots"]
    }
