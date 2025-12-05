"""NLU provider implementation using DSPy SoniDU module."""

from typing import Any

import dspy

from soni.core.interfaces import INLUProvider
from soni.du.models import DialogueContext, NLUOutput
from soni.du.modules import SoniDU


class DSPyNLUProvider(INLUProvider):
    """NLU provider using DSPy SoniDU module."""

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

        Args:
            user_message: User's input
            dialogue_context: Context dict with fields:
                - current_slots: dict
                - available_actions: list[str]
                - available_flows: list[str]
                - current_flow: str
                - expected_slots: list[str]
                - history: list[dict] (optional)

        Returns:
            Serialized NLUOutput as dict
        """
        # Build structured context
        context = DialogueContext(
            current_slots=dialogue_context.get("current_slots", {}),
            available_actions=dialogue_context.get("available_actions", []),
            available_flows=dialogue_context.get("available_flows", []),
            current_flow=dialogue_context.get("current_flow", "none"),
            expected_slots=dialogue_context.get("expected_slots", []),
        )

        # Build history
        history_data = dialogue_context.get("history", [])
        history = dspy.History(messages=history_data)

        # Call NLU
        result: NLUOutput = await self.module.predict(
            user_message=user_message,
            history=history,
            context=context,
        )

        # Return serialized
        return dict(result.model_dump())
