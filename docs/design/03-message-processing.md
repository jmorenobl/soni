# Message Processing Flow

**Document Version**: 1.0
**Last Updated**: 2025-12-02
**Status**: Draft

## Table of Contents

1. [Overview](#overview)
2. [Processing Pipeline](#processing-pipeline)
3. [Context-Aware Routing](#context-aware-routing)
4. [Intent Detection](#intent-detection)
5. [Direct Slot Mapping](#direct-slot-mapping)
6. [Message Router Implementation](#message-router-implementation)
7. [Performance Optimizations](#performance-optimizations)

---

## Overview

The message processing flow is the **core innovation** of this redesign. Instead of always calling NLU on every turn, the system uses **context-aware routing** to determine the most efficient way to process each message.

### Key Innovation

**OLD Design** (Always NLU):
```
Every Message → NLU → Extract Slots → Update State → Execute Graph
```

**NEW Design** (Context-Aware):
```
Every Message → Context Router → Decision:
  ├─ If WAITING_FOR_SLOT → Direct Mapping (fast, no LLM)
  ├─ If IDLE → NLU (need to understand intent)
  └─ If EXECUTING_ACTION → Wait for completion
```

### Performance Impact

| Scenario | OLD | NEW | Savings |
|----------|-----|-----|---------|
| **Simple slot collection** | NLU call (300ms, ~500 tokens) | Direct mapping (<10ms) | **97% latency, 100% tokens** |
| **Intent change** | NLU call (300ms) | NLU call (300ms) | **0% (necessary)** |
| **Multi-slot message** | NLU call (300ms) | NLU call (300ms) | **0% (necessary)** |

**Typical 4-turn booking flow**:
- OLD: 4 NLU calls = 1200ms, ~2000 tokens
- NEW: 1 NLU call + 3 direct mappings = 330ms, ~500 tokens
- **Savings: 72% latency, 75% tokens**

---

## Processing Pipeline

### Complete Flow

```
┌─────────────────────────────────────────────────────────┐
│  1. User Message Received                                │
│     - Validate input                                     │
│     - Sanitize message                                   │
└────────────────────┬────────────────────────────────────┘
                     │
┌────────────────────▼────────────────────────────────────┐
│  2. Load Dialogue State                                  │
│     - Load from checkpoint (thread_id = user_id)        │
│     - Add user message to state.messages                │
└────────────────────┬────────────────────────────────────┘
                     │
┌────────────────────▼────────────────────────────────────┐
│  3. Context-Aware Routing (NEW)                          │
│     - Analyze conversation_state                         │
│     - Decide: Direct Mapping, NLU, or Wait              │
└────────────────────┬────────────────────────────────────┘
                     │
         ┌───────────┴──────────┐
         │                      │
┌────────▼──────────┐  ┌───────▼────────┐
│  Direct Mapping   │  │  NLU Call      │
│  (Fast path)      │  │  (Full NLU)    │
└────────┬──────────┘  └───────┬────────┘
         │                      │
         └───────────┬──────────┘
                     │
┌────────────────────▼────────────────────────────────────┐
│  4. Determine Execution Entry Point (NEW)                │
│     - If resuming: start from current_step              │
│     - If new flow: start from START                     │
└────────────────────┬────────────────────────────────────┘
                     │
┌────────────────────▼────────────────────────────────────┐
│  5. Execute Graph                                        │
│     - Run LangGraph nodes                               │
│     - Update state after each node                      │
│     - Stop on interactive pause (slot collection)       │
└────────────────────┬────────────────────────────────────┘
                     │
┌────────────────────▼────────────────────────────────────┐
│  6. Generate Response                                    │
│     - Extract last_response from state                  │
│     - Apply response templates if needed                │
└────────────────────┬────────────────────────────────────┘
                     │
┌────────────────────▼────────────────────────────────────┐
│  7. Save Checkpoint                                      │
│     - Persist updated state                             │
│     - Save conversation_state and current_step          │
└────────────────────┬────────────────────────────────────┘
                     │
┌────────────────────▼────────────────────────────────────┐
│  8. Return Response to User                              │
└─────────────────────────────────────────────────────────┘
```

---

## Context-Aware Routing

### Routing Decision Tree

```python
async def route_message(
    self,
    user_msg: str,
    state: DialogueState
) -> MessageRoute:
    """
    Decide how to process message based on conversation context.

    This is the CRITICAL routing logic that enables performance optimization.
    """

    # ===== Case 1: Waiting for specific slot =====
    if state.conversation_state == ConversationState.WAITING_FOR_SLOT:
        # Check if message looks like a simple value or contains intent
        if self._is_simple_value(user_msg):
            # Fast path: Direct mapping, no NLU
            return MessageRoute(
                type="direct_slot_mapping",
                slot=state.waiting_for_slot,
            )
        elif self._has_intent_markers(user_msg):
            # User is changing intent, need NLU
            return MessageRoute(
                type="nlu_understanding",
                reason="intent_change_detected",
            )
        else:
            # Ambiguous, use hybrid approach
            return MessageRoute(
                type="hybrid",
                slot=state.waiting_for_slot,
            )

    # ===== Case 2: Executing action =====
    elif state.conversation_state == ConversationState.EXECUTING_ACTION:
        # User shouldn't send messages during action execution
        # But if they do, queue it for after action completes
        return MessageRoute(
            type="queue",
            reason="action_in_progress",
        )

    # ===== Case 3: Idle or need understanding =====
    elif state.conversation_state in [
        ConversationState.IDLE,
        ConversationState.UNDERSTANDING,
    ]:
        # Need NLU to understand intent
        return MessageRoute(
            type="nlu_understanding",
            reason="need_intent_understanding",
        )

    # ===== Case 4: Error state =====
    elif state.conversation_state == ConversationState.ERROR:
        # Try to recover via NLU
        return MessageRoute(
            type="nlu_understanding",
            reason="error_recovery",
        )

    # ===== Default: Use NLU =====
    else:
        return MessageRoute(
            type="nlu_understanding",
            reason="default_case",
        )
```

### MessageRoute Type

```python
from dataclasses import dataclass
from typing import Literal

@dataclass
class MessageRoute:
    """
    Result of message routing decision.

    Tells the system how to process the current message.
    """

    type: Literal[
        "direct_slot_mapping",  # Map message directly to slot (fast)
        "nlu_understanding",     # Call NLU to understand intent
        "hybrid",                # Try direct mapping, fallback to NLU
        "queue",                 # Queue message for later
    ]

    slot: str | None = None
    """Slot name if type == 'direct_slot_mapping'"""

    reason: str | None = None
    """Why this route was chosen (for debugging/logging)"""
```

---

## Intent Detection

### Intent Markers

**Purpose**: Detect when user is changing intent vs providing a value.

**Examples**:

```python
# Intent markers (user wants something different)
INTENT_MARKERS = [
    # Command verbs
    "book", "cancel", "change", "modify", "help", "restart",

    # Questions
    "what", "how", "can you", "could you", "would you",

    # Negations
    "no", "not", "don't", "nope", "never",

    # Corrections
    "actually", "wait", "instead", "rather",

    # Flow switching
    "switch to", "start", "begin", "i want to",
]

def _has_intent_markers(self, message: str) -> bool:
    """
    Check if message contains intent markers.

    Returns:
        True if message likely contains a new intent/command
        False if message is likely just a value
    """
    msg_lower = message.lower()

    # Check for intent markers
    for marker in INTENT_MARKERS:
        if marker in msg_lower:
            return True

    # Check for questions (ends with '?')
    if message.strip().endswith("?"):
        return True

    # Check for multiple sentences (likely complex intent)
    if ". " in message or "! " in message:
        return True

    return False
```

### Simple Value Detection

```python
def _is_simple_value(self, message: str) -> bool:
    """
    Check if message is a simple value (not an intent).

    Simple values:
    - Single word: "Boston"
    - Number: "42"
    - Date-like: "tomorrow", "next Friday"
    - Short phrase: "New York"

    NOT simple values:
    - Questions: "What time is it?"
    - Commands: "Cancel the booking"
    - Corrections: "Actually, change it to Boston"
    """
    msg = message.strip()

    # Single word (likely a value)
    if " " not in msg:
        return True

    # Short phrase (2-4 words) without intent markers
    word_count = len(msg.split())
    if word_count <= 4 and not self._has_intent_markers(msg):
        return True

    # Date-like patterns
    date_patterns = [
        r"tomorrow",
        r"next \w+",  # "next Friday"
        r"\d{1,2}/\d{1,2}",  # "12/15"
        r"in \d+ days",
    ]
    for pattern in date_patterns:
        if re.search(pattern, msg, re.IGNORECASE):
            return True

    return False
```

---

## Slot Collection (Lightweight Approach)

> **Note**: The original "direct slot mapping" approach described below has been superseded by a more realistic DSPy-based lightweight collector. See `19-realistic-slot-collection-strategy.md` and `20-consolidated-design-decisions.md` for the final design.

### Context-Aware Slot Collection

When `conversation_state == WAITING_FOR_SLOT`:

```python
async def _collect_slot_lightweight(
    self,
    user_msg: str,
    slot_name: str,
    state: DialogueState,
) -> DialogueState:
    """
    Collect slot using lightweight DSPy-based collector.

    This is the OPTIMIZED PATH that handles realistic user behavior:
    - Slot values: "New York"
    - Intent changes: "Actually, I want to cancel"
    - Questions: "What cities do you support?"
    - Clarifications: "Why do you need this?"
    - Corrections: "Change it to Boston"

    Steps:
    1. Call lightweight DSPy collector
    2. Handle outcome based on type:
       - slot_value → Validate + normalize + update state
       - intent_change → Route to new intent
       - question → Answer + re-prompt
       - clarification → Explain + re-prompt
       - correction → Update + continue
       - ambiguous → Fall back to full NLU
    """

    # 1. Call lightweight collector
    try:
        result = await self.lightweight_collector.aforward(
            user_message=user_msg,
            slot_being_collected=slot_name,
            slot_prompt=state.last_response,
            conversation_context=self._build_context_string(state),
        )

        # Check confidence
        if result.confidence < 0.7 or result.outcome_type == "ambiguous":
            # Low confidence → Fall back to full NLU
            logger.info(f"Lightweight collector uncertain (confidence={result.confidence}), "
                       f"falling back to full NLU")
            return await self._nlu_understanding(user_msg, state)

        # 2. Handle outcome based on type
        if result.outcome_type == "slot_value":
            # Extract and validate
            raw_value = result.extracted_value
            slot_config = self.config.slots[slot_name]

            # Normalize
            normalized_value = await self.normalizer.normalize(raw_value, slot_config)

            # Validate
            if slot_config.validator:
                is_valid = ValidatorRegistry.validate(
                    slot_config.validator,
                    normalized_value
                )
                if not is_valid:
                    return self._create_reprompt_state(
                        state,
                        slot_name,
                        error=f"Invalid format for {slot_name}"
                    )

            # Update state
            state.slots[slot_name] = normalized_value
            state.waiting_for_slot = None
            state.conversation_state = ConversationState.VALIDATING_SLOT
            return state

        elif result.outcome_type == "intent_change":
            # User wants to do something else → Use full NLU
            logger.info(f"Intent change detected: {result.detected_intent}")
            return await self._nlu_understanding(user_msg, state)

        elif result.outcome_type in ["question", "clarification"]:
            # Answer and re-prompt
            answer = await self._handle_user_question(result, slot_name)
            state.last_response = f"{answer}\n\n{state.last_response}"
            return state

        elif result.outcome_type == "correction":
            # Handle correction → Use full NLU to determine what to correct
            logger.info("User correction detected")
            return await self._nlu_understanding(user_msg, state)

        else:
            # Unknown outcome → Full NLU
            logger.warning(f"Unknown outcome type: {result.outcome_type}")
            return await self._nlu_understanding(user_msg, state)

    except Exception as e:
        # Any error → Fall back to full NLU
        logger.error(f"Lightweight collector failed: {e}, falling back to full NLU")
        return await self._nlu_understanding(user_msg, state)
```

---

## Message Router Implementation

### Complete RuntimeLoop.process_message()

```python
class RuntimeLoop:
    async def process_message(
        self,
        user_msg: str,
        user_id: str,
    ) -> str:
        """
        Process user message with context-aware routing.

        This is the main entry point for message processing.
        """

        # 1. Validate and sanitize
        sanitized_msg, sanitized_user_id = self._validate_inputs(user_msg, user_id)

        # 2. Load state
        state = await self._load_state(sanitized_user_id)

        # 3. Add user message to state
        state.messages.append({
            "role": "user",
            "content": sanitized_msg,
            "timestamp": time.time(),
        })
        state.turn_count += 1

        # 4. Context-aware routing (NEW)
        route = await self.route_message(sanitized_msg, state)

        logger.info(
            f"Message routing decision: {route.type}",
            extra={
                "user_id": sanitized_user_id,
                "conversation_state": state.conversation_state,
                "route_type": route.type,
                "route_reason": route.reason,
            }
        )

        # 5. Execute based on route
        if route.type == "direct_slot_mapping":
            # Fast path: direct mapping
            state = await self._direct_slot_mapping(
                sanitized_msg,
                route.slot,
                state
            )

        elif route.type == "nlu_understanding":
            # Full NLU path
            state = await self._nlu_understanding(sanitized_msg, state)

        elif route.type == "hybrid":
            # Try direct, fallback to NLU
            state = await self._hybrid_slot_mapping(
                sanitized_msg,
                route.slot,
                state
            )

        elif route.type == "queue":
            # Queue message for later
            state.metadata.setdefault("queued_messages", []).append(sanitized_msg)
            state.last_response = "Please wait while I complete the current action."

        # 6. Execute graph if needed
        if state.conversation_state != ConversationState.WAITING_FOR_SLOT:
            # Need to execute graph to continue flow
            entry_point = state.current_step or START
            result = await self._execute_graph_from(state, entry_point)
            state = DialogueState.from_dict(result)

        # 7. Save checkpoint
        await self._save_state(sanitized_user_id, state)

        # 8. Return response
        return state.last_response
```

---

## Performance Optimizations

### 1. NLU Result Caching

**Problem**: Same message might be sent multiple times (retries, corrections).

**Solution**: Cache NLU results by message + context hash.

```python
class NLUCache:
    def __init__(self, ttl: int = 60):
        self.cache: dict[str, tuple[NLUResult, float]] = {}
        self.ttl = ttl

    def get_cache_key(self, msg: str, context: NLUContext) -> str:
        """Generate cache key from message and context"""
        context_hash = hashlib.sha256(
            json.dumps({
                "msg": msg,
                "flow": context.current_flow,
                "actions": sorted(context.available_actions),
            }, sort_keys=True).encode()
        ).hexdigest()
        return context_hash

    async def get_or_predict(
        self,
        msg: str,
        context: NLUContext,
    ) -> NLUResult:
        """Get cached result or call NLU"""
        key = self.get_cache_key(msg, context)

        if key in self.cache:
            result, timestamp = self.cache[key]
            if time.time() - timestamp < self.ttl:
                logger.info("NLU cache hit", extra={"cache_key": key})
                return result

        # Cache miss or expired, call NLU
        result = await self.nlu_provider.predict(msg, context)
        self.cache[key] = (result, time.time())

        # Cleanup old entries
        self._cleanup_expired()

        return result

    def _cleanup_expired(self):
        """Remove expired cache entries"""
        now = time.time()
        expired = [
            k for k, (_, ts) in self.cache.items()
            if now - ts > self.ttl
        ]
        for k in expired:
            del self.cache[k]
```

### 2. Message History Pruning

**Problem**: Full message history grows unbounded, exploding tokens.

**Solution**: Keep only recent N messages or implement sliding window.

```python
def _prune_message_history(
    self,
    messages: list[dict[str, str]],
    max_messages: int = 10,
) -> list[dict[str, str]]:
    """
    Prune message history to prevent token explosion.

    Strategies:
    1. Keep only last N messages
    2. Keep all system prompts + last N user messages
    3. Summarize old messages (future enhancement)
    """

    if len(messages) <= max_messages:
        return messages

    # Keep last N messages
    return messages[-max_messages:]
```

### 3. Skip NLU When Confidence Not Needed

```python
async def _should_call_nlu(self, state: DialogueState) -> bool:
    """
    Decide if NLU call is necessary.

    Returns False (skip NLU) when:
    - conversation_state == WAITING_FOR_SLOT
    - Last message is simple value
    - Last NLU call was recent (<5s ago)
    """

    # Always call NLU if idle
    if state.conversation_state == ConversationState.IDLE:
        return True

    # Skip if waiting for slot and message is simple
    if state.conversation_state == ConversationState.WAITING_FOR_SLOT:
        user_msg = state.messages[-1]["content"]
        if self._is_simple_value(user_msg):
            return False

    # Skip if NLU was called very recently (< 5s)
    if state.last_nlu_call and (time.time() - state.last_nlu_call) < 5.0:
        return False

    # Default: call NLU
    return True
```

---

## Performance Benchmarks

### Expected Performance

**Scenario 1: Simple Slot Collection (4 turns)**
```
OLD:
  Turn 1: NLU (300ms) + collect (10ms) = 310ms
  Turn 2: NLU (300ms) + collect (10ms) = 310ms
  Turn 3: NLU (300ms) + collect (10ms) = 310ms
  Turn 4: NLU (300ms) + action (100ms) = 400ms
  TOTAL: 1330ms, ~2000 tokens

NEW:
  Turn 1: NLU (300ms) + collect (10ms) = 310ms
  Turn 2: Direct map (5ms) + collect (10ms) = 15ms
  Turn 3: Direct map (5ms) + collect (10ms) = 15ms
  Turn 4: Direct map (5ms) + action (100ms) = 105ms
  TOTAL: 445ms, ~500 tokens

IMPROVEMENT: 67% faster, 75% fewer tokens
```

**Scenario 2: Intent Change Mid-Flow (3 turns)**
```
Turn 1: Collect slot → User: "New York" → Direct map (fast)
Turn 2: Collect slot → User: "Actually, cancel" → Intent detected → NLU (necessary)
Turn 3: Process cancellation → NLU (necessary)

Savings: 1 unnecessary NLU call avoided in Turn 1
```

---

## Summary

This message processing design provides:

1. ✅ **Context-aware routing** based on conversation state
2. ✅ **Direct slot mapping** for simple values (no NLU)
3. ✅ **Intent detection** to catch user changes
4. ✅ **NLU caching** to avoid redundant calls
5. ✅ **Hybrid fallback** for ambiguous messages
6. ✅ **Performance**: 60-70% faster, 70-75% fewer tokens

**Critical Innovation**: The system knows "what it's waiting for" and can process simple responses without expensive NLU calls, while still detecting when the user changes intent.

---

**Next**: Read [04-graph-execution-model.md](04-graph-execution-model.md) for LangGraph integration details.
