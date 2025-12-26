"""ResponseRephraser - DSPy module for polishing responses."""

from typing import Literal

import dspy

from soni.du.base import OptimizableDSPyModule
from soni.du.signatures.rephrase_response import RephraserSignature

# Type alias for supported tones
RephraseTone = Literal["friendly", "professional", "formal"]


class ResponseRephraser(OptimizableDSPyModule):
    """DSPy module for contextual response rephrasing.

    Features:
    - Contextual polishing based on conversation history
    - Configurable tone (friendly, professional, formal)
    - Fact preservation (numbers, dates, names)
    - Optional (can be disabled for determinism)

    Usage:
        # Runtime (async)
        polished = await rephraser.acall(template, context)

        # Optimization (sync)
        polished = rephraser(template, context)
    """

    # Priority-ordered optimization files
    optimized_files = [
        "rephraser_miprov2.json",
        "rephraser_gepa.json",
    ]

    # Default: no ChainOfThought (simple rephrasing task)
    default_use_cot = False

    def __init__(self, tone: RephraseTone = "friendly", use_cot: bool | None = None):
        """Initialize rephraser with specified tone.

        Args:
            tone: Desired response tone (friendly, professional, formal)
            use_cot: If True, use ChainOfThought for reasoning.
                     If False, use simple Predict (faster, less tokens).
                     If None, use class default.
        """
        super().__init__(use_cot=use_cot)
        self.tone = tone

    def _create_extractor(self, use_cot: bool) -> dspy.Module:
        """Create the DSPy predictor for rephrasing."""
        if use_cot:
            return dspy.ChainOfThought(RephraserSignature)
        return dspy.Predict(RephraserSignature)

    async def aforward(self, template: str, context: str) -> str:
        """Polish a template response (async).

        Args:
            template: Original template response to polish
            context: Recent conversation history for context

        Returns:
            Polished response preserving all facts
        """
        result = await self.extractor.acall(
            template_response=template,
            conversation_context=context,
            tone=self.tone,
        )
        return str(result.polished_response)

    def forward(self, template: str, context: str) -> str:
        """Sync version for DSPy optimization.

        Args:
            template: Original template response to polish
            context: Recent conversation history for context

        Returns:
            Polished response preserving all facts
        """
        result = self.extractor(
            template_response=template,
            conversation_context=context,
            tone=self.tone,
        )
        return str(result.polished_response)
