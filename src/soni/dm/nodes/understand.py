"""Understand node for NLU processing (two-pass architecture).

ADR-002: This node now also processes flow-modifying commands (StartFlow, CancelFlow)
so that flow_stack is updated BEFORE orchestrator runs. This ensures
the state is persisted correctly when interrupt() is called.
"""

from typing import Any, Literal, cast

from langchain_core.messages import HumanMessage
from langgraph.runtime import Runtime

from soni.core.types import DialogueState, _merge_flow_slots
from soni.du.models import CommandInfo, DialogueContext, FlowInfo, SlotDefinition, SlotValue
from soni.du.slot_extractor import SlotExtractionInput
from soni.flow.manager import merge_delta
from soni.runtime.context import RuntimeContext


async def understand_node(
    state: DialogueState,
    runtime: Runtime[RuntimeContext],
) -> dict[str, Any]:
    """Process user message through two-pass NLU and apply flow commands.

    Two-pass architecture:
    1. Pass 1: Intent detection (SoniDU) - determines command type
    2. Pass 2: Slot extraction (SlotExtractor) - only if StartFlow detected

    ADR-002 Enhancement:
    - StartFlow commands are processed here to update flow_stack
    - This ensures state is persisted before orchestrator's interrupt()
    - Other commands (SetSlot, etc.) are passed to orchestrator
    """
    du = runtime.context.nlu_provider
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
            trigger_intents=getattr(flow, "trigger_intents", None) or [],
        )
        for name, flow in config.flows.items()
    ]

    commands_info = [
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
        CommandInfo(command_type="cancel_flow", description="Cancel current flow"),
        CommandInfo(command_type="chitchat", description="Off-topic message"),
        CommandInfo(command_type="affirm", description="User confirms/agrees"),
        CommandInfo(command_type="deny", description="User denies/disagrees"),
    ]

    active_ctx = fm.get_active_context(state)
    active_flow = active_ctx["flow_name"] if active_ctx else None

    pending_task = state.get("_pending_task")
    expected_slot = None
    if pending_task:
        if isinstance(pending_task, dict):
            expected_slot = (
                pending_task.get("slot") if pending_task.get("type") == "collect" else None
            )
        else:
            expected_slot = (
                getattr(pending_task, "slot", None)
                if getattr(pending_task, "type", None) == "collect"
                else None
            )

    # Build flow_slots from active flow's collect steps (as SlotDefinition for NLU context)
    flow_slots_defs: list[SlotDefinition] = []
    if active_flow and active_flow in config.flows:
        for slot_input in _get_slot_definitions(config.flows[active_flow]):
            flow_slots_defs.append(
                SlotDefinition(
                    name=slot_input.name,
                    slot_type=slot_input.slot_type,
                    description=slot_input.description,
                    examples=slot_input.examples,
                )
            )

    # Build current_slots from flow state
    current_slots = _get_current_slots(state, fm)

    # Determine conversation state
    if not active_flow:
        conversation_state = "idle"
    elif expected_slot:
        conversation_state = "collecting"
    else:
        conversation_state = "collecting"  # Active flow = collecting by default

    context = DialogueContext(
        available_flows=flows_info,
        available_commands=commands_info,
        active_flow=active_flow,
        flow_slots=flow_slots_defs,
        current_slots=current_slots,
        expected_slot=cast(str | None, expected_slot),
        conversation_state=cast(
            Literal["idle", "collecting", "confirming", "action_pending"], conversation_state
        ),
    )

    # Get conversation history
    messages = state.get("messages", [])
    history = [
        {
            "role": "user" if hasattr(m, "type") and m.type == "human" else "assistant",
            "content": m.content if hasattr(m, "content") else str(m),
        }
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
        (cmd for cmd in commands if getattr(cmd, "type", None) == "start_flow"), None
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

    # ADR-002: Process flow-modifying commands HERE to persist before interrupt
    updates: dict[str, Any] = {}
    remaining_commands: list[dict] = []
    local_state = dict(state)  # Work with a copy for delta calculations

    for cmd in commands:
        cmd_dict = cmd.model_dump() if hasattr(cmd, "model_dump") else dict(cmd)
        cmd_type = cmd_dict.get("type")

        if cmd_type == "start_flow":
            flow_name = cmd_dict.get("flow_name")
            if flow_name and flow_name in config.flows:
                # Check if same flow already active
                current_ctx = fm.get_active_context(cast(DialogueState, local_state))
                if current_ctx and current_ctx["flow_name"] == flow_name:
                    continue

                _, delta = fm.push_flow(cast(DialogueState, local_state), flow_name)
                merge_delta(updates, delta)
                # Update local state for subsequent commands
                if delta.flow_stack:
                    local_state["flow_stack"] = delta.flow_stack
                if delta.flow_slots:
                    active_slots = cast(
                        dict[str, dict[str, Any]], local_state.get("flow_slots") or {}
                    )
                    local_state["flow_slots"] = _merge_flow_slots(active_slots, delta.flow_slots)
            # Don't pass StartFlow to orchestrator (already processed)

        elif cmd_type == "cancel_flow":
            stack = local_state.get("flow_stack")
            if stack:
                _, delta = fm.pop_flow(cast(DialogueState, local_state))
                merge_delta(updates, delta)
                if delta.flow_stack is not None:
                    local_state["flow_stack"] = delta.flow_stack
            # Don't pass CancelFlow to orchestrator (already processed)

        else:
            # Pass other commands (SetSlot, Affirm, Deny, etc.) to orchestrator
            remaining_commands.append(cmd_dict)

    return {
        **updates,
        "commands": remaining_commands,
        "messages": [HumanMessage(content=user_message)],
    }


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


def _get_current_slots(state: DialogueState, fm) -> list[SlotValue]:
    """Get current slot values from flow state.

    Converts the flow_slots dict to a list of SlotValue objects
    for the NLU context.
    """
    active_ctx = fm.get_active_context(state)
    if not active_ctx:
        return []

    flow_id = active_ctx["flow_id"]
    flow_slots = state.get("flow_slots", {})
    if not flow_slots:
        return []

    slot_dict = flow_slots.get(flow_id, {})
    return [
        SlotValue(name=name, value=str(value) if value is not None else None)
        for name, value in slot_dict.items()
        if not name.startswith("_")  # Skip internal slots
    ]
