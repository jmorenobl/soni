"""Execute flow node with proper interrupt orchestration (ADR-002).

This module implements the "Invoke Graph from Node" pattern where interrupt()
is called at the orchestrator level, not inside subgraphs.

The flow is:
    1. Get active flow from stack
    2. Invoke subgraph
    3. If subgraph returns _need_input:
        a. interrupt() with prompt
        b. On resume, run NLU on user response
        c. Loop back to step 2 with new commands
    4. If subgraph completes, merge results and return
"""

import sys
from typing import Any, Literal, cast

from langchain_core.messages import AIMessage, HumanMessage
from langgraph.runtime import Runtime
from langgraph.types import interrupt

from soni.core.types import DialogueState
from soni.flow.manager import merge_delta
from soni.runtime.context import RuntimeContext

# Response constants
RESPONSE_CHITCHAT_DEFAULT = "I'm here to help!"
RESPONSE_CANCELLED = "Flow cancelled."
RESPONSE_NO_FLOW = "I can help you. What would you like to do?"


async def execute_flow_node(
    state: DialogueState,
    runtime: Runtime[RuntimeContext],
) -> dict[str, Any]:
    """Execute flows with interrupt orchestration (ADR-002).

    This node:
    1. Invokes the active flow's subgraph (flow stack already set by understand_node)
    2. Handles interrupts for user input at THIS level
    3. Runs NLU on resumed input to get new commands
    4. Loops until flow completes or no more input needed

    NOTE: StartFlow and CancelFlow are processed by understand_node.
    This node only handles SetSlot, Affirm, Deny, and similar commands.
    """
    du = runtime.context.nlu_provider
    ctx = runtime.context
    fm = ctx.flow_manager
    config = ctx.config
    subgraph_registry = ctx.subgraph_registry

    # Commands are passed from understand_node (SetSlot, Affirm, Deny, etc.)
    # StartFlow and CancelFlow are already processed by understand_node
    commands = state.get("commands") or []
    updates: dict[str, Any] = {}

    # Handle chitchat (no flow execution needed)
    for cmd in commands:
        if cmd.get("type") == "chitchat":
            message = cmd.get("message", RESPONSE_CHITCHAT_DEFAULT)
            return {"response": message, "commands": []}

    # No active flow?
    stack = state.get("flow_stack")
    if not stack:
        return {"response": RESPONSE_NO_FLOW, "commands": []}

    active_flow = stack[-1]
    flow_name = active_flow["flow_name"]

    subgraph = subgraph_registry.get(flow_name)
    if not subgraph:
        return {"response": RESPONSE_NO_FLOW, "commands": []}

    # Prepare subgraph state
    subgraph_state: dict[str, Any] = {
        "user_message": state.get("user_message"),
        "messages": state.get("messages") or [],
        "response": None,
        "flow_stack": state.get("flow_stack"),
        "flow_slots": state.get("flow_slots") or {},
        "commands": commands,  # Pass commands for collect/confirm to process
        "_need_input": False,
        "_pending_prompt": None,
        "_executed_steps": state.get("_executed_steps") or {},
        "_branch_target": None,
        "_flow_changed": False,
        "_loop_flag": False,
        "_pending_responses": None,
    }

    # Clear consumed commands from updates
    updates["commands"] = []

    # Main execution loop
    responses: list[str] = []

    while True:
        # Invoke subgraph
        try:
            result = await subgraph.ainvoke(
                subgraph_state,
                context=ctx,
            )
        except Exception as e:
            sys.stderr.write(f"DEBUG: Subgraph {flow_name} failed: {e}\n")
            import traceback

            traceback.print_exc(file=sys.stderr)
            raise

        # Collect response
        subgraph_responses = result.get("_pending_responses") or []
        if not subgraph_responses and result.get("response"):
            subgraph_responses = [result["response"]]

        responses.extend(subgraph_responses)

        # Check for flow change (link/call executed)
        if result.get("_flow_changed"):
            # Update state with new flow stack from result
            new_stack = result.get("flow_stack") or []
            subgraph_state["flow_stack"] = new_stack
            subgraph_state["flow_slots"] = result.get("flow_slots") or {}
            subgraph_state["_executed_steps"] = result.get("_executed_steps") or {}
            subgraph_state["_flow_changed"] = False
            subgraph_state["commands"] = []  # Consume commands

            # Update updates dict with new stack
            updates["flow_stack"] = new_stack
            updates["flow_slots"] = result.get("flow_slots") or {}
            updates["_executed_steps"] = result.get("_executed_steps") or {}

            # Switch to new flow's subgraph
            if new_stack:
                new_flow_name = new_stack[-1]["flow_name"]
                if new_flow_name:
                    subgraph = subgraph_registry.get(new_flow_name)
                    flow_name = new_flow_name
                    active_flow = new_stack[-1]
                    continue
            # No new flow - exit
            break

        # Flow completed (no input needed)?
        if not result.get("_need_input"):
            # Check for nested flow return
            result_stack = result.get("flow_stack") or []
            if len(result_stack) > 1:
                # Pop completed subflow
                _, delta = fm.pop_flow({**state, "flow_stack": result_stack})
                merge_delta(updates, delta)

                # Update state and continue parent flow
                subgraph_state["flow_stack"] = delta.flow_stack
                subgraph_state["_executed_steps"] = result.get("_executed_steps") or {}

                # Switch to parent flow's subgraph
                if delta.flow_stack:
                    parent_flow = delta.flow_stack[-1]["flow_name"]
                    subgraph = subgraph_registry.get(parent_flow)
                    flow_name = parent_flow
                    active_flow = delta.flow_stack[-1]
                    continue

            # Single flow completed or no parent - exit loop
            break

        # Need input - INTERRUPT HERE (ADR-002 key pattern)
        prompt = result.get("_pending_prompt") or {}

        # Include all responses collected in this turn so far
        full_response = "\n".join(responses)
        if full_response:
            prompt["prompt"] = full_response

        # This is the real LangGraph interrupt
        resume_value = interrupt(prompt)

        # CLEAR responses after interrupt - they have been sent to user
        responses = []

        # Extract message from resume value
        if isinstance(resume_value, str):
            user_message = resume_value
        elif isinstance(resume_value, dict):
            user_message = resume_value.get("message", str(resume_value))
        else:
            user_message = str(resume_value)

        # Run NLU on the response (ADR-002: NLU at orchestrator level)
        # Build proper DialogueContext with expected_slot, flow_slots, etc.
        from soni.config.models import CollectStepConfig
        from soni.du.models import CommandInfo, DialogueContext, FlowInfo, SlotDefinition, SlotValue

        # Get pending prompt info for expected_slot
        pending = result.get("_pending_prompt") or {}
        expected_slot = pending.get("slot")

        # Build flow_slots from config
        flow_slots_defs: list[SlotDefinition] = []
        if flow_name in config.flows:
            flow_config = config.flows[flow_name]
            for step in flow_config.steps:
                if isinstance(step, CollectStepConfig):
                    flow_slots_defs.append(
                        SlotDefinition(
                            name=step.slot,
                            slot_type="string",
                            description=step.message or f"Value for {step.slot}",
                        )
                    )

        # Get current slots
        current_slots: list[SlotValue] = []
        flow_slots_state = subgraph_state.get("flow_slots", {})
        if active_flow:
            flow_id = active_flow.get("flow_id")
            if flow_id and flow_id in flow_slots_state:
                slot_dict = flow_slots_state[flow_id]
                for name, value in slot_dict.items():
                    if not name.startswith("_"):
                        current_slots.append(
                            SlotValue(name=name, value=str(value) if value is not None else None)
                        )

        # Build available flows and commands
        flows_info = [
            FlowInfo(name=n, description=f.description or n) for n, f in config.flows.items()
        ]

        commands_info = [
            CommandInfo(
                command_type="set_slot",
                description="Set a slot value when user provides information",
                required_fields=["slot", "value"],
            ),
            CommandInfo(command_type="affirm", description="User confirms"),
            CommandInfo(command_type="deny", description="User denies"),
        ]

        conversation_state = "collecting"  # Default for when input is needed

        dialogue_context = DialogueContext(
            available_flows=flows_info,
            available_commands=commands_info,
            active_flow=flow_name,
            flow_slots=flow_slots_defs,
            current_slots=current_slots,
            expected_slot=expected_slot,
            conversation_state=cast(
                Literal["idle", "collecting", "confirming", "action_pending"], conversation_state
            ),
        )

        history = subgraph_state.get("messages") or []
        nlu_result = await du.acall(user_message, dialogue_context, history)
        new_commands = [cmd.model_dump() for cmd in nlu_result.commands]

        # Pass 2: Slot Extraction (if flow is active)
        if hasattr(ctx, "slot_extractor") and flow_name in config.flows:
            # Get slot definitions for current flow
            flow_config = config.flows[flow_name]
            # Collect all slots defined in the flow (trigger slots + step slots)
            slot_defs = {}

            # From trigger
            if flow_config.trigger and flow_config.trigger.slots:
                for s in flow_config.trigger.slots:
                    if isinstance(s, dict):
                        slot_defs.update(s)
                    else:  # simple str
                        pass

            # From steps (config doesn't easily expose slots per step without iterating)
            # Actually, `SlotExtractor` usually expects a dict of `SlotConfig`.
            # For M10 verification, if we just rely on SoniDU for now it failed.
            # But iterating config steps is expensive here?
            # ConfigLoader should have provided a map?

            # Simplified: Use Config helper if available or extract relevant slots
            # For banking, slots are defined in trigger OR implicit in collect steps.
            # StartFlow passes definitions. Here we are MID-flow.
            # The `SlotExtractor` needs definitions to know what to look for.

            # If we don't have definitions readily available, maybe we skip or rely on SoniDU?
            # BUT SoniDU failed.

            # Let's inspect `config.flows[flow_name]`. It is `FlowConfig`.
            # We can get `slots` from `trigger` if defined there.
            # The `banking` example defines slots in `trigger` for `check_transactions` but NOT for `transfer_funds`.
            # `transfer_funds` uses `collect` steps.

            # M10 Fix: Construct definitions from flow config steps
            # This is technical debt, should be pre-computed.
            definitions = {}
            if flow_config.steps:
                from soni.config.models import CollectStepConfig

                for step in flow_config.steps:
                    if isinstance(step, CollectStepConfig):
                        # Create a minimal definition
                        definitions[step.slot] = {"type": "string", "description": step.message}

            if definitions:
                from soni.du.slot_extractor import SlotExtractionInput

                inputs = [
                    SlotExtractionInput(
                        name=k,
                        slot_type=v.get("type", "string"),
                        description=v.get("description", ""),
                    )
                    for k, v in definitions.items()
                ]

                slot_cmds = await ctx.slot_extractor.acall(user_message, inputs)
                new_commands.extend([cmd.model_dump() for cmd in slot_cmds])

        for cmd in new_commands:
            cmd_type = cmd.get("type")

            if cmd_type == "start_flow":
                # Digression - push new flow
                new_flow = cmd.get("flow_name")
                if new_flow and new_flow != flow_name and new_flow in config.flows:
                    _, delta = fm.push_flow(
                        {**state, "flow_stack": result.get("flow_stack") or stack}, new_flow
                    )
                    merge_delta(updates, delta)
                    subgraph = subgraph_registry.get(new_flow)
                    if subgraph:
                        flow_name = new_flow
                        subgraph_state["flow_stack"] = delta.flow_stack
                        subgraph_state["flow_slots"] = {
                            **(subgraph_state.get("flow_slots") or {}),
                            **(delta.flow_slots or {}),
                        }
                        continue

            elif cmd_type == "cancel_flow":
                current_stack = result.get("flow_stack") or stack
                if current_stack:
                    _, delta = fm.pop_flow({**state, "flow_stack": current_stack})
                    merge_delta(updates, delta)
                    responses.append(RESPONSE_CANCELLED)

                    if delta.flow_stack:
                        # Return to parent flow
                        parent_flow = delta.flow_stack[-1]["flow_name"]
                        subgraph = subgraph_registry.get(parent_flow)
                        if subgraph:
                            flow_name = parent_flow
                            active_flow = delta.flow_stack[-1]
                            subgraph_state["flow_stack"] = delta.flow_stack
                            new_commands = []  # Clear commands
                            continue
                    # No more flows
                    break

        # Update subgraph state for next iteration
        subgraph_state["commands"] = new_commands
        subgraph_state["user_message"] = user_message
        subgraph_state["flow_slots"] = (
            result.get("flow_slots") or subgraph_state.get("flow_slots") or {}
        )
        subgraph_state["_executed_steps"] = result.get("_executed_steps") or {}
        subgraph_state["_need_input"] = False
        subgraph_state["_pending_prompt"] = None

        # Add user message to history
        messages = list(subgraph_state.get("messages") or [])
        messages.append(HumanMessage(content=user_message))
        subgraph_state["messages"] = messages

    # Build final result
    final_response = "\n".join(responses) if responses else None

    messages = list(state.get("messages") or [])
    if final_response:
        messages.append(AIMessage(content=final_response))

    return {
        **updates,
        "response": final_response,
        "messages": messages,
        "_pending_responses": responses,  # Return only THIS turn's responses
        "flow_stack": result.get("flow_stack") if "result" in locals() else state.get("flow_stack"),
        "flow_slots": result.get("flow_slots") if "result" in locals() else state.get("flow_slots"),
        "_executed_steps": result.get("_executed_steps")
        if "result" in locals()
        else state.get("_executed_steps"),
        "commands": [],
        "_need_input": False,
        "_pending_prompt": None,
    }
