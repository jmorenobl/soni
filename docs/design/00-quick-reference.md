# Quick Reference Guide

**Document Version**: 1.0
**Last Updated**: 2025-12-02

## Overview

This document provides a **quick reference** for the Soni Framework redesign. For detailed information, see the individual design documents.

---

## Key Innovations Summary

### 1. Explicit State Machine
**What**: Track conversation state explicitly (IDLE, WAITING_FOR_SLOT, EXECUTING_ACTION, etc.)
**Why**: Enables context-aware message processing
**Impact**: 60-70% reduction in unnecessary NLU calls

### 2. Context-Aware Routing
**What**: Route messages based on conversation_state, not always through NLU
**Why**: Avoid expensive LLM calls when we know what we're waiting for
**Impact**: 72% faster, 75% fewer tokens in typical flows

### 3. Resumable Graph Execution
**What**: Resume execution from current_step instead of always starting from START
**Why**: Skip redundant node executions
**Impact**: 88% faster graph execution

### 4. Lightweight Slot Collection (FINAL)
**What**: Two-level strategy using DSPy for intelligent slot collection
**Why**: Balance speed with correct handling of realistic human communication
**Levels**:
- **Level 1** - Lightweight DSPy Module (~150ms, ~250 tokens): Extracts slot value OR detects digression (intent changes, questions, clarifications, corrections)
- **Level 2** - Full NLU (~300ms, ~500 tokens): Complete intent + multi-slot extraction when lightweight is uncertain
**Impact**:
- Simple cases: 50% faster (lightweight succeeds)
- Digressions: 50% faster + correct handling
- Ambiguous: 0% faster but correct (uses full NLU)
- Overall: ~45% latency savings, ~55% token savings

**Note**: This replaces earlier "direct slot mapping" approaches which were too simplistic for realistic user behavior. See `19-realistic-slot-collection-strategy.md` for details.

### 5. NLU Result Caching
**What**: Cache NLU results by message + context hash
**Why**: Avoid redundant NLU calls for similar messages
**Impact**: 30%+ cache hit rate expected

---

## State Machine Quick Guide

### Conversation States

```python
class ConversationState(Enum):
    IDLE = "idle"                    # No active flow
    UNDERSTANDING = "understanding"   # Calling NLU
    WAITING_FOR_SLOT = "waiting_for_slot"  # Expecting slot value
    VALIDATING_SLOT = "validating_slot"    # Validating slot
    EXECUTING_ACTION = "executing_action"  # Running action
    CONFIRMING = "confirming"         # Asking confirmation
    COMPLETED = "completed"           # Flow done
    ERROR = "error"                   # Error occurred
```

### Common Transitions

```
IDLE → UNDERSTANDING → WAITING_FOR_SLOT → VALIDATING_SLOT → EXECUTING_ACTION → COMPLETED
```

### State Fields (NEW)

```python
class DialogueState:
    # NEW fields
    conversation_state: ConversationState  # What are we doing?
    current_step: str | None               # Where are we in flow?
    waiting_for_slot: str | None           # Which slot expected?
    last_nlu_call: float | None            # When was last NLU call?

    # Original fields
    messages: list[dict[str, str]]
    slots: dict[str, Any]
    current_flow: str
    turn_count: int
    last_response: str
    trace: list[dict[str, Any]]
    metadata: dict[str, Any]
```

---

## Message Processing Quick Guide

### Routing Decision Tree

```
Message received
  ↓
conversation_state == WAITING_FOR_SLOT?
  YES → Is message a simple value?
    YES → Direct slot mapping (FAST)
    NO → Has intent markers?
      YES → Call NLU (intent change)
      NO → Hybrid (try direct, fallback NLU)
  NO → conversation_state == IDLE?
    YES → Call NLU (need intent)
    NO → conversation_state == EXECUTING_ACTION?
      YES → Queue message (action in progress)
      NO → Call NLU (default)
```

### Intent Markers

```python
INTENT_MARKERS = [
    "book", "cancel", "change", "modify", "help", "restart",
    "what", "how", "can you", "actually", "wait", "instead",
    "no", "not", "don't", "i want to", "switch to"
]
```

### Simple Value Detection

- Single word: "Boston" ✅
- Short phrase (2-4 words): "New York" ✅
- Date-like: "tomorrow", "next Friday" ✅
- Question: "What time?" ❌
- Command: "Cancel booking" ❌

---

## Graph Execution Quick Guide

### Entry Point Selection

```python
if conversation_state == IDLE:
    entry_point = START
elif conversation_state == WAITING_FOR_SLOT:
    entry_point = current_step  # Resume from collect node
elif conversation_state == UNDERSTANDING:
    entry_point = first_flow_step  # After NLU
else:
    entry_point = START  # Default
```

### Node Lifecycle

```
PRE-EXECUTION
  ↓
EXECUTION (node function runs)
  ↓
POST-EXECUTION (update state, checkpoint)
  ↓
ROUTING DECISION (next node or END)
```

### Enhanced Routing

```python
def enhanced_router(state):
    if state.conversation_state == WAITING_FOR_SLOT:
        return END  # Stop, wait for user
    if state.conversation_state == ERROR:
        return END  # Stop, handle error
    if last_event == EVENT_SLOT_COLLECTION:
        return END  # Interactive pause
    return "next"  # Continue
```

---

## Performance Quick Reference

### Expected Improvements

| Metric | OLD | NEW | Improvement |
|--------|-----|-----|-------------|
| Latency per turn | 350ms | 120ms | **66% faster** |
| NLU calls (4-turn flow) | 4 | 1.5 | **62% reduction** |
| Tokens (4-turn flow) | 2000 | 600 | **70% reduction** |
| Graph execution | 1500ms | 180ms | **88% faster** |

### When NLU is Skipped

- User provides simple value when waiting for slot
- Message doesn't contain intent markers
- Last NLU call was very recent (<5s)
- Cache hit for same message + context

### When NLU is Called

- conversation_state == IDLE (need intent)
- Intent markers detected in message
- User is correcting/changing request
- Cache miss or expired

---

## Implementation Phases Quick Reference

1. **Phase 1 (2 weeks)**: State Machine Foundation
   - Add conversation_state, current_step, waiting_for_slot to DialogueState

2. **Phase 2 (3 weeks)**: Context-Aware Routing
   - Implement route_message() with direct slot mapping

3. **Phase 3 (2 weeks)**: Resumable Execution
   - Implement entry point selection and enhanced routing

4. **Phase 4 (1.5 weeks)**: NLU Caching
   - Add NLU result cache with TTL

5. **Phase 5 (1.5 weeks)**: Testing & Polish
   - Comprehensive tests, documentation, monitoring

**Total**: 10-12 weeks

---

## Code Snippets

### Minimal Example: Context-Aware Processing

```python
async def process_message(self, msg: str, user_id: str) -> str:
    # Load state
    state = await self.load_state(user_id)
    state.messages.append({"role": "user", "content": msg})

    # Route message
    if state.conversation_state == ConversationState.WAITING_FOR_SLOT:
        if self._is_simple_value(msg):
            # Direct mapping: FAST PATH
            state.slots[state.waiting_for_slot] = msg
            state.waiting_for_slot = None
        else:
            # Intent change detected
            nlu_result = await self.nlu.predict(msg, ...)
            state.slots.update(nlu_result.slots)
    else:
        # Need NLU
        nlu_result = await self.nlu.predict(msg, ...)
        state.slots.update(nlu_result.slots)

    # Execute graph from appropriate entry point
    entry_point = self._determine_entry_point(state)
    result = await self.graph.ainvoke(state, entry_point=entry_point)

    # Save and return
    await self.save_state(user_id, result)
    return result.last_response
```

### Minimal Example: Enhanced Routing

```python
def enhanced_router(state: DialogueState) -> str:
    """Decide whether to continue or stop"""
    if state.conversation_state in [
        ConversationState.WAITING_FOR_SLOT,
        ConversationState.ERROR,
        ConversationState.COMPLETED,
    ]:
        return END  # Stop execution

    return "next"  # Continue to next node
```

---

## Testing Checklist

### Unit Tests
- [ ] State machine transitions
- [ ] Message routing logic
- [ ] Intent marker detection
- [ ] Simple value detection
- [ ] Direct slot mapping
- [ ] NLU cache

### Integration Tests
- [ ] RuntimeLoop with routing
- [ ] Graph execution with resumption
- [ ] Checkpointing with new state fields
- [ ] State recovery from checkpoints

### E2E Tests
- [ ] Complete booking flow (4 turns)
- [ ] Flow with intent change
- [ ] Flow with slot correction
- [ ] Flow with validation errors
- [ ] Multi-user conversations

### Performance Tests
- [ ] Latency benchmarks
- [ ] Token usage benchmarks
- [ ] Cache hit rate measurement
- [ ] Graph execution time

---

## Configuration Examples

### Enable Context-Aware Routing

```yaml
settings:
  features:
    context_aware_routing: true  # NEW
    direct_slot_mapping: true    # NEW
    nlu_caching: true             # NEW

  routing:
    simple_value_threshold: 4     # Max words for simple value
    intent_marker_sensitivity: medium  # low, medium, high

  caching:
    nlu_cache_ttl: 60             # seconds
    max_cache_size: 1000          # entries
```

### Debug Logging

```yaml
settings:
  logging:
    level: DEBUG
    log_routing_decisions: true   # NEW
    log_state_transitions: true   # NEW
    log_cache_hits: true           # NEW
```

---

## Troubleshooting

### Issue: NLU still called on every turn

**Check**:
1. Is `context_aware_routing` enabled in config?
2. Are messages simple values or contain intent markers?
3. Check logs for routing decisions

**Debug**:
```python
logger.info(f"Routing decision: {route.type}, reason: {route.reason}")
```

### Issue: Direct mapping not working

**Check**:
1. Is `conversation_state == WAITING_FOR_SLOT`?
2. Is `waiting_for_slot` set correctly?
3. Does message pass `_is_simple_value()` check?

**Debug**:
```python
logger.debug(f"Message: '{msg}', is_simple: {self._is_simple_value(msg)}")
```

### Issue: Cache not hitting

**Check**:
1. Is `nlu_caching` enabled?
2. Is cache TTL too short?
3. Is context changing between calls?

**Debug**:
```python
cache_key = self.nlu_cache.get_cache_key(msg, context)
logger.debug(f"Cache key: {cache_key}, hit: {cache_key in self.cache}")
```

---

## Documentation Map

### For Understanding
1. [Architecture Overview](01-architecture-overview.md) - High-level design
2. [State Machine](02-state-machine.md) - Conversation states
3. [Message Processing](03-message-processing.md) - Routing logic

### For Implementation
1. [Graph Execution Model](04-graph-execution-model.md) - LangGraph integration
2. [Implementation Roadmap](14-implementation-roadmap.md) - Phased plan

### For Reference
- This document (Quick Reference)
- Individual design docs for details

---

## Key Metrics to Monitor

### Performance Metrics
- Average latency per turn
- P95 latency per turn
- NLU calls per conversation
- Tokens used per conversation
- Graph execution time

### Quality Metrics
- Intent detection accuracy
- Slot extraction F1 score
- Validation error rate
- Error recovery success rate

### Efficiency Metrics
- NLU cache hit rate
- Direct slot mapping success rate
- Node skip rate (resumable execution)
- Average message history length

---

## Contact & Support

For questions or clarifications on this design:
- Review detailed design documents (01-14)
- Check implementation roadmap (14)
- Refer to CLAUDE.md for coding conventions

---

**Document Status**: Complete
**Last Updated**: 2025-12-02
