"""Respond node - generates final response."""

from typing import Any

from langchain_core.runnables import RunnableConfig

from soni.core.types import DialogueState


async def respond_node(
    state: DialogueState,
    config: RunnableConfig,
) -> dict[str, Any]:
    """Generate response for user."""
    last_msg = state["messages"][-1] if state["messages"] else None
    response = last_msg.content if last_msg else "I don't understand."
    return {"last_response": response}
