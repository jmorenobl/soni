"""DSPy modules for dialogue understanding.

Async-first design using native .acall() method.
"""

import logging

import dspy

from soni.du.base import OptimizableDSPyModule, safe_extract_result
from soni.du.models import DialogueContext, NLUOutput
from soni.du.signatures import ExtractCommands

logger = logging.getLogger(__name__)


class SoniDU(OptimizableDSPyModule):
    """Dialogue Understanding module using DSPy.

    Features:
    - Native async with .acall() (more efficient than asyncify)
    - Optional ChainOfThought reasoning (configurable)
    - Pydantic types for structured I/O
    - MIPROv2/GEPA optimization support
    - Save/load for persistence
    """

    # Priority-ordered optimization files
    optimized_files = [
        "baseline_v1_gepa.json",
        "baseline_v1_miprov2.json",
        "baseline_v1.json",
    ]

    # Default: use ChainOfThought for better reasoning
    default_use_cot = True

    def _create_extractor(self, use_cot: bool) -> dspy.Module:
        """Create the command extractor predictor."""
        if use_cot:
            return dspy.ChainOfThought(ExtractCommands)
        return dspy.Predict(ExtractCommands)

    async def aforward(
        self,
        user_message: str,
        context: DialogueContext,
        history: list[dict[str, str]] | None = None,
    ) -> NLUOutput:
        """Extract commands from user message (async).

        Primary async interface matching DUProtocol.
        Uses native .acall() for async LM calls - more efficient
        than wrapping with asyncify.
        """
        history_obj = dspy.History(messages=history or [])

        try:
            result = await self.extractor.acall(
                user_message=user_message,
                context=context,
                history=history_obj,
            )
            # Validate and extract result safely
            return safe_extract_result(
                result.result,
                NLUOutput,
                default_factory=lambda: NLUOutput(commands=[], confidence=0.0),
                context="NLU extraction",
            )

        except Exception as e:
            logger.error(f"NLU extraction failed: {e}", exc_info=True)
            return NLUOutput(commands=[], confidence=0.0)

    def forward(
        self,
        user_message: str,
        context: DialogueContext,
        history: list[dict[str, str]] | None = None,
    ) -> NLUOutput:
        """Sync version (for testing/optimization)."""
        history_obj = dspy.History(messages=history or [])
        result = self.extractor(
            user_message=user_message,
            context=context,
            history=history_obj,
        )
        return safe_extract_result(
            result.result,
            NLUOutput,
            default_factory=lambda: NLUOutput(commands=[], confidence=0.0),
            context="NLU forward pass",
        )
