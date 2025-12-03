# Implementation Roadmap

**Document Version**: 1.1
**Last Updated**: 2025-12-02
**Status**: Draft (Updated for LangGraph patterns)

> **Ground Truth**: See [01-architecture-overview.md](01-architecture-overview.md) for the definitive architecture.

## Executive Summary

This document provides a **phased implementation plan** for the Soni Framework redesign. The implementation is divided into 5 phases, each deliverable independently with incremental value.

**Total Estimated Effort**: 10-12 weeks (1 developer)
**Risk Level**: Medium (architectural changes require careful testing)

---

## Implementation Phases

### Phase 1: State Machine Foundation (2 weeks)

**Goal**: Implement explicit conversation state tracking.

**Tasks**:
1. Update `DialogueState` schema with new fields
   - Add `conversation_state` enum
   - Add `current_step` field
   - Add `waiting_for_slot` field
   - Add `last_nlu_call` timestamp

2. Create `ConversationState` enum
   - Define all states (IDLE, UNDERSTANDING, WAITING_FOR_SLOT, etc.)
   - Add state validation logic

3. Update state persistence
   - Modify checkpointing to save new fields
   - Add migration for existing conversations
   - Add state validation on load

4. Add state transition tracking
   - Log all state transitions
   - Add trace events for state changes
   - Create state transition validators

**Deliverable**: State management with explicit conversation states
**Success Metrics**:
- All tests pass with new state schema
- Backward compatibility maintained (old checkpoints can load)
- State transitions logged correctly

---

### Phase 2: Context-Aware Message Routing (3 weeks)

**Goal**: Implement smart message routing that skips unnecessary NLU calls.

**Tasks**:
1. Implement message router
   - Create `route_message()` function
   - Implement intent detection heuristics
   - Implement simple value detection

2. Implement context-enriched NLU
   - Build NLU context with conversation state, flow descriptions, paused flows
   - Add normalization pipeline for extracted values
   - Add validation for extracted values

3. Add routing decision logic
   - Route to NLU with enriched context for all states (except EXECUTING_ACTION)
   - Queue messages during action execution

4. Update RuntimeLoop
   - Integrate router into `process_message()`
   - Add logging for routing decisions
   - Add metrics collection

**Deliverable**: Context-aware NLU with enriched prompts
**Success Metrics**:
- High accuracy for intent detection, slot extraction, digression detection
- Consistent behavior across all message types
- All e2e tests pass
- No regression in intent detection accuracy

---

### Phase 3: LangGraph Integration (2 weeks)

**Goal**: Leverage LangGraph's native checkpointing and interrupt/resume capabilities.

**Tasks**:
1. Update graph patterns to use LangGraph correctly
   - Use `interrupt()` to pause execution for user input
   - Use `Command(resume=)` to continue after interrupt
   - Remove manual entry point selection (LangGraph handles automatically)
   - Ensure EVERY message goes through understand_node first

2. Update RuntimeLoop for checkpointing
   - Use `aget_state()` to check if interrupted
   - Use `thread_id` for conversation isolation
   - Remove manual `current_step` tracking for resumption
   - Keep `current_step` for debugging/tracing only

3. Update node implementations
   - Use `interrupt()` in slot collection nodes
   - Return proper state updates as dicts
   - Let LangGraph handle automatic checkpoint saves
   - Add proper conditional routing based on NLU results

4. Test checkpoint recovery
   - Verify automatic resume from interrupted state
   - Test conversation persistence across sessions
   - Verify checkpoint cleanup on completion

**Deliverable**: Correct LangGraph integration with automatic checkpointing
**Success Metrics**:
- All conversations resume correctly after interruption
- No manual checkpoint management needed
- State correctly preserved across sessions
- `interrupt()` and `Command(resume=)` work as expected

---

### Phase 4: NLU Caching & Optimization (1.5 weeks)

**Goal**: Add NLU result caching to reduce redundant LLM calls.

**Tasks**:
1. Implement NLU cache
   - Create `NLUCache` class
   - Implement cache key generation
   - Add TTL-based expiration

2. Integrate cache into NLU provider
   - Update `SoniDU.predict()` to use cache
   - Add cache hit/miss logging
   - Add cache metrics

3. Implement message history pruning
   - Add history pruning logic
   - Configurable history window (default: 10 messages)
   - Preserve important messages (flow triggers, confirmations)

4. Add caching configuration
   - Add cache settings to config YAML
   - Make cache TTL configurable
   - Add cache clear endpoint for testing

**Deliverable**: NLU result caching with configurable TTL
**Success Metrics**:
- 30%+ cache hit rate in typical conversations
- 50%+ reduction in duplicate NLU calls
- No accuracy regression

---

### Phase 5: Testing, Documentation & Polish (1.5 weeks)

**Goal**: Comprehensive testing, documentation, and production readiness.

**Tasks**:
1. Write comprehensive tests
   - Unit tests for all new components
   - Integration tests for routing logic
   - E2E tests for complete flows
   - Performance benchmarks

2. Update documentation
   - Update README with new features
   - Add migration guide for existing users
   - Update API documentation
   - Add performance tuning guide

3. Add monitoring & observability
   - Add metrics for routing decisions
   - Add metrics for cache hit rates
   - Add metrics for node execution times
   - Create Grafana dashboard templates

4. Performance optimization
   - Profile critical paths
   - Optimize hot code paths
   - Add connection pooling for persistence
   - Add batch processing where applicable

**Deliverable**: Production-ready system with full test coverage
**Success Metrics**:
- 90%+ test coverage
- All e2e tests pass
- Performance benchmarks meet targets
- Documentation complete

---

## Phase Dependencies

```
Phase 1: State Machine Foundation
    ↓
Phase 2: Context-Aware Routing
    ↓
Phase 3: Resumable Execution
    ↓
Phase 4: NLU Caching
    ↓
Phase 5: Testing & Polish
```

**Critical Path**: All phases are sequential.
**Parallel Work**: Documentation can start in Phase 3.

---

## Success Metrics

### Performance Targets

| Metric | Current (OLD) | Target (NEW) | Measurement |
|--------|--------------|--------------|-------------|
| **Avg latency per turn** | 350ms | 120ms | 66% reduction |
| **NLU calls per 4-turn flow** | 4 | 1.5 | 62% reduction |
| **Tokens per 4-turn flow** | 2000 | 600 | 70% reduction |
| **Graph execution time** | 1500ms | 180ms | 88% reduction |
| **Cache hit rate** | 0% | 30%+ | New metric |

### Quality Targets

| Metric | Target | Measurement |
|--------|--------|-------------|
| **Test coverage** | 90%+ | pytest-cov |
| **E2E test pass rate** | 100% | CI/CD |
| **Intent detection accuracy** | No regression | Benchmark suite |
| **Slot extraction F1** | No regression | Benchmark suite |

---

## Risk Mitigation

### Risk 1: Breaking Changes

**Risk**: New state schema breaks existing conversations.

**Mitigation**:
- Implement backward-compatible state loading
- Add migration script for old checkpoints
- Test with sample of production data (if available)
- Feature flag for gradual rollout

### Risk 2: Performance Regression

**Risk**: New routing logic adds overhead.

**Mitigation**:
- Benchmark before and after each phase
- Profile critical paths
- Add performance tests to CI
- Optimize hot paths

### Risk 3: Accuracy Regression

**Risk**: Direct slot mapping reduces accuracy vs full NLU.

**Mitigation**:
- Keep hybrid fallback for ambiguous cases
- Measure intent detection accuracy
- Monitor NLU performance and optimize prompts with DSPy
- A/B test in production (if applicable)

### Risk 4: Implementation Complexity

**Risk**: Architectural changes introduce bugs.

**Mitigation**:
- Comprehensive test suite
- Incremental implementation with testing at each phase
- Code review for all changes
- Beta testing with select users

---

## Testing Strategy

### Test Pyramid

```
        ┌─────────────┐
        │   E2E Tests │  (10 tests)
        │   Full flows │
        └─────────────┘
       ┌───────────────┐
       │  Integration   │  (30 tests)
       │     Tests      │  Component interaction
       └───────────────┘
      ┌─────────────────┐
      │   Unit Tests     │  (100+ tests)
      │  Individual      │  Pure functions
      │  functions       │
      └─────────────────┘
```

### Test Coverage by Phase

**Phase 1**: Unit tests for state management
**Phase 2**: Unit + integration tests for routing
**Phase 3**: Integration tests for graph execution
**Phase 4**: Unit tests for caching
**Phase 5**: E2E tests for complete flows

---

## Rollout Strategy

### Option A: Big Bang (Not Recommended)

Deploy all changes at once after Phase 5.

**Pros**: Simpler deployment
**Cons**: High risk, harder to debug issues

### Option B: Phased Rollout (Recommended)

Deploy each phase independently with feature flags.

**Phase 1**: Deploy state schema changes (backward compatible)
**Phase 2**: Deploy routing with feature flag (default: OFF)
**Phase 3**: Deploy resumable execution with feature flag
**Phase 4**: Deploy caching with feature flag
**Phase 5**: Enable all features by default

**Pros**: Lower risk, easier debugging, gradual validation
**Cons**: More complex deployment process

---

## Timeline

```
Week 1-2:   Phase 1 - State Machine
Week 3-5:   Phase 2 - Context-Aware Routing
Week 6-7:   Phase 3 - Resumable Execution
Week 8-9:   Phase 4 - NLU Caching
Week 10-11: Phase 5 - Testing & Polish
Week 12:    Buffer for issues/refinement
```

**Total**: 10-12 weeks

---

## Task Breakdown (Detailed)

### Phase 1 Tasks (Detail)

1.1. **Update DialogueState schema** (2 days)
   - [ ] Add conversation_state field
   - [ ] Add current_step field
   - [ ] Add waiting_for_slot field
   - [ ] Add last_nlu_call field
   - [ ] Update to_dict() and from_dict()
   - [ ] Write unit tests

1.2. **Create ConversationState enum** (1 day)
   - [ ] Define all states
   - [ ] Add state descriptions
   - [ ] Write state transition validators

1.3. **Update state persistence** (3 days)
   - [ ] Update checkpointer to save new fields
   - [ ] Write migration script for old data
   - [ ] Test backward compatibility
   - [ ] Add state validation on load

1.4. **Add state transition tracking** (2 days)
   - [ ] Log all transitions
   - [ ] Add trace events
   - [ ] Add transition metrics

1.5. **Testing** (2 days)
   - [ ] Unit tests for state management
   - [ ] Integration tests for persistence
   - [ ] Migration tests

### Phase 2 Tasks (Detail)

2.1. **Implement message router** (4 days)
   - [ ] Create route_message() function
   - [ ] Implement intent detection
   - [ ] Implement simple value detection
   - [ ] Add logging and metrics

2.2. **Implement direct slot mapping** (3 days)
   - [ ] Create _direct_slot_mapping() function
   - [ ] Add normalization pipeline
   - [ ] Add validation
   - [ ] Handle edge cases

2.3. **Add routing decision logic** (2 days)
   - [ ] Implement _has_intent_markers()
   - [ ] Implement _is_simple_value()
   - [ ] Add hybrid fallback

2.4. **Update RuntimeLoop** (2 days)
   - [ ] Integrate router
   - [ ] Add logging
   - [ ] Add metrics collection

2.5. **Testing** (4 days)
   - [ ] Unit tests for router
   - [ ] Integration tests for context-enriched NLU
   - [ ] E2E tests for routing decisions
   - [ ] Performance benchmarks
   - [ ] Test all message types (slots, intents, digressions, resume)

### Phase 3 Tasks (Detail)

3.1. **Implement entry point selection** (2 days)
   - [ ] Create _determine_entry_point()
   - [ ] Add resume from current_step logic
   - [ ] Handle edge cases

3.2. **Update graph building** (3 days)
   - [ ] Create enhanced router
   - [ ] Update conditional edges
   - [ ] Add node lifecycle wrappers

3.3. **Implement incremental checkpointing** (2 days)
   - [ ] Save after each node
   - [ ] Implement state merging
   - [ ] Add recovery logic

3.4. **Update node execution** (2 days)
   - [ ] Track current_step
   - [ ] Update conversation_state
   - [ ] Add node skip logic

3.5. **Testing** (3 days)
   - [ ] Integration tests for resumption
   - [ ] E2E tests for multi-turn flows
   - [ ] Checkpoint recovery tests

---

## Success Criteria

The implementation is considered successful when:

1. ✅ All phases completed
2. ✅ All tests passing (90%+ coverage)
3. ✅ Performance targets met
4. ✅ No accuracy regression
5. ✅ Documentation complete
6. ✅ Production deployment successful

---

## Next Steps

1. **Review this roadmap** with stakeholders
2. **Approve timeline and resource allocation**
3. **Set up project tracking** (GitHub Projects, Jira, etc.)
4. **Begin Phase 1 implementation**

---

**Document Status**: Ready for review and approval
