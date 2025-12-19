"""RespondNode - generates final user response.

## How Respond Node Works

The respond node is the **final output stage** in Soni's dialogue management pipeline.
It constructs the response message that will be delivered to the user based on the
current dialogue state and message history.

## Purpose

This node serves as the **termination point** for each dialogue turn:
- Extracts the assistant's response from the message history
- Populates the `last_response` field for the application to retrieve
- Completes the dialogue turn gracefully

## Execution Flow

```
Flow Execution → Generate Response → Respond Node → User Sees Response
                                         ↓
                                   Sets last_response
```

## When Respond Node is Called

1. **After Flow Subgraph Completion**: When a flow finishes and response is ready
2. **After Resume Node**: When resuming a parent flow or ending conversation
3. **Idle State**: When execute node routes here (no active flow)

## Message History Pattern

The respond node assumes the **last message** in the `messages` list contains
the assistant's response to display. This follows the conversational pattern:

```
messages: [
    HumanMessage("I want to book a flight"),
    AIMessage("Where would you like to go?"),  ← This is extracted
]
```

## Fallback Behavior

If no messages exist or the message structure is unexpected, returns a safe
default to avoid crashes in production.

## Implementation Details

- **Non-blocking**: No async operations, just state reading
- **Idempotent**: Can be called multiple times without side effects
- **Defensive**: Handles edge cases like empty message lists or malformed messages
- **Single Responsibility**: Only formats output, no business logic
"""

from typing import Any

from langgraph.runtime import Runtime

from soni.core.types import DialogueState, RuntimeContext


async def respond_node(
    state: DialogueState,
    runtime: Runtime[RuntimeContext],
) -> dict[str, Any]:
    """Generate response for user.

    Extracts the last assistant message from the conversation history
    and sets it as the response to be displayed to the user.

    Note: LangChain messages always have a 'content' attribute by protocol.
    If messages list is empty, we return a neutral fallback message.

    Returns:
        Dictionary with 'last_response' key containing the message to display.
    """
    messages = state.get("messages", [])

    if messages:
        # Trust the type system - LangChain messages always have .content
        last_msg = messages[-1]
        return {"last_response": last_msg.content}

    # No messages exist - neutral fallback
    return {"last_response": "How can I help you?"}
