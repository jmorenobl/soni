"""Respond node - generates final response for user.

Simple node that takes the response from state and returns it.
Can optionally use LLM for response polishing.
"""

import logging
from typing import Any

from soni.core.types import DialogueState, RuntimeContext

logger = logging.getLogger(__name__)


async def respond_node(
    state: DialogueState,
    context: RuntimeContext,
) -> dict[str, Any]:
    """Generate response for user.
    
    Args:
        state: Current dialogue state (should have 'response' set)
        context: Runtime context
        
    Returns:
        State updates with last_response
    """
    response = state.get("response", "")
    
    if not response:
        response = "How can I help you?"
    
    logger.info(f"Response: {response[:50]}...")
    
    return {
        "last_response": response,
        "response": None,  # Clear for next turn
    }
