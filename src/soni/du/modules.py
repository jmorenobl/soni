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
    Natural Language Understanding module for dialogue systems.

    This module analyzes user messages in dialogue context to:
    - Classify message type (slot value, confirmation, correction, interruption, etc.)
    - Extract slot values with metadata (confidence, action type, previous value)
    - Detect intent changes and digressions
    - Resolve temporal expressions using current datetime

    Data Flow
    ---------
    Input:
        - user_message (str): Raw user input
        - history (dspy.History): Conversation history
        - context (DialogueContext): Current state (flow, slots, conversation phase)
        - current_datetime (str): ISO timestamp for temporal resolution

    Output:
        - NLUOutput: Structured analysis with message_type, command, slots, confidence

    For detailed data structure specifications, see DATA_STRUCTURES.md.

    Usage
    -----
    The module provides multiple interfaces for different use cases:

    1. **predict()** - Main async interface for production runtime
       - High-level API with caching and post-processing
       - Accepts structured types (dspy.History, DialogueContext)
       - Returns NLUOutput Pydantic model
       - Use this in production code

    2. **understand()** - Dict-based async interface for compatibility
       - Implements INLUProvider protocol
       - Accepts dict-based dialogue_context
       - Returns dict representation of NLUOutput
       - Use this when integrating with dict-based systems

    3. **forward()** - Sync interface for DSPy optimizers
       - Used during optimization/training
       - Called by MIPROv2, BootstrapFewShot, etc.
       - Do not call directly in production

    4. **aforward()** - Async version of forward()
       - Used internally by predict()
       - Do not call directly

    Optimization
    ------------
    - use_cot=False (default): Use Predict for speed and efficiency
      - Faster inference
      - Fewer tokens
      - Sufficient for most dialogue scenarios

    - use_cot=True: Use ChainOfThought for debugging and precision
      - Slower inference
      - More tokens (shows reasoning)
      - Useful for debugging NLU behavior
      - Useful when precision is critical

    Compatible with DSPy optimizers:
    - MIPROv2 (recommended for dialogue NLU)
    - BootstrapFewShot
    - COPRO
    - Others (see DSPy docs)

    Examples
    --------
    Basic usage with structured types:

    >>> import dspy
    >>> from soni.du.modules import SoniDU
    >>> from soni.du.models import DialogueContext
    >>>
    >>> # Initialize module
    >>> nlu = SoniDU(use_cot=False)
    >>>
    >>> # Prepare inputs
    >>> user_message = "I want to fly to Madrid"
    >>> history = dspy.History(messages=[])
    >>> context = DialogueContext(
    ...     current_flow="book_flight",
    ...     expected_slots=["destination", "departure_date"],
    ...     current_slots={},
    ...     conversation_state="waiting_for_slot",
    ... )
    >>>
    >>> # Call predict
    >>> result = await nlu.predict(user_message, history, context)
    >>> print(result.message_type)  # MessageType.SLOT_VALUE
    >>> print(result.slots[0].name)  # "destination"
    >>> print(result.slots[0].value)  # "Madrid"

    Dict-based interface (for compatibility):

    >>> result_dict = await nlu.understand(
    ...     user_message="Madrid",
    ...     dialogue_context={
    ...         "current_flow": "book_flight",
    ...         "expected_slots": ["destination"],
    ...         "current_slots": {},
    ...         "conversation_state": "waiting_for_slot",
    ...     },
    ... )
    >>> print(result_dict["message_type"])  # "slot_value"
    """

    def __init__(
        self,
        cache_size: int = 1000,
        cache_ttl: int = 300,
        use_cot: bool = False,
        load_baseline: bool = True,
    ) -> None:
        """Initialize Natural Language Understanding module.

        Args:
            cache_size: Maximum number of cached NLU results (default: 1000)
            cache_ttl: Cache entry lifetime in seconds (default: 300 = 5 minutes)
            use_cot: Predictor mode selection (default: False)
                - False: Use Predict (faster, recommended for production)
                - True: Use ChainOfThought (slower, better for debugging)
            load_baseline: Auto-load baseline optimization if available (default: True)
                - True: Loads pre-trained baseline_v1.json from framework
                - False: Use unoptimized module (only for testing/development)

        Note:
            The module requires dspy.configure(lm=...) to be called before use.
            See DSPy documentation for LM configuration.

            The baseline optimization is automatically loaded to provide
            reasonable out-of-the-box performance. You can override it by
            calling load() with a custom optimized module path.
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

        # Auto-load baseline optimization if available
        if load_baseline:
            self._load_baseline_optimization()

    def forward(
        self,
        user_message: str,
        history: dspy.History,
        context: DialogueContext,
        current_datetime: str = "",
    ) -> dspy.Prediction:
        """Synchronous forward pass for DSPy optimizers.

        This method is called by DSPy optimizers during training/optimization.
        Do NOT call this method directly in production code - use predict() instead.

        Args:
            user_message: User's input message to analyze
            history: Conversation history (dspy.History)
            context: Current dialogue state (DialogueContext)
            current_datetime: Current datetime in ISO format (auto-generated if empty)

        Returns:
            dspy.Prediction with result field containing NLUOutput

        Note:
            Used by MIPROv2, BootstrapFewShot, and other DSPy optimizers.
            For production use, call predict() or understand() instead.
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
        """Asynchronous forward pass for production runtime.

        This method is called internally by predict(). Do NOT call directly.

        Args:
            user_message: User's input message to analyze
            history: Conversation history (dspy.History)
            context: Current dialogue state (DialogueContext)
            current_datetime: Current datetime in ISO format (auto-generated if empty)

        Returns:
            dspy.Prediction with result field containing NLUOutput

        Note:
            Uses async LM calls via DSPy's adapter system.
            Called internally by predict() - use that method instead.
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
            available_flows=dialogue_context.get("available_flows", {}),
            current_flow=dialogue_context.get("current_flow", "none"),
            expected_slots=dialogue_context.get("expected_slots", []),
            current_prompted_slot=dialogue_context.get("waiting_for_slot"),
            conversation_state=dialogue_context.get("conversation_state"),
        )

        return history, context

    async def understand(
        self,
        user_message: str,
        dialogue_context: dict[str, Any],
    ) -> dict[str, Any]:
        """Analyze user message with NLU (dict-based interface for compatibility).

        This method implements the INLUProvider protocol for compatibility with
        dict-based systems. Internally converts dicts to structured types and
        delegates to predict().

        Use this method when integrating with systems that use dict-based state
        (e.g., legacy code, external integrations). For new code, prefer predict().

        Args:
            user_message: User's input message to analyze
            dialogue_context: Dict with keys:
                - current_slots (dict): Already filled slots
                - expected_slots (list[str]): Expected slot names
                - current_flow (str): Active flow name
                - conversation_state (str): Current conversation phase
                - available_flows (dict): Available flows {name: description}
                - available_actions (list[str]): Available action names
                - history (list): Conversation messages

        Returns:
            Dict representation of NLUOutput with keys:
                - message_type (str): Type of message
                - command (str | None): Intent/flow name
                - slots (list[dict]): Extracted slot values
                - confidence (float): Overall confidence
                - confirmation_value (bool | None): For confirmations

        Example:
            >>> result = await nlu.understand(
            ...     user_message="Madrid",
            ...     dialogue_context={
            ...         "current_flow": "book_flight",
            ...         "expected_slots": ["destination"],
            ...         "current_slots": {},
            ...         "conversation_state": "waiting_for_slot",
            ...     },
            ... )
            >>> print(result["message_type"])  # "slot_value"
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
        """Analyze user message with NLU (main production interface).

        This is the primary method for NLU analysis in production. It provides:
        - Structured type inputs/outputs
        - Automatic caching (avoid re-analyzing same inputs)
        - Post-processing (validate slots, normalize confirmation values)
        - Internal datetime management

        Args:
            user_message: User's input message to analyze
            history: Conversation history (dspy.History)
            context: Current dialogue state (DialogueContext)

        Returns:
            NLUOutput: Structured analysis with message_type, command, slots, confidence

        Example:
            >>> result = await nlu.predict(user_message="Madrid", history=history, context=context)
            >>> print(result.message_type)  # MessageType.SLOT_VALUE
            >>> print(result.slots[0].name)  # "destination"
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

        # Post-process to ensure correct slot actions
        result = self._post_process_result(result, context)

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

    def _post_process_result(self, result: NLUOutput, context: DialogueContext) -> NLUOutput:
        """
        Post-process NLU result to ensure correctness.

        This complements the LLM's work by:
        1. Filtering out invalid slot names
        2. Detecting corrections/modifications based on current_slots
        3. Adding previous_value where needed
        4. Validating and normalizing confirmation_value
        """
        # 1. Filter invalid slot names
        valid_slots = [slot for slot in result.slots if slot.name in context.expected_slots]

        # 2. Fix slot actions based on current_slots
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

        # 3. Validate and normalize confirmation_value
        # Handle type conversion (DSPy may return string "True"/"False" or bool)
        if hasattr(result, "confirmation_value") and result.confirmation_value is not None:
            cv = result.confirmation_value
            if isinstance(cv, bool):
                confirmation_value = cv
            elif isinstance(cv, str):
                if cv.lower() in ("true", "yes", "confirmed"):
                    confirmation_value = True
                elif cv.lower() in ("false", "no", "denied"):
                    confirmation_value = False
                else:
                    confirmation_value = None
            else:
                confirmation_value = None
        else:
            confirmation_value = None

        # Validation: confirmation_value should only be set for CONFIRMATION messages
        if result.message_type != MessageType.CONFIRMATION:
            confirmation_value = None

        # Set the normalized value
        result.confirmation_value = confirmation_value

        # 4. Adjust confidence for unclear confirmations
        if result.message_type == MessageType.CONFIRMATION and confirmation_value is None:
            # Unclear confirmation - lower confidence
            result.confidence = min(result.confidence, 0.6)
            logger.warning(
                f"Confirmation detected but value unclear (message_type=CONFIRMATION, "
                f"confirmation_value=None). Setting confidence to {result.confidence}"
            )

        return result

    def _load_baseline_optimization(self) -> None:
        """Load baseline pre-trained optimization if available.

        This method attempts to load the framework's baseline optimization
        (baseline_v1.json) to provide reasonable out-of-the-box performance.

        If the baseline file doesn't exist (e.g., in development), the module
        continues with the unoptimized predictor. This is silent to avoid
        warnings during development/testing.

        The baseline can be regenerated with:
            uv run python scripts/generate_baseline_optimization.py
        """
        from pathlib import Path

        # Find baseline optimization relative to this module
        module_dir = Path(__file__).parent
        baseline_path = module_dir / "optimized" / "baseline_v1.json"

        if baseline_path.exists():
            try:
                self.load(str(baseline_path))
                logger.info(f"Loaded baseline NLU optimization from {baseline_path.name}")
            except Exception as e:
                logger.warning(
                    f"Failed to load baseline optimization from {baseline_path}: {e}. "
                    f"Using unoptimized module."
                )
        else:
            logger.debug(
                f"Baseline optimization not found at {baseline_path}. "
                f"Using unoptimized module. Generate with: "
                f"uv run python scripts/generate_baseline_optimization.py"
            )
