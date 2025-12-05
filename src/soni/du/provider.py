"""NLU provider implementation using DSPy SoniDU module."""

from typing import Any

from soni.core.interfaces import INLUProvider
from soni.du.modules import SoniDU


class DSPyNLUProvider(INLUProvider):
    """NLU provider using DSPy SoniDU module.

    This is a thin wrapper that delegates to SoniDU.understand().
    Follows Adapter Pattern: adapts INLUProvider interface to SoniDU interface.
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

        This method delegates to SoniDU.understand() which handles:
        - Type conversion (dict → structured types)
        - Caching
        - Actual NLU prediction

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
        # Delegate to SoniDU.understand() which handles all conversion and caching
        # This eliminates code duplication (DRY principle)
        return await self.module.understand(user_message, dialogue_context)
