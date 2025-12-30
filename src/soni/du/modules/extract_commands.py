"""Dialogue Understanding module using DSPy."""

import logging

import dspy

from soni.du.base import OptimizableDSPyModule, safe_extract_result
from soni.du.models import DialogueContext, NLUOutput
from soni.du.signatures.extract_commands import ExtractCommands

logger = logging.getLogger(__name__)


class CommandGenerator(OptimizableDSPyModule):
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

    def _convert_history(self, history: list) -> list[dict[str, str]]:
        """Convert mixed history types to DSPy-compatible dicts."""
        if not history:
            return []

        clean_history = []
        for msg in history:
            if isinstance(msg, dict):
                clean_history.append(msg)
            elif hasattr(msg, "content") and hasattr(msg, "type"):
                # Handle LangChain/Pydantic message objects
                role = (
                    "user" if msg.type == "human" else "assistant" if msg.type == "ai" else "system"
                )
                clean_history.append({"role": role, "content": str(msg.content)})
            else:
                # Fallback
                clean_history.append({"role": "user", "content": str(msg)})
        return clean_history

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
        history_list = self._convert_history(history or [])
        history_obj = dspy.History(messages=history_list)

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

    def forward(
        self,
        user_message: str,
        context: DialogueContext,
        history: list[dict[str, str]] | None = None,
    ) -> NLUOutput:
        """Sync version (for testing/optimization)."""
        history_list = self._convert_history(history or [])
        history_obj = dspy.History(messages=history_list)

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
