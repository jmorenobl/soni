"""State-Based Routing for Soni v2.0.

This component is responsible ONLY for routing based on the deterministic
DialogueState. It does NOT perform NLU classification or heuristic routing.

Routing Logic:
1. Execute Commands (Executor Node) updates State.
2. Router checks State (conversation_state, flow_stack).
3. Router returns Next Node.
"""

import logging

from soni.core.constants import ConversationState, NodeName
from soni.core.types import DialogueState

logger = logging.getLogger(__name__)


def route_next(state: DialogueState) -> str:
    """Determine the next graph node based on current state.

    Args:
        state: Current dialogue state (post-command execution).

    Returns:
        NodeName of the next node.
    """
    conv_state = state.get("conversation_state")
    flow_stack = state.get("flow_stack", [])

    # 1. Error State
    if conv_state == ConversationState.ERROR:
        return NodeName.GENERATE_RESPONSE  # Or dedicated error handler

    # 2. Waiting for Input -> End Turn
    if conv_state in (ConversationState.WAITING_FOR_SLOT, ConversationState.CONFIRMING):
        return "END"  # End of turn, wait for user

    # 3. Ready for Action -> Execute
    if conv_state == ConversationState.READY_FOR_ACTION:
        return NodeName.EXECUTE_ACTION

    # 4. Ready for Confirmation -> Ask
    if conv_state == ConversationState.READY_FOR_CONFIRMATION:
        return NodeName.CONFIRM_ACTION

    # 5. Default: If active flow, continue flow steps
    if flow_stack:
        return NodeName.COLLECT_NEXT_SLOT  # Simplification for "continue flow"

    return NodeName.GENERATE_RESPONSE
