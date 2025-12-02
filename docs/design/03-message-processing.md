# Message Processing Flow

**Document Version**: 1.1
**Last Updated**: 2025-12-02
**Status**: ✅ Updated (Aligned with 01-architecture-overview.md)

> **Ground Truth**: See [01-architecture-overview.md](01-architecture-overview.md) for the definitive architecture. This document provides additional details on message processing.

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

The message processing flow is the **core design** of the system. It uses **context-aware NLU** with enriched prompts to understand user messages in the context of the current conversation state.

### Key Innovation

**OLD Design** (Context-unaware):
```
Every Message → NLU (no context) → Extract Slots → Update State → Execute Graph
```

**NEW Design** (Context-Aware):
```
Every Message → Context Router → Decision:
  ├─ If EXECUTING_ACTION → Wait for completion
  └─ Else → NLU with enriched context (conversation state, flow descriptions, paused flows)
```

### Design Philosophy

The system uses a **unified NLU approach**:
- Single DSPy module handles all understanding tasks
- Context-enriched prompts include: conversation state, waiting_for_slot, flow descriptions, paused flows
- NLU can detect: slot values, intent changes, digressions, resume requests
- Simpler architecture with one optimization point

**Typical 4-turn booking flow**:
- All messages: 4 NLU calls with context = ~1200ms, ~2000 tokens
- **Benefits**: Consistent behavior, accurate understanding, simpler to maintain

---

## Processing Pipeline (LangGraph Pattern)

### Complete Flow

> **Critical Pattern**: Every user message passes through the Understand Node (NLU) FIRST. LangGraph handles checkpointing and resumption automatically.

```
┌─────────────────────────────────────────────────────────┐
│  1. User Message Received                                │
│     - Validate input                                     │
│     - Sanitize message                                   │
└────────────────────┬────────────────────────────────────┘
                     │
┌────────────────────▼────────────────────────────────────┐
│  2. Check LangGraph State                                │
│     - aget_state(config) to check if interrupted        │
│     - thread_id = user_id for conversation isolation    │
└────────────────────┬────────────────────────────────────┘
                     │
         ┌───────────┴──────────┐
         │                      │
         ▼                      ▼
┌────────────────────┐  ┌───────────────────┐
│  If Interrupted:   │  │  If New/Complete: │
│  Resume with       │  │  Invoke with      │
│  Command(resume=)  │  │  initial state    │
└────────┬───────────┘  └──────────┬────────┘
         │                         │
         └───────────┬─────────────┘
                     │
┌────────────────────▼────────────────────────────────────┐
│  3. LangGraph Auto-Resume                                │
│     - Loads checkpoint for thread_id automatically      │
│     - Skips already-executed nodes                      │
│     - NO manual entry point selection needed            │
└────────────────────┬────────────────────────────────────┘
                     │
┌────────────────────▼────────────────────────────────────┐
│  4. ALWAYS → Understand Node (NLU)                       │
│     - Every message processed through NLU first         │
│     - Context includes: waiting_for_slot, flow desc     │
│     - NLU determines: slot, digression, intent change   │
└────────────────────┬────────────────────────────────────┘
                     │
┌────────────────────▼────────────────────────────────────┐
│  5. Conditional Routing (based on NLU result)            │
│     - Slot Value → Validate Node                        │
│     - Digression → Digression Node → Back to Understand │
│     - Intent Change → Flow Stack Node                   │
└────────────────────┬────────────────────────────────────┘
                     │
┌────────────────────▼────────────────────────────────────┐
│  6. Execute Appropriate Node                             │
│     - Validation, action, digression, etc.              │
│     - If need user input → interrupt() → PAUSE          │
│     - LangGraph auto-saves checkpoint after each node   │
└────────────────────┬────────────────────────────────────┘
                     │
┌────────────────────▼────────────────────────────────────┐
│  7. Return Response to User                              │
│     - Extract from state.last_response                  │
│     - [User responds → Loop back to step 1]             │
└─────────────────────────────────────────────────────────┘
```

### Key LangGraph Patterns

1. **Automatic Checkpointing**: LangGraph saves state after each node (no manual save needed)
2. **Auto-Resume**: Same `thread_id` → automatically loads last checkpoint
3. **interrupt()**: Pauses execution to wait for user input
4. **Command(resume=)**: Continues execution with user's response
5. **Conditional Edges**: Route based on NLU result type

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

    This routing logic determines whether to call NLU or queue the message.
    """

    # ===== Case 1: Executing action =====
    if state.conversation_state == ConversationState.EXECUTING_ACTION:
        # User shouldn't send messages during action execution
        # But if they do, queue it for after action completes
        return MessageRoute(
            type="queue",
            reason="action_in_progress",
        )

    # ===== Case 2: All other states - use NLU with context =====
    else:
        # Build enriched context for NLU
        context = self._build_nlu_context(state)

        return MessageRoute(
            type="nlu_understanding",
            context=context,
            reason=f"process_in_state_{state.conversation_state}",
        )
```

**Simplified Approach**: Instead of complex routing logic, we always call NLU (except when action is executing). The NLU receives rich context that helps it understand:
- What slot we're waiting for (if any)
- Current conversation state
- Available flows with descriptions
- Paused flows that can be resumed
- Conversation history

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
        "nlu_understanding",  # Call NLU with enriched context
        "queue",              # Queue message for later
    ]

    context: NLUContext | None = None
    """Enriched context for NLU if type == 'nlu_understanding'"""

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

## NLU-Based Message Understanding

### Unified NLU Approach

All messages are processed through the NLU with enriched context:

```python
async def _process_with_nlu(
    self,
    user_msg: str,
    state: DialogueState,
) -> DialogueState:
    """
    Process message using NLU with enriched context.

    The NLU handles all understanding tasks:
    - Slot value extraction: "New York"
    - Intent detection/changes: "Actually, I want to cancel"
    - Digression detection: "What cities do you support?"
    - Resume requests: "Go back to booking"

    Steps:
    1. Build enriched NLU context
    2. Call NLU with context
    3. Handle result based on type
    """

    # 1. Build enriched context
    context = NLUContext(
        conversation_state=state.conversation_state,
        waiting_for_slot=state.waiting_for_slot,
        current_flow=state.current_flow,
        available_flows=self._get_flow_descriptions(),
        paused_flows=self._get_paused_flows(state),
        conversation_history=state.messages[-5:],  # Last 5 messages
    )

    # 2. Call NLU
    try:
        result = await self.nlu.predict(
            user_message=user_msg,
            context=context,
        )

        # 3. Handle result based on type
        if result.is_slot_value:
            # Extract and validate slot
            slot_name = state.waiting_for_slot or result.slot_name
            raw_value = result.slot_value
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

        elif result.is_digression:
            # Handle digression without changing flow stack
            return await self._handle_digression(result, state)

        elif result.is_intent_change:
            # Push new flow or pop current
            return await self._handle_intent_change(result, state)

        elif result.is_resume_request:
            # Pop to requested flow
            return await self._handle_resume(result, state)

        else:
            # Continue current flow
            return state

    except Exception as e:
        # Log error and handle gracefully
        logger.error(f"NLU processing failed: {e}")
        return self._create_error_state(state, str(e))
```

---

## Message Router Implementation

### Complete RuntimeLoop.process_message() (LangGraph Pattern)

```python
from langgraph.types import Command

class RuntimeLoop:
    async def process_message(
        self,
        user_msg: str,
        user_id: str,
    ) -> str:
        """
        Process user message with LangGraph checkpointing.

        This is the main entry point for message processing.

        Key LangGraph patterns:
        - Automatic checkpoint save/load via thread_id
        - interrupt() to pause for user input
        - Command(resume=) to continue after interrupt
        """

        # 1. Validate and sanitize
        sanitized_msg, sanitized_user_id = self._validate_inputs(user_msg, user_id)

        # 2. Config for LangGraph (thread_id enables auto-resume)
        config = {"configurable": {"thread_id": sanitized_user_id}}

        # 3. Check if we're in the middle of an interrupted flow
        current_state = await self.graph.aget_state(config)

        logger.info(
            f"Processing message",
            extra={
                "user_id": sanitized_user_id,
                "has_checkpoint": current_state is not None,
                "is_interrupted": current_state.next if current_state else None,
            }
        )

        # 4. Execute graph based on state
        if current_state and current_state.next:
            # We're interrupted - resume with user message
            # The message goes through understand_node first (graph structure)
            result = await self.graph.ainvoke(
                Command(resume={"user_message": sanitized_msg}),
                config=config
            )
        else:
            # New conversation or flow just completed
            input_state = {
                "user_message": sanitized_msg,
                "messages": [],
                "slots": {},
                "flow_stack": [],
                "conversation_state": ConversationState.IDLE,
            }
            result = await self.graph.ainvoke(input_state, config=config)

        # 5. Return response (checkpoint saved automatically by LangGraph)
        return result["last_response"]
```

### Key Differences from Old Design

| Aspect | OLD (Incorrect) | NEW (LangGraph Pattern) |
|--------|-----------------|-------------------------|
| Entry point | Manual `current_step or START` | Automatic via checkpoint |
| Checkpoint save | Manual `await self._save_state()` | Automatic after each node |
| Resume | `await self._execute_graph_from(state, entry_point)` | `Command(resume=)` |
| Pause | Check `conversation_state` | `interrupt()` in node |
| NLU processing | Separate from graph | ALWAYS first node in graph |

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

### 3. Context Building for NLU

```python
def _build_nlu_context(self, state: DialogueState) -> NLUContext:
    """
    Build enriched context for NLU.

    Includes:
    - Conversation state and current position
    - Flow descriptions and metadata
    - Paused flows that can be resumed
    - Recent conversation history
    """

    return NLUContext(
        # Current state
        conversation_state=state.conversation_state,
        waiting_for_slot=state.waiting_for_slot,
        current_flow=state.current_flow,
        current_step=state.current_step,

        # Available flows with descriptions
        available_flows=[
            FlowInfo(
                name=name,
                description=config.description,
                category=config.metadata.get("category"),
                keywords=config.trigger.get("keywords", [])
            )
            for name, config in self.config.flows.items()
        ],

        # Paused flows
        paused_flows=self._get_paused_flows(state),

        # Recent history
        conversation_history=state.messages[-5:],

        # Collected slots
        collected_slots=state.slots,
    )
```

---

## Performance Considerations

### Performance Profile

**Scenario: Simple Slot Collection (4 turns)**
```
Unified NLU Approach:
  Turn 1: NLU with context (300ms) + collect (10ms) = 310ms
  Turn 2: NLU with context (300ms) + collect (10ms) = 310ms
  Turn 3: NLU with context (300ms) + collect (10ms) = 310ms
  Turn 4: NLU with context (300ms) + action (100ms) = 400ms
  TOTAL: 1330ms, ~2000 tokens

Characteristics:
  - Consistent latency per turn
  - Predictable behavior
  - High accuracy (full NLU on all turns)
  - Simpler architecture
```

**Scenario: Intent Change Mid-Flow**
```
Turn 1: Collect slot → User: "New York" → NLU extracts slot (300ms)
Turn 2: Collect slot → User: "Actually, cancel" → NLU detects intent change (300ms)
Turn 3: Process cancellation → NLU handles new intent (300ms)

Benefits:
  - Consistent handling of all message types
  - No complexity of fallback logic
  - Single code path to optimize
```

### Optimization Opportunities

Future optimizations can be explored:
1. **Caching**: Cache NLU results for identical messages
2. **Batch processing**: Process multiple messages in parallel
3. **Model selection**: Use faster models for simpler scenarios
4. **Prompt optimization**: Use DSPy to optimize NLU prompts
5. **Streaming**: Stream NLU responses for better perceived latency

---

## Summary

This message processing design provides:

1. ✅ **Unified NLU approach** - Every message through understand_node FIRST
2. ✅ **Context-enriched prompts** that include waiting_for_slot, flow descriptions, paused flows
3. ✅ **LangGraph checkpointing** - Automatic save/load via thread_id
4. ✅ **interrupt() and Command(resume=)** for pausing/resuming
5. ✅ **Conditional routing** based on NLU result type
6. ✅ **Consistent behavior** across all message types (slot, digression, intent change)

**Critical Pattern**: Every user message passes through the Understand Node (NLU) first, even when waiting for a slot value. The user might say "New York" (slot) or "What cities?" (digression) or "Cancel" (intent change) - NLU with context determines which.

**LangGraph Integration**:
- `interrupt()` - Pause execution waiting for user
- `Command(resume=)` - Continue with user's response
- Checkpointing - Automatic after each node
- Auto-resume - Same thread_id loads last checkpoint

---

**Ground Truth**: See [01-architecture-overview.md](01-architecture-overview.md) for the definitive architecture.
**Next**: Read [04-graph-execution-model.md](04-graph-execution-model.md) for LangGraph integration details.
