"""Pattern Handlers - SOLID-compliant conversation pattern processing.

Each handler follows the PatternHandler protocol and handles a single command type.
This design follows:
- SRP: Each handler has one responsibility
- OCP: Add new patterns by creating new handlers, not modifying existing code
- DIP: Handlers depend on abstractions (protocol), not concrete implementations
"""

from typing import Any

from langchain_core.messages import AIMessage

from soni.core.commands import (
    CancelFlow,
    CorrectSlot,
    HumanHandoff,
    RequestClarification,
)
from soni.core.types import DialogueState, RuntimeContext
from soni.dm.patterns.base import PatternHandler
from soni.dm.patterns.cancellation import CancellationHandler
from soni.dm.patterns.clarification import ClarificationHandler
from soni.dm.patterns.correction import CorrectionHandler
from soni.dm.patterns.handoff import HumanHandoffHandler

# Registry of handlers by command type
# OCP: Add new handlers here without modifying understand_node
PATTERN_HANDLERS: dict[type, PatternHandler] = {
    CorrectSlot: CorrectionHandler(),
    CancelFlow: CancellationHandler(),
    RequestClarification: ClarificationHandler(),
    HumanHandoff: HumanHandoffHandler(),
}


async def dispatch_pattern_command(
    cmd: Any,
    state: DialogueState,
    context: RuntimeContext,
) -> tuple[dict[str, Any], list[AIMessage]] | None:
    """Dispatch a command to its appropriate handler.

    Returns None if no handler exists for this command type.
    """
    handler = PATTERN_HANDLERS.get(type(cmd))
    if handler:
        return await handler.handle(cmd, state, context)
    return None
