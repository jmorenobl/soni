"""Respond node - generates final response."""
from typing import Any

from langgraph.runtime import Runtime

from soni.core.types import DialogueState, RuntimeContext


async def respond_node(
    state: DialogueState,
    runtime: Runtime[RuntimeContext],
) -> dict[str, Any]:
    """Generate response for user."""
    # Stub: formatting logic.
    return {}
