"""DSPy modules for dialogue understanding.

Async-first design using native .acall() method.
"""

import dspy

from soni.du.models import DialogueContext, NLUOutput
from soni.du.signatures import ExtractCommands


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
        # Wrap history in dspy.History object as expected by signature
        history_obj = dspy.History(messages=history or [])
        result = await self.extractor.acall(
            user_message=user_message,
            context=context,
            history=history_obj,
        )

        # dspy Prediction object attributes match output fields
        return result.result  # type: ignore

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
