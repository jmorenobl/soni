"""Handle cancellation node for popping flows from stack.

According to design (docs/design/10-dsl-specification/06-patterns.md):
- Cancellation should "Pop flow, return to previous or idle"
- Design (docs/design/07-flow-management.md): pop_flow(state, result="cancelled")
"""

import logging

from soni.core.types import DialogueState, NodeRuntime

logger = logging.getLogger(__name__)


async def handle_cancellation_node(
    state: DialogueState,
    runtime: NodeRuntime,
) -> dict:
    """
    Handle flow cancellation by popping current flow from stack.

    According to design:
    - Pop current flow with result="cancelled"
    - Return to previous flow (if exists) or idle state
    - Generate appropriate response

    Args:
        state: Current dialogue state
        runtime: Runtime context

    Returns:
        Partial state updates with conversation_state and last_response
    """
    flow_manager = runtime.context["flow_manager"]
    nlu_result = state.get("nlu_result", {})

    if not nlu_result:
        logger.warning("No NLU result in state for cancellation")
        return {
            "conversation_state": "error",
            "user_message": "",
            "nlu_result": {},  # Clear to prevent loops
        }

    # Get active flow before popping
    active_ctx = flow_manager.get_active_context(state)
    if not active_ctx:
        # No active flow to cancel
        logger.info("No active flow to cancel")
        return {
            "conversation_state": "idle",
            "last_response": "There's nothing to cancel. How can I help you?",
            "user_message": "",  # Clear to prevent loops
            "nlu_result": {},  # Clear to prevent loops
            "current_step": None,
            "current_prompted_slot": None,
            "waiting_for_slot": None,
        }

    flow_name = active_ctx.get("flow_name", "this task")
    flow_id = active_ctx.get("flow_id", "unknown")
    logger.info(f"Cancelling flow: {flow_name} (flow_id: {flow_id})")
    logger.debug(f"Flow stack before pop: {len(state.get('flow_stack', []))} flows")
    logger.debug(f"Flow slots before pop: {list(state.get('flow_slots', {}).keys())}")

    # Pop the current flow with result="cancelled"
    # This modifies state["flow_stack"] in place
    flow_manager.pop_flow(state, result="cancelled")

    logger.debug(f"Flow stack after pop: {len(state.get('flow_stack', []))} flows")
    logger.debug(f"Flow slots after pop: {list(state.get('flow_slots', {}).keys())}")

    # Check if there's a previous flow to resume
    # Note: pop_flow() already resumes the previous flow (sets flow_state="active")
    remaining_stack = state.get("flow_stack", [])
    if remaining_stack:
        # Previous flow was automatically resumed by pop_flow()
        previous_ctx = remaining_stack[-1]
        previous_flow_name = previous_ctx.get("flow_name", "previous task")
        logger.info(f"Resuming previous flow: {previous_flow_name}")

        # Determine what the previous flow was waiting for
        step_manager = runtime.context["step_manager"]
        current_step_config = step_manager.get_current_step_config(state, runtime.context)
        waiting_for_slot = None
        if current_step_config and current_step_config.type == "collect":
            waiting_for_slot = current_step_config.slot

        # CRITICAL: Clear user_message after processing to prevent routing loops
        # Also clear nlu_result to prevent re-routing
        result = {
            "conversation_state": "waiting_for_slot" if waiting_for_slot else "idle",
            "waiting_for_slot": waiting_for_slot,
            "last_response": f"I've cancelled {flow_name}. Returning to {previous_flow_name}.",
            "flow_stack": state["flow_stack"],  # Include updated stack
            "flow_slots": state["flow_slots"],  # Include updated slots
            "user_message": "",  # Clear to prevent loops
            "nlu_result": {},  # Clear nlu_result to prevent re-routing
        }
        # Only clear current_step and current_prompted_slot if not waiting for slot
        if not waiting_for_slot:
            result["current_step"] = None
            result["current_prompted_slot"] = None
        return result
    else:
        # No previous flow - return to idle
        logger.info("No previous flow, returning to idle")
        # Validate that flow_stack is empty
        if state.get("flow_stack"):
            logger.warning(
                f"Expected empty flow_stack after cancellation, but found {len(state['flow_stack'])} flows"
            )
        # Validate that flow_slots doesn't have orphaned entries
        active_flow_ids = {ctx["flow_id"] for ctx in state.get("flow_stack", [])}
        slot_flow_ids = set(state.get("flow_slots", {}).keys())
        orphaned_ids = slot_flow_ids - active_flow_ids
        if orphaned_ids:
            logger.warning(
                f"Found orphaned flow_slots after cancellation: {orphaned_ids}. "
                "These should have been cleaned by pop_flow."
            )
        # CRITICAL: Clear user_message after processing to prevent routing loops
        # Also clear all flow-related state to prevent loops
        result = {
            "conversation_state": "idle",
            "last_response": f"I've cancelled {flow_name}. How else can I help you?",
            "flow_stack": state["flow_stack"],  # Include updated stack (empty)
            "flow_slots": state["flow_slots"],  # Include updated slots
            "user_message": "",  # Clear to prevent loops
            "nlu_result": {},  # Clear nlu_result to prevent re-routing
            "current_step": None,  # Clear current_step
            "current_prompted_slot": None,  # Clear current_prompted_slot
            "waiting_for_slot": None,  # Clear waiting_for_slot when idle
        }
        logger.debug(f"Returning state updates: {list(result.keys())}")
        return result
