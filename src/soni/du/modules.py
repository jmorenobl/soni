"""DSPy modules for Dialogue Understanding"""

import hashlib
import json
import logging
from dataclasses import asdict, dataclass
from typing import Any

import dspy
from cachetools import TTLCache  # type: ignore[import-untyped]

from soni.core.interfaces import IScopeManager
from soni.core.state import DialogueState
from soni.du.signatures import DialogueUnderstanding

logger = logging.getLogger(__name__)


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

    def __init__(
        self,
        scope_manager: IScopeManager | None = None,
        cache_size: int = 1000,
        cache_ttl: int = 300,
    ):
        super().__init__()
        self.predictor = dspy.ChainOfThought(DialogueUnderstanding)
        self.scope_manager = scope_manager

        # Cache for NLU results
        self.nlu_cache: TTLCache[str, NLUResult] = TTLCache(
            maxsize=cache_size,  # Cache up to 1000 results
            ttl=cache_ttl,  # 5 minutes TTL (300 seconds)
        )

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

    def _get_cache_key(
        self,
        user_message: str,
        dialogue_history: str,
        current_slots: dict[str, Any],
        available_actions: list[str],
        current_flow: str,
    ) -> str:
        """
        Generate cache key for NLU request.

        Args:
            user_message: User's input message
            dialogue_history: Previous conversation context
            current_slots: Currently filled slots
            available_actions: Available actions list
            current_flow: Current dialogue flow name

        Returns:
            Cache key as MD5 hash string
        """
        # Create hash of inputs
        key_data = json.dumps(
            {
                "message": user_message,
                "history": dialogue_history,
                "slots": current_slots,
                "actions": sorted(available_actions),  # Sort for consistency
                "flow": current_flow,
            },
            sort_keys=True,
        )
        return hashlib.md5(key_data.encode()).hexdigest()

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
        # Apply scoping if scope_manager is available and available_actions not provided
        if self.scope_manager and available_actions is None:
            # Create minimal state for scoping
            scoping_state = DialogueState(
                current_flow=current_flow,
                slots=current_slots or {},
            )
            available_actions = self.scope_manager.get_available_actions(scoping_state)
            logger.debug(
                f"Applied scoping: {len(available_actions)} actions available "
                f"for flow '{current_flow}'"
            )

        # Check cache first
        cache_key = self._get_cache_key(
            user_message,
            dialogue_history,
            current_slots or {},
            available_actions or [],
            current_flow,
        )

        if cache_key in self.nlu_cache:
            logger.debug(f"NLU cache hit for key: {cache_key[:8]}...")
            cached_result: NLUResult = self.nlu_cache[cache_key]
            return cached_result

        # Cache miss - call NLU
        logger.debug("NLU cache miss, calling predictor")

        # Convert inputs to string format expected by signature
        slots_str = json.dumps(current_slots or {})
        actions_str = json.dumps(available_actions or [])

        # Get prediction using acall() (DSPy's public async method)
        prediction = await self.acall(
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

        nlu_result = NLUResult(
            command=prediction.structured_command or "",
            slots=slots,
            confidence=confidence,
            reasoning=prediction.reasoning or "",
        )

        # Cache result
        self.nlu_cache[cache_key] = nlu_result
        logger.debug(f"Cached NLU result for key: {cache_key[:8]}...")

        return nlu_result
