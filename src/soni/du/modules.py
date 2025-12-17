"""DSPy modules for dialogue understanding.

Async-first design using native .acall() method.
"""

import logging
from pathlib import Path

import dspy

from soni.du.models import DialogueContext, NLUOutput
from soni.du.signatures import ExtractCommands

logger = logging.getLogger(__name__)


class SoniDU(dspy.Module):
    """Dialogue Understanding module using DSPy.

    Features:
    - Native async with .acall() (more efficient than asyncify)
    - Optional ChainOfThought reasoning (configurable)
    - Pydantic types for structured I/O
    - MIPROv2 optimization support
    - Save/load for persistence
    """

    def __init__(self, use_cot: bool = True):
        """Initialize SoniDU.

        Args:
            use_cot: If True, use ChainOfThought for reasoning.
                     If False, use simple Predict (faster, less tokens).
        """
        super().__init__()
        if use_cot:
            self.extractor = dspy.ChainOfThought(ExtractCommands)
        else:
            self.extractor = dspy.Predict(ExtractCommands)

    @classmethod
    def create_with_best_model(cls, use_cot: bool = True) -> "SoniDU":
        """Create SoniDU instance with the best available optimized model.

        Automatically searches for optimization files in `src/soni/du/optimized`
        with the following priority:
        1. GEPA (Most advanced)
        2. MIPROv2 (Stable fallback)
        3. Baseline (Legacy)

        If none found, returns a standard zero-shot instance.
        """
        instance = cls(use_cot=use_cot)

        base_path = Path(__file__).parent / "optimized"
        optimized_files = [
            "baseline_v1_gepa.json",
            "baseline_v1_miprov2.json",
            "baseline_v1.json",
        ]

        for filename in optimized_files:
            file_path = base_path / filename
            if file_path.exists():
                logger.info(f"Loading optimized NLU module from {file_path}")
                try:
                    instance.load(str(file_path))
                    break
                except Exception as e:
                    logger.warning(f"Failed to load optimized module {filename}: {e}")
            else:
                logger.debug(f"Optimized module not found: {filename}")
        else:
            logger.info("No optimized NLU module found, using default zero-shot.")

        return instance

    async def aforward(
        self,
        user_message: str,
        context: DialogueContext,
        history: list[dict[str, str]] | None = None,
    ) -> NLUOutput:
        """Extract commands from user message (async).

        Uses native .acall() for async LM calls - more efficient
        than wrapping with asyncify.
        """
        # Note: dspy methods typically return Prediction with output fields
        # Our signature output field is 'result' of type NLUOutput.
        history_obj = dspy.History(messages=history or [])

        try:
            result = await self.extractor.acall(
                user_message=user_message,
                context=context,
                history=history_obj,
            )
            # dspy Prediction object attributes match output fields
            return result.result  # type: ignore

        except Exception as e:
            logger.error(f"NLU extraction failed: {e}", exc_info=True)
            # Return safe fallback - no commands, zero confidence
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
        return result.result  # type: ignore
