"""NLU provider implementation using DSPy SoniDU module."""

from typing import Any

from soni.core.interfaces import INLUProvider
from soni.du.modules import SoniDU


class DSPyNLUProvider(INLUProvider):
    """NLU provider using DSPy SoniDU module.

    This is a thin wrapper that adapts INLUProvider interface (dict-based)
    to SoniDU.predict() (structured types).

    Uses predict() directly instead of understand() adapter for consistency.
    """

    def __init__(self, module: SoniDU) -> None:
        """Initialize provider with SoniDU module.

        Args:
            module: Optimized SoniDU module
        """
        self.module = module

    async def understand(
        self,
        user_message: str,
        dialogue_context: dict[str, Any],
    ) -> dict[str, Any]:
        """Understand user message and return NLU result.

        Adapts dict-based interface to structured types and uses predict() directly.
        This eliminates the need for SoniDU.understand() adapter.

        Args:
            user_message: User's input
            dialogue_context: Context dict with fields:
                - current_slots: dict
                - available_actions: list[str]
                - available_flows: list[str]
                - current_flow: str
                - expected_slots: list[str]
                - history: list[dict] (optional)
                - waiting_for_slot: str | None (optional)

        Returns:
            Serialized NLUOutput as dict
        """
        # Convert dict to structured types (same logic as understand_node)
        # Use centralized conversion from SoniDU
        history, context = SoniDU._dict_to_structured_types(dialogue_context)

        # Use predict() directly (no adapter needed)
        result = await self.module.predict(user_message, history, context)

        # Convert structured result back to dict
        return dict(result.model_dump())
