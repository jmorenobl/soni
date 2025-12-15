"""DSPy modules for Dialogue Understanding (v2.0 Command-Driven)."""

import hashlib
import json
import logging
from datetime import datetime
from typing import cast

import dspy
from cachetools import TTLCache

from soni.core.commands import (
    Command,
    CorrectSlot,
    SetSlot,
)
from soni.du.models import DialogueContext, NLUOutput
from soni.du.signatures import DialogueUnderstanding

logger = logging.getLogger(__name__)


class SoniDU(dspy.Module):
    """
    Natural Language Understanding module (v2.0).

    Translates user messages into executable Commands using DSPy.
    """

    def __init__(
        self,
        cache_size: int = 1000,
        cache_ttl: int = 300,
        use_cot: bool = False,
        load_baseline: bool = True,
    ) -> None:
        super().__init__()

        # Initialize predictor
        if use_cot:
            self.predictor = dspy.ChainOfThought(DialogueUnderstanding)
        else:
            self.predictor = dspy.Predict(DialogueUnderstanding)

        self.nlu_cache: TTLCache[str, NLUOutput] = TTLCache(
            maxsize=cache_size,
            ttl=cache_ttl,
        )

        self.use_cot = use_cot
        if load_baseline:
            self._load_baseline_optimization()

    async def predict(
        self,
        user_message: str,
        history: dspy.History,
        context: DialogueContext,
    ) -> NLUOutput:
        """Analyze user message and return Commands."""
        current_datetime_str = datetime.now().isoformat()

        # Cache check
        cache_key = self._get_cache_key(user_message, history, context)
        if cache_key in self.nlu_cache:
            return cast(NLUOutput, self.nlu_cache[cache_key])

        # Async prediction
        prediction = await self.predictor.acall(
            user_message=user_message,
            history=history,
            context=context,
            current_datetime=current_datetime_str,
        )

        result = prediction.result
        if not isinstance(result, NLUOutput):
            # Fallback if DSPy returns raw dict or other type
            try:
                result = NLUOutput.model_validate(result)
            except Exception as e:
                logger.error(f"Failed to validate NLU capability: {e}")
                # Return empty result with low confidence
                result = NLUOutput(commands=[], confidence=0.0)

        # Post-process commands (validation/normalization)
        result = self._post_process_commands(result, context)

        self.nlu_cache[cache_key] = result
        return result

    def _post_process_commands(self, result: NLUOutput, context: DialogueContext) -> NLUOutput:
        """Validate and refine generated commands."""
        valid_commands: list[Command] = []

        for cmd in result.commands:
            # 1. Validate SetSlot commands against expected slots
            if isinstance(cmd, SetSlot):
                # Only allow SetSlot for expected slots or if starting a new flow (implied)
                if cmd.slot_name in context.expected_slots:
                    valid_commands.append(cmd)
                else:
                    logger.warning(f"Ignored SetSlot for unexpected slot: {cmd.slot_name}")

            # 2. Convert SetSlot to CorrectSlot if value exists and changes
            elif isinstance(cmd, SetSlot) and cmd.slot_name in context.current_slots:
                current_val = context.current_slots[cmd.slot_name]
                if cmd.value != current_val:
                    logger.info(f"Auto-converting SetSlot to CorrectSlot for {cmd.slot_name}")
                    valid_commands.append(CorrectSlot(slot_name=cmd.slot_name, new_value=cmd.value))
                else:
                    valid_commands.append(cmd)  # Re-setting same value is fine

            else:
                valid_commands.append(cmd)

        result.commands = valid_commands
        return result

    def _get_cache_key(
        self, user_message: str, history: dspy.History, context: DialogueContext
    ) -> str:
        data = {
            "message": user_message,
            "history_length": len(history.messages),
            "context": context.model_dump(),
        }
        json_str = json.dumps(data, sort_keys=True)
        return hashlib.sha256(json_str.encode()).hexdigest()

    def _load_baseline_optimization(self) -> None:
        """Load baseline weights (placeholder for now)."""
        pass
