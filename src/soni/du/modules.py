"""DSPy modules for Dialogue Understanding."""

import json
import logging
from dataclasses import asdict, dataclass
from typing import Any

import dspy
from cachetools import TTLCache

from soni.du.signatures import DialogueUnderstanding
from soni.utils.hashing import generate_cache_key_from_dict

logger = logging.getLogger(__name__)


@dataclass
class NLUResult:
    """Result from NLU prediction."""

    command: str
    slots: dict[str, Any]
    confidence: float
    reasoning: str

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary."""
        return asdict(self)


class SoniDU(dspy.Module):
    """Soni Dialogue Understanding module using DSPy.

    This module can be optimized using DSPy optimizers (e.g., MIPROv2)
    and provides both sync (for optimization) and async (for runtime) interfaces.
    """

    def __init__(
        self,
        cache_size: int = 1000,
        cache_ttl: int = 300,
    ):
        """Initialize SoniDU module.

        Args:
            cache_size: Maximum number of cached NLU results.
            cache_ttl: Time-to-live for cache entries in seconds.
        """
        super().__init__()
        self.predictor = dspy.ChainOfThought(DialogueUnderstanding)

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
        expected_slots: str = "[]",
        current_datetime: str = "",
    ) -> dspy.Prediction:
        """Forward pass (synchronous) for use with optimizers.

        Args:
            user_message: User's input message
            dialogue_history: Previous conversation context
            current_slots: Currently filled slots as JSON string
            available_actions: Available actions as JSON array string
            current_flow: Current dialogue flow name
            expected_slots: Expected slot names as JSON array string
            current_datetime: Current date and time in ISO format for resolving relative dates

        Returns:
            DSPy Prediction object
        """
        return self.predictor(
            user_message=user_message,
            dialogue_history=dialogue_history,
            current_slots=current_slots,
            available_actions=available_actions,
            current_flow=current_flow,
            expected_slots=expected_slots,
            current_datetime=current_datetime,
        )

    async def aforward(
        self,
        user_message: str,
        dialogue_history: str = "",
        current_slots: str = "{}",
        available_actions: str = "[]",
        current_flow: str = "none",
        expected_slots: str = "[]",
        current_datetime: str = "",
    ) -> dspy.Prediction:
        """Async forward pass for runtime use.

        Args:
            user_message: User's input message
            dialogue_history: Previous conversation context
            current_slots: Currently filled slots as JSON string
            available_actions: Available actions as JSON array string
            current_flow: Current dialogue flow name
            expected_slots: Expected slot names as JSON array string

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
            expected_slots,
            current_datetime,
        )

    def _get_cache_key(
        self,
        user_message: str,
        dialogue_history: str,
        current_slots: dict[str, Any],
        available_actions: list[str],
        current_flow: str,
        expected_slots: list[str] | None = None,
        current_datetime: str = "",
    ) -> str:
        """Generate cache key for NLU request.

        Args:
            user_message: User's input message
            dialogue_history: Previous conversation context
            current_slots: Currently filled slots
            available_actions: Available actions list
            current_flow: Current dialogue flow name
            expected_slots: Expected slot names list
            current_datetime: Current datetime in ISO format (for cache key)

        Returns:
            Cache key as MD5 hash string
        """
        # Create hash of inputs
        return generate_cache_key_from_dict(
            {
                "message": user_message,
                "history": dialogue_history,
                "slots": current_slots,
                "actions": sorted(available_actions),  # Sort for consistency
                "flow": current_flow,
                "expected_slots": sorted(expected_slots or []),  # Sort for consistency
                "datetime": current_datetime,
            }
        )

    async def predict(
        self,
        user_message: str,
        dialogue_history: str = "",
        current_slots: dict[str, Any] | None = None,
        available_actions: list | None = None,
        current_flow: str = "none",
        expected_slots: list[str] | None = None,
    ) -> NLUResult:
        """High-level async predict method that returns NLUResult.

        Scoping of available_actions should be done by the caller
        (e.g., understand_node applies scoping via IScopeManager).

        Args:
            user_message: User's input message
            dialogue_history: Previous conversation context
            current_slots: Currently filled slots as dict
            available_actions: Available actions as list (scoped by caller)
            current_flow: Current dialogue flow name
            expected_slots: Expected slot names for the current flow.
                          NLU should use these exact names when extracting entities.

        Returns:
            NLUResult object

        Note:
            Current datetime is calculated internally by the NLU module.
            This follows encapsulation principle - NLU manages its own dependencies.
        """
        # Calculate current datetime internally (encapsulation - NLU manages its own dependencies)
        # This avoids passing datetime through the entire call chain
        from datetime import datetime

        current_datetime = datetime.now().isoformat()

        # Check cache first
        cache_key = self._get_cache_key(
            user_message,
            dialogue_history,
            current_slots or {},
            available_actions or [],
            current_flow,
            expected_slots,
            current_datetime,
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
        expected_slots_str = json.dumps(expected_slots or [])

        # Get prediction using acall() (DSPy's public async method)
        # Current datetime is calculated above and passed to signature
        prediction = await self.acall(
            user_message=user_message,
            dialogue_history=dialogue_history,
            current_slots=slots_str,
            available_actions=actions_str,
            current_flow=current_flow,
            expected_slots=expected_slots_str,
            current_datetime=current_datetime,
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
