# Consolidated Design Decisions

**Document Version**: 1.0
**Last Updated**: 2025-12-02
**Status**: Final Reference

## Purpose

This document consolidates the **final design decisions** for the Soni Framework redesign, resolving contradictions and evolution across the design documentation (docs 00-19).

---

## Critical Decisions

### 1. Slot Collection Strategy

**Evolution**:
- **Initial** (docs 00-03): Proposed simple "direct slot mapping" with regex-based value detection
- **Revision 1** (doc 18): Introduced 3-tier hybrid (pattern extraction, lightweight NLU, full NLU)
- **Final** (doc 19): **Two-level DSPy-based approach**

**Final Decision**: Use DSPy-based lightweight collector + full NLU fallback

**Rationale**:
- Simple regex cannot distinguish slot values from intent changes, questions, or corrections
- DSPy-based approach handles realistic human communication patterns
- Falls back to full NLU when uncertain
- Can be optimized separately with DSPy

**Implementation**:
- **Level 1**: `LightweightSlotCollector` (DSPy module) - Detects: slot values, intent changes, questions, clarifications, corrections
- **Level 2**: Existing full NLU - Used when Level 1 is ambiguous or low confidence

**Impact**: ~45% latency savings, ~55% token savings in typical cases

**Reference**: See `19-realistic-slot-collection-strategy.md` for complete design

---

### 2. State Machine Implementation

**Question**: Should we use `pytransitions/transitions` library?

**Decision**: **NO** - Use lightweight custom validation

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
  - If WAITING_FOR_SLOT → Lightweight slot collector
  - If IDLE → Full NLU (need intent)
  - If EXECUTING_ACTION → Queue message
  - Else → Full NLU
```

**Impact**: 60-70% reduction in unnecessary NLU calls

**Reference**: See `03-message-processing.md` for details

---

### 5. Resumable Graph Execution

**Decision**: Graph resumes from `current_step` instead of always starting from START

**Implementation**:
```python
def _determine_entry_point(state: DialogueState) -> str:
    if state.conversation_state == ConversationState.WAITING_FOR_SLOT:
        return state.current_step  # Resume from current position
    return START
```

**Impact**: 88% faster graph execution in typical flows

**Reference**: See `04-graph-execution-model.md` for details

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

### 1. Correctness Over Optimization

**Principle**: Get it working correctly first, optimize second

**Application**:
- Phase 1 (MVP): Use full NLU always → Correct behavior
- Phase 2: Add lightweight collector → Optimize common cases
- Phase 3: Fine-tune thresholds → Further optimization

### 2. Realistic Human Communication

**Principle**: Design for how humans actually communicate, not ideal cases

**Application**:
- Users don't always give direct answers
- Users change their mind mid-flow
- Users ask questions and seek clarifications
- System must handle all these gracefully

### 3. Fail-Safe Fallbacks

**Principle**: When uncertain, fall back to the comprehensive solution

**Application**:
- Lightweight collector uncertain? → Use full NLU
- Pattern matching ambiguous? → Use lightweight collector
- Always prioritize correctness over speed

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
**Superseded by**: Document 19 (Lightweight DSPy Collector)

**Why superseded**:
- Too simplistic for realistic user behavior
- Can't distinguish "Boston" from "Actually, cancel"
- Can't handle questions, corrections, or clarifications

**Status**: **Don't implement** - Use DSPy-based approach instead

---

### ❌ 3-Tier Hybrid (Pattern + Lightweight + Full NLU)

**Proposed in**: Document 18
**Superseded by**: Document 19 (2-Level DSPy)

**Why superseded**:
- Tier 1 (pattern extraction) fundamentally flawed
- Tier 2 redundant with improved Tier 1
- Complexity not justified

**Status**: **Don't implement** - Use 2-level DSPy approach

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

### Phase 4: Lightweight Slot Collector (2 weeks) ⭐ NEW
- Implement `LightweightSlotCollector` (DSPy module)
- Add fallback to full NLU
- Collect real conversation data
- Optimize with DSPy

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
- Lightweight collector (with DSPy examples)
- Normalization and validation

### Integration Tests
- RuntimeLoop with routing
- Graph execution with resumption
- Lightweight collector → Full NLU fallback
- State recovery from checkpoints

### E2E Tests
- Simple slot collection flow
- Intent change mid-flow
- User asks questions
- User corrects previous values
- Ambiguous messages

### Performance Benchmarks
- NLU call count (target: 1-2 per 4-turn flow, down from 4)
- Latency per turn (target: ~120ms, down from ~350ms)
- Token usage (target: ~600 per 4-turn flow, down from ~2000)
- Lightweight collector success rate (target: 70%+)

---

## Migration from Old Design

### Breaking Changes

1. **DialogueState schema** - Added new fields
   - Migration: Backward-compatible state loading
   - Old checkpoints will work, new fields initialize to defaults

2. **Action names** - "start_" prefix removed
   - Migration: Update tests, clear NLU cache
   - Re-optimize DSPy modules if already optimized

3. **Slot collection logic** - New lightweight collector
   - Migration: Feature flag, gradual rollout
   - Can run A/B test: old (always full NLU) vs new (lightweight + fallback)

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
- **NLU calls per conversation** (target: reduce by 60%)
- **Average latency per turn** (target: reduce by 66%)
- **Token usage per conversation** (target: reduce by 70%)
- **Lightweight collector success rate** (target: 70%+)
- **Cache hit rate** (target: 30%+)

### Quality Metrics
- **Intent detection accuracy** (target: no regression)
- **Slot extraction F1** (target: no regression)
- **Lightweight collector accuracy** (target: 85%+)
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
| How to collect slots? | Use DSPy lightweight collector + full NLU fallback | Doc 19 |
| Use transitions library? | No, custom validation | Doc 17 |
| Remove "start_" prefix? | Yes, remove it | Doc 16 |
| When to call NLU? | Based on conversation_state (context-aware routing) | Doc 03 |
| Resume graph from current step? | Yes, use resumable execution | Doc 04 |
| How to track conversation state? | Add explicit fields: conversation_state, current_step, waiting_for_slot | Doc 02 |
| Pattern extraction for slots? | No, too simplistic. Use DSPy lightweight instead | Doc 19 |
| Always call NLU on every turn? | No, skip when waiting for slot (use lightweight collector) | Doc 19 |

---

## Conclusion

This consolidated document represents the **final, evolved design** after thorough analysis and iteration. Key takeaways:

1. ✅ **Slot collection**: DSPy-based lightweight collector (not simple regex)
2. ✅ **State machine**: Custom validation (not transitions library)
3. ✅ **Action names**: No "start_" prefix
4. ✅ **Message routing**: Context-aware (skip NLU when possible)
5. ✅ **Graph execution**: Resumable from current step
6. ✅ **State tracking**: Explicit conversation_state fields

**Status**: Ready for implementation starting with Phase 1 (State Machine Foundation)

**Next Actions**:
1. Review and approve this consolidated design
2. Begin Phase 1 implementation
3. Update main architecture docs (01-04) with final decisions
4. Mark superseded docs (18) appropriately

---

**Document Status**: Complete - Single Source of Truth for Final Design
**Maintained by**: Design team
**Last Review**: 2025-12-02
