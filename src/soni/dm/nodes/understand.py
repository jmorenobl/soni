"""Understand node - processes input."""

from typing import Any

from langchain_core.runnables import RunnableConfig

from soni.core.types import DialogueState, RuntimeContext, get_runtime_context
from soni.du.models import CommandInfo, DialogueContext, FlowInfo, SlotValue


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
            # Use trigger_intents from YAML or fallback to heuristic
            trigger_intents = flow_cfg.trigger_intents or [f"start {name}", name]
            available_flows.append(
                FlowInfo(
                    name=name,
                    description=flow_cfg.description,
                    trigger_intents=trigger_intents,
                )
            )

    # 2. Available commands
    # Include required_fields so LLM knows what to provide
    available_commands = [
        CommandInfo(
            command_type="start_flow",
            description="Start a new flow. flow_name must match one of available_flows.name",
            required_fields=["flow_name"],
            example='{"type": "start_flow", "flow_name": "check_balance"}',
        ),
        CommandInfo(
            command_type="set_slot",
            description="Set a slot value when user provides information",
            required_fields=["slot", "value"],
            example='{"type": "set_slot", "slot": "account_type", "value": "checking"}',
        ),
    ]

    # 3. Active flow and expected slot
    curr_ctx = fm.get_active_context(state)
    active_flow = curr_ctx["flow_name"] if curr_ctx else None
    expected_slot = state.get("waiting_for_slot")  # Set by collect/confirm nodes

    # 4. Current slots - convert from dict to SlotValue list
    current_slots: list[SlotValue] = []
    if curr_ctx:
        flow_id = curr_ctx["flow_id"]
        slot_dict = state.get("flow_slots", {}).get(flow_id, {})
        for slot_name, slot_value in slot_dict.items():
            # Skip internal slots (prefixed with __)
            if not slot_name.startswith("__"):
                current_slots.append(
                    SlotValue(name=slot_name, value=str(slot_value) if slot_value else None)
                )

    return DialogueContext(
        available_flows=available_flows,
        available_commands=available_commands,
        active_flow=active_flow,
        current_slots=current_slots,
        expected_slot=expected_slot,
        conversation_state="idle" if not active_flow else "collecting",
    )


async def understand_node(
    state: DialogueState,
    config: RunnableConfig,
) -> dict[str, Any]:
    """Process user input via NLU."""
    # 1. Get Context
    context = get_runtime_context(config)
    du = context.du  # DUProtocol
    fm = context.flow_manager

    # 2. Build DU Context & Run NLU
    du_ctx = build_du_context(state, context)
    user_message = state.get("user_message") or ""
    nlu_out = await du.aforward(user_message, du_ctx)

    # 3. Process Commands (Update State)
    # We apply them to 'state' object here, then return the Modified keys
    commands = nlu_out.commands

    for cmd in commands:
        if cmd.type == "start_flow" and hasattr(cmd, "flow_name"):
            # Check availability logic? For now just push.
            # Handle intent change (pushes flow)
            await fm.handle_intent_change(state, cmd.flow_name)

        elif cmd.type == "set_slot" and hasattr(cmd, "slot"):
            await fm.set_slot(state, cmd.slot, cmd.value)

    # 4. Return updates
    # Must return keys that changed so LangGraph keeps them
    # FlowManager modifies flow_stack and flow_slots in place
    return {
        "flow_state": state.get("flow_state"),
        "waiting_for_slot": state.get("waiting_for_slot"),
        "flow_slots": state.get("flow_slots"),
        "flow_stack": state.get("flow_stack"),
        "commands": [cmd.model_dump() for cmd in commands],
        "metadata": state.get("metadata", {}),
    }
