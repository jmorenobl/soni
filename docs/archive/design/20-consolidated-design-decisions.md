# Consolidated Design Decisions

**Document Version**: 1.1
**Last Updated**: 2025-12-02
**Status**: Final Reference (Updated)

> **Ground Truth**: See [01-architecture-overview.md](01-architecture-overview.md) for the definitive architecture.

## Purpose

This document consolidates the **final design decisions** for the Soni Framework redesign, resolving contradictions and evolution across the design documentation (docs 00-19).

---

## Critical Decisions

### 1. Message Understanding Strategy

**Evolution**:
- **Initial** (docs 00-03): Proposed simple "direct slot mapping" with regex-based value detection
- **Revision 1** (doc 18): Introduced 3-tier hybrid (pattern extraction, lightweight NLU, full NLU)
- **Revision 2** (doc 19): Two-level DSPy-based approach
- **Final**: **Unified context-aware NLU approach**

**Final Decision**: Use single NLU with enriched context for all understanding tasks

**Rationale**:
- Simpler architecture with single optimization point
- Context-enriched prompts provide all necessary information
- Consistent behavior across all message types
- Easier to maintain and debug
- DSPy can optimize the single NLU module

**Implementation**:
- **Single NLU Provider** (DSPy module) handles:
  - Slot value extraction
  - Intent detection and changes
  - Digression detection (questions, clarifications, corrections)
  - Resume request identification
- **Enriched Context** includes:
  - Conversation state and position
  - Flow descriptions and metadata
  - Paused flows
  - Recent conversation history

**Impact**: Simplified architecture, consistent behavior, single code path to optimize

**Reference**: See `01-architecture-overview.md` and `03-message-processing.md` for complete design

---

### 2. State Machine Implementation

**Question**: Should we use `pytransitions/transitions` library?

**Decision**: **NO** - Use custom validation

**Rationale**:
- LangGraph already manages state as dict
- `transitions` library assumes control of state object (incompatible with LangGraph)
- Custom validation provides core benefit (transition validation) without complexity
- No external dependency, easier to maintain

**Implementation**:
```python
class StateTransitionValidator:
    VALID_TRANSITIONS: dict[ConversationState, list[ConversationState]] = {...}

    @classmethod
    def validate_transition(cls, from_state, to_state) -> None:
        # Raises ValueError if invalid
```

**Reference**: See `17-state-validation-approach.md` for details

---

### 3. "start_" Prefix in Action Names

**Question**: Should flow names have "start_" prefix when no active flow?

**Decision**: **REMOVE** the prefix entirely

**Rationale**:
- Creates mismatch preventing flow activation (`"start_book_flight"` vs `config.flows["book_flight"]`)
- Adds unnecessary complexity
- Inconsistent with industry standards (Rasa, DialogFlow, Lex)
- No real benefit

**Impact**:
- Fixes critical bug where `current_flow` never activates
- Simpler code, consistent naming
- Aligns with industry standards

**Reference**: See `16-start-prefix-investigation.md` for analysis

---

### 4. Context-Aware Message Routing

**Decision**: Implement router that decides whether to use NLU based on conversation state

**Final Approach**:
```
Message received → Context Router:
  - If EXECUTING_ACTION → Queue message
  - Else → NLU with enriched context (handles all understanding)
```

**Impact**: Simplified routing logic, consistent behavior

**Reference**: See `03-message-processing.md` for details

---

### 5. Resumable Graph Execution with LangGraph

**Decision**: Use LangGraph's native checkpointing for automatic resumption

**Implementation** (CORRECT PATTERN):
```python
from langgraph.types import Command, interrupt

async def process_message(msg: str, user_id: str) -> str:
    config = {"configurable": {"thread_id": user_id}}

    # Check if interrupted
    current_state = await graph.aget_state(config)

    if current_state and current_state.next:
        # Resume with user response
        result = await graph.ainvoke(
            Command(resume={"user_message": msg}),
            config=config
        )
    else:
        # New conversation
        result = await graph.ainvoke(initial_state, config=config)

    return result["last_response"]
```

**Key Points**:
- ✅ NO manual entry point selection needed
- ✅ Use `interrupt()` to pause execution waiting for user
- ✅ Use `Command(resume=)` to continue after interrupt
- ✅ LangGraph auto-loads checkpoint via `thread_id`

**Impact**: Simplified code, correct LangGraph integration

**Reference**: See `01-architecture-overview.md` for ground truth

---

### 6. Explicit State Machine

**Decision**: Add explicit state tracking fields to DialogueState

**New Fields**:
- `conversation_state: ConversationState` - What are we doing? (IDLE, WAITING_FOR_SLOT, etc.)
- `current_step: str | None` - Where are we in the flow?
- `waiting_for_slot: str | None` - Which slot are we expecting?
- `last_nlu_call: float | None` - When was last NLU call?

**Impact**: Enables all other optimizations (routing, resumption, caching)

**Reference**: See `02-state-machine.md` for complete schema

---

## Design Principles (Final)

### 1. Simplicity and Correctness

**Principle**: Prefer simple, correct solutions over premature optimization

**Application**:
- Use unified NLU approach → Simpler architecture
- Enrich context with conversation state → Better understanding
- Single code path → Easier to maintain and optimize
- DSPy optimization → Systematic prompt improvement

### 2. Realistic Human Communication

**Principle**: Design for how humans actually communicate, not ideal cases

**Application**:
- Users don't always give direct answers
- Users change their mind mid-flow
- Users ask questions and seek clarifications
- System must handle all these gracefully

### 3. Context-Aware Understanding

**Principle**: Provide rich context to enable accurate understanding

**Application**:
- Include conversation state in NLU prompts
- Provide flow descriptions and metadata
- Include paused flows and conversation history
- Single NLU module with comprehensive context

### 4. LangGraph-First

**Principle**: Work WITH LangGraph's architecture, not against it

**Application**:
- State is dict (LangGraph's format)
- Nodes return update dicts
- Checkpointing is LangGraph's responsibility
- Don't try to wrap state with external libraries

---

## Superseded Ideas

### ❌ Direct Slot Mapping (Simple Regex)

**Proposed in**: Documents 00, 01, 03
**Superseded by**: Unified NLU approach

**Why superseded**:
- Too simplistic for realistic user behavior
- Can't distinguish "Boston" from "Actually, cancel"
- Can't handle questions, corrections, or clarifications

**Status**: **Don't implement** - Use unified NLU approach

---

### ❌ 3-Tier Hybrid (Pattern + Lightweight + Full NLU)

**Proposed in**: Document 18
**Superseded by**: Unified NLU approach

**Why superseded**:
- Added unnecessary complexity
- Multiple code paths to maintain
- Pattern extraction fundamentally flawed

**Status**: **Don't implement** - Use unified NLU approach

---

### ❌ Two-Level Collector (Lightweight + Full NLU)

**Proposed in**: Document 19
**Superseded by**: Unified NLU approach

**Why superseded**:
- Simpler to have single NLU module
- Context-enriched prompts achieve same goals
- Easier to maintain and optimize
- No fallback logic needed

**Status**: **Don't implement** - Use unified NLU approach

---

### ❌ Using `transitions` Library

**Discussed in**: Document 17
**Decision**: Don't use

**Why rejected**:
- Incompatible with LangGraph's state management
- Adds complexity without proportional benefit
- Custom validation is simpler and sufficient

**Status**: **Don't implement** - Use custom `StateTransitionValidator`

---

## Implementation Phases (Revised)

### Phase 1: State Machine Foundation (2 weeks)
- ✅ **Use full NLU always** (correctness first)
- Add `conversation_state`, `current_step`, `waiting_for_slot` to DialogueState
- Implement state transition validation (custom, no `transitions` library)
- Remove "start_" prefix from action names

### Phase 2: Context-Aware Routing (3 weeks)
- ✅ **Still use full NLU** (optimization comes later)
- Implement message router (decides when to call NLU)
- Track execution context
- Add routing metrics

### Phase 3: Resumable Execution (2 weeks)
- Implement entry point selection
- Enable resuming from `current_step`
- Update graph building for enhanced routing

### Phase 4: NLU Optimization (2 weeks)
- Optimize NLU prompts with DSPy
- Fine-tune context building
- Collect real conversation data
- Measure and improve accuracy

### Phase 5: NLU Caching & Polish (1.5 weeks)
- Implement NLU result caching
- Fine-tune confidence thresholds
- Comprehensive testing
- Documentation

**Total**: 10.5-12 weeks

---

## Testing Strategy

### Unit Tests
- State transition validation
- Message routing logic
- Context building for NLU
- Normalization and validation

### Integration Tests
- RuntimeLoop with context-aware NLU
- Graph execution with resumption
- Flow stack management
- State recovery from checkpoints

### E2E Tests
- Simple slot collection flow
- Intent change mid-flow
- User asks questions (digressions)
- User corrects previous values
- Flow interruption and resumption
- Multiple nested flows

### Performance Benchmarks
- NLU accuracy (intent, slots, digressions)
- Latency per turn (target: consistent ~300ms)
- Token usage (measure baseline)
- Context-building overhead (target: <10ms)

---

## Migration from Old Design

### Breaking Changes

1. **DialogueState schema** - Added new fields
   - Migration: Backward-compatible state loading
   - Old checkpoints will work, new fields initialize to defaults

2. **Action names** - "start_" prefix removed
   - Migration: Update tests, clear NLU cache
   - Re-optimize DSPy modules if already optimized

3. **Message processing** - Unified NLU with context
   - Migration: Update NLU module to accept enriched context
   - No A/B test needed (simplified architecture)

### Backward Compatibility

**Must maintain**:
- YAML configuration format
- Action registry API
- Validator registry API
- External action implementations

**Can break**:
- Internal node implementations
- State schema (with migration)
- Graph structure

---

## Key Metrics to Monitor

### Performance Metrics
- **NLU latency per turn** (baseline: ~300ms)
- **Context building overhead** (target: <10ms)
- **Token usage per conversation** (baseline for optimization)
- **Cache hit rate** (target: 30%+)

### Quality Metrics
- **Intent detection accuracy** (target: >90%)
- **Slot extraction F1** (target: >85%)
- **Digression detection accuracy** (target: >80%)
- **Flow resumption accuracy** (target: >90%)
- **User satisfaction** (if measurable)

### Operational Metrics
- **Error rate** (target: <1%)
- **State transition errors** (target: 0)
- **Checkpoint recovery success** (target: 100%)

---

## Documentation Structure (Updated)

### Core Architecture (Stable)
- **01-architecture-overview.md** - High-level design (UPDATED with final decisions)
- **02-state-machine.md** - State schema and transitions
- **03-message-processing.md** - Message routing (UPDATED with final slot collection)
- **04-graph-execution-model.md** - LangGraph integration

### Implementation Guide (Stable)
- **14-implementation-roadmap.md** - Phased plan (UPDATED with Phase 4)

### Problem Analysis (Reference)
- **15-current-problems-analysis.md** - Original problems found
- **16-start-prefix-investigation.md** - Analysis and decision (REMOVE prefix)
- **17-state-validation-approach.md** - Analysis and decision (NO transitions library)

### Design Evolution (Historical)
- **18-hybrid-slot-collection-strategy.md** - ⚠️ **SUPERSEDED** by doc 19
- **19-realistic-slot-collection-strategy.md** - ✅ **FINAL** slot collection design

### This Document
- **20-consolidated-design-decisions.md** - Single source of truth for final decisions

---

## Quick Decision Lookup

Need a quick answer? Here's the executive summary:

| Question | Answer | Reference |
|----------|--------|-----------|
| How to process messages? | Use unified NLU with enriched context | Doc 01, 03 |
| Use transitions library? | No, custom validation | Doc 02 |
| Remove "start_" prefix? | Yes, remove it | Doc 01 |
| When to call NLU? | Always (except during action execution) | Doc 03 |
| Resume graph from current step? | Yes, use resumable execution | Doc 04 |
| How to track conversation state? | Add explicit fields: conversation_state, current_step, waiting_for_slot | Doc 02 |
| How to handle digressions? | NLU detects digressions, system handles without changing flow stack | Doc 05 |
| Flow interruption? | Push new flow to stack, pause current | Doc 05 |
| How to pause/resume execution? | Use `interrupt()` to pause, `Command(resume=)` to continue | Doc 01 |
| Manual entry point selection? | NO - LangGraph handles automatically via checkpointing | Doc 01 |

---

## Conclusion

This consolidated document represents the **final, simplified design** after thorough analysis and iteration. Key takeaways:

1. ✅ **Message processing**: Unified context-aware NLU (single module)
2. ✅ **State machine**: Custom validation (not transitions library)
3. ✅ **Action names**: No "start_" prefix
4. ✅ **Message routing**: Simple (NLU with context or queue)
5. ✅ **Graph execution**: Resumable from current step
6. ✅ **State tracking**: Explicit conversation_state fields
7. ✅ **Flow management**: Flow stack for complex conversations

**Status**: Ready for implementation starting with Phase 1 (State Machine Foundation)

**Next Actions**:
1. Review and approve this consolidated design
2. Begin Phase 1 implementation
3. Implement unified NLU with context enrichment
4. Add flow stack management for complex conversations

---

**Document Status**: Complete - Single Source of Truth for Final Design
**Maintained by**: Design team
**Last Review**: 2025-12-02
