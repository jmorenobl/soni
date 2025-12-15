"""Step node - runs the current step in the active flow.

This node interprets the flow definition and executes the appropriate
step type:
- collect: Prompt for slot value
- action: Execute action handler
- confirm: Show confirmation message
- respond: Show message to user

The step advances automatically when slots are filled.
"""

import logging
from typing import Any

from soni.core.constants import FlowState
from soni.core.state import get_all_slots, get_flow_config
from soni.core.types import DialogueState, RuntimeContext

logger = logging.getLogger(__name__)


async def step_node(
    state: DialogueState,
    context: RuntimeContext,
) -> dict[str, Any]:
    """Run the current step in the active flow.
    
    Args:
        state: Current dialogue state
        context: Runtime context with step_manager, action_handler
        
    Returns:
        State updates including response and flow_state
    """
    flow_manager = context["flow_manager"]
    step_manager = context["step_manager"]
    
    # Get active flow
    active_ctx = flow_manager.get_active_context(state)
    if not active_ctx:
        logger.info("No active flow")
        return {
            "flow_state": FlowState.DONE,
            "response": "How can I help you?",
        }
    
    # Get current step config
    step_config = step_manager.get_current_step_config(state, context)
    if not step_config:
        # No more steps, flow complete
        logger.info(f"Flow {active_ctx['flow_name']} completed")
        flow_manager.pop_flow(state, result="completed")
        return {
            "flow_stack": state["flow_stack"],
            "flow_state": FlowState.DONE,
        }
    
    step_type = step_config.type
    logger.info(f"Running step: {step_config.step} (type={step_type})")
    
    # Dispatch based on step type
    if step_type == "collect":
        return await _handle_collect(state, context, step_config)
    elif step_type == "action":
        return await _handle_action(state, context, step_config)
    elif step_type == "confirm":
        return await _handle_confirm(state, context, step_config)
    elif step_type == "respond" or step_type == "say":
        return await _handle_respond(state, context, step_config)
    else:
        logger.warning(f"Unknown step type: {step_type}")
        return {"flow_state": FlowState.RUNNING}


async def _handle_collect(
    state: DialogueState,
    context: RuntimeContext,
    step_config: Any,
) -> dict[str, Any]:
    """Handle collect step - prompt for slot if empty, advance if filled."""
    step_manager = context["step_manager"]
    slots = get_all_slots(state)
    slot_name = step_config.slot
    
    if slot_name and slots.get(slot_name):
        # Slot already filled, advance
        logger.info(f"Slot {slot_name} already filled, advancing")
        step_manager.advance_to_next_step(state, context)
        return {
            "flow_stack": state["flow_stack"],
            "flow_state": FlowState.RUNNING,
        }
    else:
        # Need to prompt for slot
        prompt = step_config.prompt or f"Please provide {slot_name}"
        return {
            "flow_state": FlowState.WAITING_INPUT,
            "waiting_for_slot": slot_name,
            "response": prompt,
        }


async def _handle_action(
    state: DialogueState,
    context: RuntimeContext,
    step_config: Any,
) -> dict[str, Any]:
    """Handle action step - execute action handler."""
    action_handler = context["action_handler"]
    step_manager = context["step_manager"]
    flow_manager = context["flow_manager"]
    
    action_name = step_config.call
    slots = get_all_slots(state)
    
    try:
        result = await action_handler.execute(action_name, slots)
        logger.info(f"Action {action_name} completed: {list(result.keys())}")
        
        # Store action outputs in slots
        for key, value in result.items():
            flow_manager.set_slot(state, key, value)
        
        # Advance to next step
        step_manager.advance_to_next_step(state, context)
        
        return {
            "flow_slots": state["flow_slots"],
            "flow_stack": state["flow_stack"],
            "action_result": result,
            "flow_state": FlowState.RUNNING,
        }
    except Exception as e:
        logger.error(f"Action {action_name} failed: {e}")
        return {
            "flow_state": FlowState.DONE,
            "response": f"Sorry, something went wrong: {e}",
        }


async def _handle_confirm(
    state: DialogueState,
    context: RuntimeContext,
    step_config: Any,
) -> dict[str, Any]:
    """Handle confirm step - show confirmation message."""
    slots = get_all_slots(state)
    
    # Interpolate message with slot values
    message = step_config.message or "Is this correct?"
    try:
        message = message.format(**slots)
    except KeyError:
        pass  # Missing slot in template
    
    return {
        "flow_state": FlowState.WAITING_INPUT,
        "response": message,
    }


async def _handle_respond(
    state: DialogueState,
    context: RuntimeContext,
    step_config: Any,
) -> dict[str, Any]:
    """Handle respond/say step - show message and advance."""
    step_manager = context["step_manager"]
    slots = get_all_slots(state)
    
    message = step_config.message or step_config.say or ""
    try:
        message = message.format(**slots)
    except KeyError:
        pass
    
    # Advance to next step
    step_manager.advance_to_next_step(state, context)
    
    return {
        "flow_stack": state["flow_stack"],
        "flow_state": FlowState.RUNNING,
        "response": message,
    }
