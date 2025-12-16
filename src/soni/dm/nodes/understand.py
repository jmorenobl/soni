"""Understand node - processes input."""
from typing import Any

from langgraph.runtime import Runtime

from soni.core.types import DialogueState, RuntimeContext


async def understand_node(
    state: DialogueState,
    runtime: Runtime[RuntimeContext],
) -> dict[str, Any]:
    """Process user input via NLU."""
    # Stub: simplified logic. Real impl calls DU module.
    # For now, just pass through. Logic normally updates state['commands']
    return {"commands": []}
