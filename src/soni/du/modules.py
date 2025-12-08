"""DSPy modules for Dialogue Understanding."""

import hashlib
import json
import logging
from datetime import datetime
from typing import Any

import dspy
from cachetools import TTLCache

from soni.du.models import DialogueContext, MessageType, NLUOutput, SlotAction
from soni.du.signatures import DialogueUnderstanding

logger = logging.getLogger(__name__)


class SoniDU(dspy.Module):
    """
    Soni Dialogue Understanding module with structured types.

    This module provides:
    - Type-safe async interface for runtime
    - Sync interface for DSPy optimizers
    - Automatic prompt optimization via DSPy
    - Structured Pydantic models throughout
    - Configurable predictor: Predict (fast) or ChainOfThought (precise)

    Performance Notes:
    - Predict (use_cot=False): Faster, fewer tokens, sufficient for most cases
    - ChainOfThought (use_cot=True): Slower, more tokens, shows reasoning,
      useful when precision is critical or debugging NLU behavior
    """

    def __init__(self, cache_size: int = 1000, cache_ttl: int = 300, use_cot: bool = False) -> None:
        """Initialize SoniDU module.

        Args:
            cache_size: Maximum number of cached NLU results
            cache_ttl: Time-to-live for cache entries in seconds
            use_cot: If True, use ChainOfThought (slower, more precise).
                     If False, use Predict (faster, less tokens). Default: False
        """
        super().__init__()  # CRITICAL: Must call super().__init__()

        # Create predictor based on use_cot parameter
        if use_cot:
            # ChainOfThought: More precise, shows reasoning, but slower and uses more tokens
            self.predictor = dspy.ChainOfThought(DialogueUnderstanding)
            logger.debug("SoniDU initialized with ChainOfThought (use_cot=True)")
        else:
            # Predict: Faster, fewer tokens, sufficient for most cases
            self.predictor = dspy.Predict(DialogueUnderstanding)
            logger.debug("SoniDU initialized with Predict (use_cot=False, default)")

        # Optional caching layer
        self.nlu_cache: TTLCache[str, NLUOutput] = TTLCache(
            maxsize=cache_size,
            ttl=cache_ttl,
        )

        self.use_cot = use_cot  # Store for reference

    def forward(
        self,
        user_message: str,
        history: dspy.History,
        context: DialogueContext,
        current_datetime: str = "",
    ) -> dspy.Prediction:
        """Sync forward pass for DSPy optimizers.

        Used during optimization/training with MIPROv2, BootstrapFewShot, etc.

        Args:
            user_message: User's input message
            history: Conversation history (dspy.History)
            context: Dialogue context with slots, actions, flows (DialogueContext)
            current_datetime: Current datetime in ISO format

        Returns:
            dspy.Prediction object with result field containing NLUOutput
        """
        return self.predictor(
            user_message=user_message,
            history=history,
            context=context,
            current_datetime=current_datetime,
        )

    async def aforward(
        self,
        user_message: str,
        history: dspy.History,
        context: DialogueContext,
        current_datetime: str = "",
    ) -> dspy.Prediction:
        """Async forward pass for production runtime.

        Called internally by acall(). Uses async LM calls via DSPy's adapter system.

        Args:
            Same as forward()

        Returns:
            dspy.Prediction object with result field containing NLUOutput
        """
        # DSPy's predictor.acall() handles async LM calls
        return await self.predictor.acall(
            user_message=user_message,
            history=history,
            context=context,
            current_datetime=current_datetime,
        )

    @staticmethod
    def _dict_to_structured_types(
        dialogue_context: dict[str, Any],
    ) -> tuple[dspy.History, DialogueContext]:
        """
        Convert dict-based dialogue context to structured types.

        This is a pure function (no side effects) that centralizes the conversion
        logic to avoid duplication (DRY principle).

        Used by SoniDU.understand() to adapt dict-based interface
        to structured types for predict().

        Args:
            dialogue_context: Dict with current_slots, available_actions, etc.

        Returns:
            Tuple of (history, context) as structured types
        """
        # Convert history from dialogue_context
        history_messages = dialogue_context.get("history", [])
        history = dspy.History(messages=history_messages)

        # Convert dialogue_context to DialogueContext model
        # Use waiting_for_slot as current_prompted_slot for NLU prioritization
        context = DialogueContext(
            current_slots=dialogue_context.get("current_slots", {}),
            available_actions=dialogue_context.get("available_actions", []),
            available_flows=dialogue_context.get("available_flows", []),
            current_flow=dialogue_context.get("current_flow", "none"),
            expected_slots=dialogue_context.get("expected_slots", []),
            current_prompted_slot=dialogue_context.get("waiting_for_slot"),
        )

        return history, context

    async def understand(
        self,
        user_message: str,
        dialogue_context: dict[str, Any],
    ) -> dict[str, Any]:
        """High-level async interface for NLU (INLUProvider interface).

        This method implements INLUProvider.understand() to provide dict-based
        interface compatibility. It adapts dict-based input to structured types
        and delegates to predict() (the main implementation).

        Args:
            user_message: User's input message
            dialogue_context: Dict with current_slots, available_actions, etc.

        Returns:
            Dict with message_type, command, slots, and confidence
        """
        # Convert dict to structured types (DRY: uses centralized conversion)
        history, context = self._dict_to_structured_types(dialogue_context)

        # Delegate to predict() (the actual implementation)
        result = await self.predict(user_message, history, context)

        # Convert structured result back to dict
        return dict(result.model_dump())

    async def predict(
        self,
        user_message: str,
        history: dspy.History,
        context: DialogueContext,
    ) -> NLUOutput:
        """High-level async prediction method with caching.

        This is the main entry point for runtime NLU calls. Provides:
        - Structured type inputs (dspy.History, DialogueContext)
        - NLUOutput Pydantic model output
        - Automatic caching
        - Internal datetime management

        Args:
            user_message: User's input message
            history: Conversation history (dspy.History)
            context: Dialogue context (DialogueContext)

        Returns:
            NLUOutput with message_type, command, slots, and confidence
        """
        # Calculate current datetime (encapsulation principle)
        current_datetime_str = datetime.now().isoformat()

        # Check cache
        cache_key = self._get_cache_key(user_message, history, context)

        if cache_key in self.nlu_cache:
            cached_result = self.nlu_cache[cache_key]
            # Type assertion for mypy
            assert isinstance(cached_result, NLUOutput)
            return cached_result

        # Call via acall() (public async method)
        prediction = await self.acall(
            user_message=user_message,
            history=history,
            context=context,
            current_datetime=current_datetime_str,
        )

        # Extract structured result (no parsing needed!)
        # Type assertion needed because DSPy returns Any
        result = prediction.result
        if not isinstance(result, NLUOutput):
            raise TypeError(f"Expected NLUOutput, got {type(result)}")

        # Post-process to ensure correct slot actions and assignments
        result = self._post_process_result(result, context, user_message)

        # Cache and return
        self.nlu_cache[cache_key] = result

        return result

    def _get_cache_key(
        self,
        user_message: str,
        history: dspy.History,
        context: DialogueContext,
    ) -> str:
        """Generate cache key from structured inputs."""
        data = {
            "message": user_message,
            "history_length": len(history.messages),
            "context": context.model_dump(),
        }

        json_str = json.dumps(data, sort_keys=True)
        return hashlib.sha256(json_str.encode()).hexdigest()

    def _post_process_result(
        self, result: NLUOutput, context: DialogueContext, user_message: str = ""
    ) -> NLUOutput:
        """
        Post-process NLU result to ensure correctness.

        This complements the LLM's work by:
        1. Filtering out invalid slot names
        2. Detecting corrections/modifications based on current_slots
        3. Adding previous_value where needed
        4. Correcting slot assignment when current_prompted_slot is set
        """
        # 1. Filter invalid slot names
        valid_slots = [slot for slot in result.slots if slot.name in context.expected_slots]

        # 2. Fix slot assignment if current_prompted_slot is set
        # This handles cases where NLU extracts wrong slot (e.g., "Madrid" -> destination
        # when we're waiting for origin)
        if (
            context.current_prompted_slot
            and context.current_prompted_slot in context.expected_slots
        ):
            # Check if current_prompted_slot was extracted
            prompted_slot_extracted = any(
                slot.name == context.current_prompted_slot for slot in valid_slots
            )

            if not prompted_slot_extracted and valid_slots:
                # NLU extracted a different slot, but we're waiting for current_prompted_slot
                # If message is simple (likely a direct answer), correct the slot assignment
                # Simple = short message (1-3 words) that looks like a direct answer
                message_words = user_message.strip().split()
                is_simple_message = len(message_words) <= 3 and all(
                    len(word) < 20 for word in message_words
                )

                if is_simple_message and result.message_type == MessageType.SLOT_VALUE:
                    # Take the first extracted slot's value and reassign to current_prompted_slot
                    first_slot = valid_slots[0]
                    logger.debug(
                        f"Correcting slot assignment: NLU extracted '{first_slot.name}' "
                        f"but we're waiting for '{context.current_prompted_slot}'. "
                        f"Reassigning value '{first_slot.value}' to '{context.current_prompted_slot}'."
                    )

                    # Create new slot with correct name
                    from soni.du.models import SlotValue

                    corrected_slot = SlotValue(
                        name=context.current_prompted_slot,
                        value=first_slot.value,
                        confidence=first_slot.confidence,
                        action=first_slot.action,
                        previous_value=first_slot.previous_value,
                    )

                    # Replace the incorrectly extracted slot
                    valid_slots = [corrected_slot]

        # 3. Fix slot actions based on current_slots
        for slot in valid_slots:
            if slot.name in context.current_slots:
                current_value = context.current_slots[slot.name]

                # If value is different, it might be a correction/modification
                if slot.value != current_value:
                    # If LLM said PROVIDE but it's changing existing value
                    if slot.action == SlotAction.PROVIDE:
                        # Infer based on message_type
                        if result.message_type == MessageType.CORRECTION:
                            slot.action = SlotAction.CORRECT
                        elif result.message_type == MessageType.MODIFICATION:
                            slot.action = SlotAction.MODIFY

                    # Always set previous_value for corrections/modifications
                    if slot.action in (SlotAction.CORRECT, SlotAction.MODIFY):
                        slot.previous_value = current_value

        result.slots = valid_slots
        return result
