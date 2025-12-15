"""Understand node - NLU processing for Soni v3.0.

Simplified version that:
1. Calls DSPy NLU module
2. Outputs list of Commands
3. Updates user_message in state

No complex routing logic or conversation_state management.
"""

import logging
from typing import Any

from soni.core.state import get_all_slots
from soni.core.types import DialogueState, RuntimeContext

logger = logging.getLogger(__name__)


async def understand_node(
    state: DialogueState,
    context: RuntimeContext,
) -> dict[str, Any]:
    """Process user message via NLU, produce Commands.
    
    Args:
        state: Current dialogue state with user_message
        context: Runtime context with du (NLU provider), flow_manager
        
    Returns:
        State updates with commands list
    """
    import dspy
    from soni.du.models import DialogueContext
    
    nlu_provider = context["du"]
    flow_manager = context["flow_manager"]
    scope_manager = context["scope_manager"]
    
    user_message = state.get("user_message", "")
    if not user_message:
        return {"commands": []}
    
    # Build context for NLU
    active_ctx = flow_manager.get_active_context(state)
    current_flow = active_ctx["flow_name"] if active_ctx else "none"
    current_slots = get_all_slots(state) if active_ctx else {}
    
    # Get available flows and actions for NLU context
    available_flows = scope_manager.get_available_flows(state)
    available_actions = scope_manager.get_available_actions(state)
    
    # Get expected slots for current flow
    expected_slots = []
    if current_flow != "none":
        expected_slots = scope_manager.get_expected_slots(
            flow_name=current_flow,
            available_actions=available_actions,
        )
    else:
        # No active flow - combine expected slots from all flows
        all_slots = set()
        for flow_name in available_flows.keys():
            flow_slots = scope_manager.get_expected_slots(
                flow_name=flow_name,
                available_actions=available_actions,
            )
            all_slots.update(flow_slots)
        expected_slots = list(all_slots)
    
    # Build history (last 5 messages)
    history = dspy.History(messages=state.get("messages", [])[-5:])
    
    # Build dialogue context
    dialogue_context = DialogueContext(
        current_slots=current_slots,
        available_actions=available_actions,
        available_flows=available_flows,
        current_flow=current_flow,
        expected_slots=expected_slots,
        current_prompted_slot=state.get("waiting_for_slot"),
        conversation_state=state.get("flow_state"),
    )
    
    logger.debug(f"NLU context: flow={current_flow}, expected_slots={expected_slots}")
    
    # Call NLU
    try:
        nlu_result = await nlu_provider.predict(
            user_message,
            history,
            dialogue_context,
        )
        commands = nlu_result.commands
        logger.info(f"NLU produced {len(commands)} commands: {[c.__class__.__name__ for c in commands]}")
    except Exception as e:
        logger.error(f"NLU error: {e}")
        commands = []
    
    return {
        "commands": commands,
        "waiting_for_slot": None,  # Clear after processing message
    }
