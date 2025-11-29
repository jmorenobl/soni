"""DSPy modules for Dialogue Understanding"""

from dataclasses import asdict, dataclass
from typing import Any

import dspy

from soni.core.interfaces import IScopeManager
from soni.du.signatures import DialogueUnderstanding


@dataclass
class NLUResult:
    """Result from NLU prediction"""

    command: str
    slots: dict[str, Any]
    confidence: float
    reasoning: str

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary"""
        return asdict(self)


class SoniDU(dspy.Module):
    """
    Soni Dialogue Understanding module using DSPy.

    This module can be optimized using DSPy optimizers (e.g., MIPROv2)
    and provides both sync (for optimization) and async (for runtime) interfaces.
    """

    def __init__(self, scope_manager: IScopeManager | None = None):
        super().__init__()
        self.predictor = dspy.ChainOfThought(DialogueUnderstanding)
        self.scope_manager = scope_manager

    def forward(
        self,
        user_message: str,
        dialogue_history: str = "",
        current_slots: str = "{}",
        available_actions: str = "[]",
        current_flow: str = "none",
    ) -> dspy.Prediction:
        """
        Forward pass (synchronous) for use with optimizers.

        Args:
            user_message: User's input message
            dialogue_history: Previous conversation context
            current_slots: Currently filled slots as JSON string
            available_actions: Available actions as JSON array string
            current_flow: Current dialogue flow name

        Returns:
            DSPy Prediction object
        """
        return self.predictor(
            user_message=user_message,
            dialogue_history=dialogue_history,
            current_slots=current_slots,
            available_actions=available_actions,
            current_flow=current_flow,
        )

    async def aforward(
        self,
        user_message: str,
        dialogue_history: str = "",
        current_slots: str = "{}",
        available_actions: str = "[]",
        current_flow: str = "none",
    ) -> dspy.Prediction:
        """
        Async forward pass for runtime use.

        Args:
            user_message: User's input message
            dialogue_history: Previous conversation context
            current_slots: Currently filled slots as JSON string
            available_actions: Available actions as JSON array string
            current_flow: Current dialogue flow name

        Returns:
            DSPy Prediction object
        """
        # For now, run sync forward in executor
        # In future, this could use async LLM calls
        import asyncio

        loop = asyncio.get_event_loop()
        return await loop.run_in_executor(
            None,
            self.forward,
            user_message,
            dialogue_history,
            current_slots,
            available_actions,
            current_flow,
        )

    async def predict(
        self,
        user_message: str,
        dialogue_history: str = "",
        current_slots: dict[str, Any] | None = None,
        available_actions: list | None = None,
        current_flow: str = "none",
    ) -> NLUResult:
        """
        High-level async predict method that returns NLUResult.

        Args:
            user_message: User's input message
            dialogue_history: Previous conversation context
            current_slots: Currently filled slots as dict
            available_actions: Available actions as list
            current_flow: Current dialogue flow name

        Returns:
            NLUResult object
        """
        import json

        # Convert inputs to string format expected by signature
        slots_str = json.dumps(current_slots or {})
        actions_str = json.dumps(available_actions or [])

        # Apply scoping if scope_manager is available
        if self.scope_manager and available_actions:
            # Note: This requires DialogueState, will be fully integrated later
            # For now, use available_actions as-is
            pass

        # Get prediction
        prediction = await self.aforward(
            user_message=user_message,
            dialogue_history=dialogue_history,
            current_slots=slots_str,
            available_actions=actions_str,
            current_flow=current_flow,
        )

        # Parse outputs
        try:
            slots = json.loads(prediction.extracted_slots)
        except (json.JSONDecodeError, AttributeError, TypeError):
            slots = {}

        try:
            confidence = float(prediction.confidence)
        except (ValueError, AttributeError, TypeError):
            confidence = 0.0

        return NLUResult(
            command=prediction.structured_command or "",
            slots=slots,
            confidence=confidence,
            reasoning=prediction.reasoning or "",
        )
