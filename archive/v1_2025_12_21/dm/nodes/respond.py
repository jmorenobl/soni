"""RespondNode - generates combined response from all turn messages.

## How Respond Node Works (Refactored)

The respond node is the **final output stage** in Soni's dialogue management pipeline.
It collects ALL AI messages generated during the turn (from multiple flows if there
was a digression) and combines them into the final response.

## Response Accumulation Pattern

When auto-resume happens after a digression, multiple flows may generate responses:
1. check_balance: "Your savings balance is 15,230€"
2. transfer_funds (resumed): "Please provide the recipient's IBAN"

Both messages are combined: "Your savings balance is 15,230€. Please provide the IBAN."

## Message History

The respond node extracts all AIMessage entries from the current turn and combines them.
"""

from typing import Any

from langchain_core.messages import AIMessage
from langgraph.runtime import Runtime

from soni.core.types import DialogueState, RuntimeContext


async def respond_node(
    state: DialogueState,
    runtime: Runtime[RuntimeContext],
) -> dict[str, Any]:
    """Generate combined response from all AI messages in the turn.

    Collects all AIMessage entries and combines them into a single response.
    This ensures digression responses are shown along with resumed flow prompts.

    Returns:
        Dictionary with 'last_response' containing the combined message.
    """
    messages = state.get("messages", [])

    # Collect all AI messages from this turn
    ai_responses: list[str] = []
    for msg in messages:
        if isinstance(msg, AIMessage) and msg.content:
            ai_responses.append(str(msg.content))

    if ai_responses:
        # Combine all responses with line breaks
        combined = "\n\n".join(ai_responses)
        return {"last_response": combined}

    # No messages exist - neutral fallback
    return {"last_response": "How can I help you?"}
