# Quick Decision Index

**Need a quick answer?** Use this index to find the final decision for common questions.

---

## Slot Collection

**Q: How should I collect slot values from users?**

**A: Use two-level DSPy-based approach**
- Level 1: Lightweight DSPy collector (~150ms) - handles values, intent changes, questions
- Level 2: Full NLU (~300ms) - fallback when uncertain
- **Don't use**: Simple regex/pattern matching (too simplistic)
- **Reference**: [19-realistic-slot-collection-strategy.md](19-realistic-slot-collection-strategy.md)

---

## State Machine

**Q: Should I use the `transitions` library?**

**A: No, use custom validation**
- LangGraph already manages state as dict
- `transitions` incompatible with LangGraph's architecture
- Use lightweight `StateTransitionValidator` class instead
- **Reference**: [17-state-validation-approach.md](17-state-validation-approach.md)

---

## Action Names

**Q: Should flow names have "start_" prefix?**

**A: No, remove the prefix**
- Creates flow activation bug
- Adds unnecessary complexity
- Not industry standard
- **Reference**: [16-start-prefix-investigation.md](16-start-prefix-investigation.md)

---

## NLU Calls

**Q: Should NLU be called on every turn?**

**A: No, use context-aware routing**
- Call NLU when IDLE (need intent)
- Skip NLU when WAITING_FOR_SLOT (use lightweight collector)
- Expected reduction: 60-70% fewer NLU calls
- **Reference**: [03-message-processing.md](03-message-processing.md)

---

## Graph Execution

**Q: Should graph always start from START?**

**A: No, resume from current_step**
- Resume from `current_step` when WAITING_FOR_SLOT
- Start from START when IDLE or new flow
- Expected improvement: 88% faster graph execution
- **Reference**: [04-graph-execution-model.md](04-graph-execution-model.md)

---

## State Tracking

**Q: What fields should DialogueState have?**

**A: Add explicit state tracking fields**
- `conversation_state`: What are we doing? (IDLE, WAITING_FOR_SLOT, etc.)
- `current_step`: Where in the flow?
- `waiting_for_slot`: Which slot expected?
- `last_nlu_call`: When was last NLU call?
- **Reference**: [02-state-machine.md](02-state-machine.md)

---

## Direct Slot Mapping

**Q: Can I use simple regex to extract slot values?**

**A: No, it's too simplistic**
- Can't distinguish "Boston" from "Actually, cancel"
- Can't handle questions, corrections, clarifications
- Use DSPy-based lightweight collector instead
- **Reference**: [19-realistic-slot-collection-strategy.md](19-realistic-slot-collection-strategy.md), section "Problem with Previous Approach"

---

## Pattern Extraction

**Q: Should I implement 3-tier pattern extraction?**

**A: No, document 18 is superseded**
- Tier 1 (pattern extraction) fundamentally flawed
- Use 2-level DSPy approach instead (doc 19)
- **Reference**: [19-realistic-slot-collection-strategy.md](19-realistic-slot-collection-strategy.md)

---

## Caching

**Q: Should I cache NLU results?**

**A: Yes, implement two-level caching**
- Turn-level cache: Same message within turn
- Session-level cache: Same message in same context
- Expected hit rate: 30%+
- **Reference**: [03-message-processing.md](03-message-processing.md), section "NLU Result Caching"

---

## Message History

**Q: Should I keep full message history?**

**A: No, prune to recent N messages**
- Keep last 10 messages (configurable)
- Prevents token explosion
- Can implement sliding window or summarization
- **Reference**: [03-message-processing.md](03-message-processing.md), section "Message History Pruning"

---

## Testing

**Q: What testing strategy should I follow?**

**A: Test pyramid with AAA pattern**
- Unit tests: Individual functions (100+ tests)
- Integration tests: Component interaction (30 tests)
- E2E tests: Complete flows (10 tests)
- All tests use AAA pattern (Arrange-Act-Assert)
- **Reference**: [14-implementation-roadmap.md](14-implementation-roadmap.md), section "Testing Strategy"

---

## Implementation Order

**Q: What order should I implement features?**

**A: Follow phased approach**
1. Phase 1 (2 weeks): State machine foundation
2. Phase 2 (3 weeks): Context-aware routing (use full NLU)
3. Phase 3 (2 weeks): Resumable execution
4. Phase 4 (2 weeks): Lightweight slot collector
5. Phase 5 (1.5 weeks): Caching & polish
- **Reference**: [14-implementation-roadmap.md](14-implementation-roadmap.md)

---

## Performance Targets

**Q: What performance should I expect?**

**A: Target metrics after full implementation**
- Latency per turn: ~120ms (down from ~350ms) = **66% faster**
- NLU calls per 4-turn flow: 1-2 (down from 4) = **60% reduction**
- Tokens per 4-turn flow: ~600 (down from ~2000) = **70% reduction**
- **Reference**: [14-implementation-roadmap.md](14-implementation-roadmap.md), section "Success Metrics"

---

## Error Handling

**Q: How should I handle errors in state transitions?**

**A: Validate transitions with StateTransitionValidator**
```python
StateTransitionValidator.validate_transition(
    from_state=current_state,
    to_state=new_state,
)  # Raises ValueError if invalid
```
- **Reference**: [17-state-validation-approach.md](17-state-validation-approach.md)

---

## DSPy Optimization

**Q: Should I optimize the lightweight collector?**

**A: Yes, optimize separately from full NLU**
- Use MIPROv2 or SIMBA
- Create training dataset with outcome examples
- Optimize for confidence calibration
- **Reference**: [19-realistic-slot-collection-strategy.md](19-realistic-slot-collection-strategy.md), section "Optimization with DSPy"

---

## Complete Reference

**For comprehensive explanation of all decisions, see:**
📋 **[20-consolidated-design-decisions.md](20-consolidated-design-decisions.md)** - Single source of truth

---

**Last Updated**: 2025-12-02
**Maintained by**: Design team
