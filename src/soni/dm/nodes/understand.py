"""Understand node for NLU processing (two-pass architecture)."""

from typing import Any

from langgraph.runtime import Runtime

from soni.core.types import DialogueState
from soni.du.models import CommandInfo, DialogueContext, FlowInfo
from soni.du.slot_extractor import SlotExtractionInput
from soni.runtime.context import RuntimeContext


async def understand_node(
    state: DialogueState,
    runtime: Runtime[RuntimeContext],
) -> dict[str, Any]:
    """Process user message through two-pass NLU.

    Two-pass architecture:
    1. Pass 1: Intent detection (SoniDU) - determines command type
    2. Pass 2: Slot extraction (SlotExtractor) - only if StartFlow detected

    Commands are serialized to state for consumption by execute_node.
    """
    du = runtime.context.du
    slot_extractor = runtime.context.slot_extractor
    config = runtime.context.config
    fm = runtime.context.flow_manager

    user_message = state.get("user_message", "")
    if not user_message:
        return {"commands": []}

    # Build dialogue context for Pass 1
    flows_info = [
        FlowInfo(
            name=name,
            description=flow.description or name,
            trigger_intents=[],
        )
        for name, flow in config.flows.items()
    ]

    commands_info = [
        CommandInfo(command_type="start_flow", description="Start a new flow"),
        CommandInfo(command_type="set_slot", description="Set a slot value"),
        CommandInfo(command_type="cancel_flow", description="Cancel current flow"),
        CommandInfo(command_type="chitchat", description="Off-topic message"),
    ]

    active_ctx = fm.get_active_context(state)
    active_flow = active_ctx["flow_name"] if active_ctx else None

    pending = state.get("_pending_prompt")
    expected_slot = pending.get("slot") if pending else None

    context = DialogueContext(
        available_flows=flows_info,
        available_commands=commands_info,
        active_flow=active_flow,
        expected_slot=expected_slot,
    )

    # Get conversation history
    messages = state.get("messages", [])
    history = [
        {"role": "user" if hasattr(m, "type") and m.type == "human" else "assistant",
         "content": m.content if hasattr(m, "content") else str(m)}
        for m in messages[-10:]  # Last 10 messages for context
    ]

    # PASS 1: Intent detection
    try:
        nlu_result = await du.acall(user_message, context, history)
        commands = list(nlu_result.commands)
    except Exception:
        return {"commands": []}

    # PASS 2: Slot extraction (only if StartFlow detected)
    start_flow_cmd = next(
        (cmd for cmd in commands if getattr(cmd, "type", None) == "start_flow"),
        None
    )

    if start_flow_cmd:
        flow_name = getattr(start_flow_cmd, "flow_name", None)
        if flow_name and flow_name in config.flows:
            flow_config = config.flows[flow_name]
            # Build slot definitions from flow config
            slot_definitions = _get_slot_definitions(flow_config)

            if slot_definitions:
                try:
                    slot_commands = await slot_extractor.acall(user_message, slot_definitions)
                    commands.extend(slot_commands)
                except Exception:
                    pass  # Continue without slot extraction on failure

    # Serialize commands for state storage
    serialized = [cmd.model_dump() for cmd in commands]
    return {"commands": serialized}


def _get_slot_definitions(flow_config) -> list[SlotExtractionInput]:
    """Extract slot definitions from flow config for SlotExtractor."""
    from soni.config.models import CollectStepConfig

    definitions = []
    for step in flow_config.steps:
        if isinstance(step, CollectStepConfig):
            definitions.append(
                SlotExtractionInput(
                    name=step.slot,
                    slot_type="string",  # Default type
                    description=step.message or f"Value for {step.slot}",
                    examples=[],
                )
            )
    return definitions

