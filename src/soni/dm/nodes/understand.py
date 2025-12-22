"""Understand node for NLU processing (two-pass architecture).

ADR-002: This node now also processes flow-modifying commands (StartFlow, CancelFlow)
so that flow_stack is updated BEFORE execute_flow_node runs. This ensures
the state is persisted correctly when interrupt() is called.
"""

import sys
from typing import Any

from langchain_core.messages import HumanMessage
from langgraph.runtime import Runtime

from soni.core.types import DialogueState
from soni.du.models import CommandInfo, DialogueContext, FlowInfo
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
    - This ensures state is persisted before execute_flow_node's interrupt()
    - Other commands (SetSlot, etc.) are passed to execute_flow_node
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
                current_ctx = fm.get_active_context(local_state)
                if current_ctx and current_ctx["flow_name"] == flow_name:
                    sys.stderr.write(f"DEBUG: understand_node: flow {flow_name} already active\n")
                    continue

                sys.stderr.write(f"DEBUG: understand_node: pushing flow {flow_name}\n")
                _, delta = fm.push_flow(local_state, flow_name)
                merge_delta(updates, delta)
                # Update local state for subsequent commands
                if delta.flow_stack:
                    local_state["flow_stack"] = delta.flow_stack
                if delta.flow_slots:
                    from typing import cast

                    from soni.core.types import _merge_flow_slots

                    current_slots = cast(
                        dict[str, dict[str, Any]], local_state.get("flow_slots") or {}
                    )
                    local_state["flow_slots"] = _merge_flow_slots(current_slots, delta.flow_slots)
            # Don't pass StartFlow to execute_flow_node (already processed)

        elif cmd_type == "cancel_flow":
            stack = local_state.get("flow_stack")
            if stack:
                _, delta = fm.pop_flow(local_state)
                merge_delta(updates, delta)
                if delta.flow_stack is not None:
                    local_state["flow_stack"] = delta.flow_stack
            # Don't pass CancelFlow to execute_flow_node (already processed)

        else:
            # Pass other commands (SetSlot, Affirm, Deny, etc.) to execute_flow_node
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
