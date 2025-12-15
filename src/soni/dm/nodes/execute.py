"""Execute node - deterministic command execution.

This node receives Commands from the understand node and executes them
in sequence. NO LLM calls, just deterministic state updates.

Commands:
- StartFlow → push flow onto stack
- SetSlot → set slot value
- CancelFlow → pop flow from stack
- AffirmConfirmation → advance to action
- DenyConfirmation → revert to slot collection
"""

import logging
from typing import Any

from soni.core.commands import (
    AffirmConfirmation,
    CancelFlow,
    Command,
    DenyConfirmation,
    SetSlot,
    StartFlow,
)
from soni.core.constants import FlowState
from soni.core.types import DialogueState, RuntimeContext

logger = logging.getLogger(__name__)


async def execute_node(
    state: DialogueState,
    context: RuntimeContext,
) -> dict[str, Any]:
    """Execute commands from NLU deterministically.
    
    Args:
        state: Current dialogue state
        context: Runtime context with flow_manager
        
    Returns:
        State updates
    """
    commands: list[Command] = state.get("commands", [])
    
    if not commands:
        logger.info("No commands to execute")
        return {
            "flow_state": FlowState.WAITING_INPUT,
            "response": "I didn't understand that. Could you rephrase?",
        }
    
    logger.info(f"Executing {len(commands)} commands: {[c.__class__.__name__ for c in commands]}")
    
    flow_manager = context["flow_manager"]
    updates: dict[str, Any] = {}
    
    for command in commands:
        cmd_updates = _execute_command(command, state, context)
        updates.update(cmd_updates)
        # Apply to state for subsequent commands
        for key, value in cmd_updates.items():
            state[key] = value  # type: ignore
    
    # Determine flow state after command execution
    flow_stack = state.get("flow_stack", [])
    if flow_stack:
        updates["flow_state"] = FlowState.RUNNING
    else:
        updates["flow_state"] = FlowState.DONE
    
    return updates


def _execute_command(
    command: Command,
    state: DialogueState,
    context: RuntimeContext,
) -> dict[str, Any]:
    """Execute a single command."""
    flow_manager = context["flow_manager"]
    
    if isinstance(command, StartFlow):
        flow_manager.push_flow(
            state,
            flow_name=command.flow_name,
            inputs=command.slots,
            reason="command",
        )
        logger.info(f"Started flow: {command.flow_name}")
        return {
            "flow_stack": state["flow_stack"],
            "flow_slots": state["flow_slots"],
        }
    
    elif isinstance(command, SetSlot):
        flow_manager.set_slot(state, command.slot_name, command.value)
        logger.info(f"Set slot: {command.slot_name} = {command.value}")
        return {
            "flow_slots": state["flow_slots"],
        }
    
    elif isinstance(command, CancelFlow):
        flow_manager.pop_flow(state, result="cancelled")
        logger.info("Cancelled flow")
        return {
            "flow_stack": state["flow_stack"],
            "response": "Okay, I've cancelled that.",
        }
    
    elif isinstance(command, AffirmConfirmation):
        # Advance to action step
        step_manager = context["step_manager"]
        updates = step_manager.advance_to_next_step(state, context)
        logger.info("Confirmation affirmed, advancing to action")
        return updates
    
    elif isinstance(command, DenyConfirmation):
        # Clear the specified slot for re-collection
        if command.slot_to_change:
            flow_manager.set_slot(state, command.slot_to_change, None)
            logger.info(f"Denial with slot change: {command.slot_to_change}")
        return {
            "response": "Okay, what would you like to change?",
        }
    
    else:
        logger.warning(f"Unknown command type: {command.__class__.__name__}")
        return {}
