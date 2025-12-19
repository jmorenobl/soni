# Roadmap: Critical Issues Resolution (P0 + P1)

**Status**: 🔴 URGENT - Production Blockers
**Total Effort**: 19 hours (~2.5 engineering days)
**Target Completion**: End of Week 51 (2025-12-20)
**Owner**: TBD

**Update 2025-12-18**: Command serialization verified as correct implementation, reducing P0 from 4 → 3 issues and total effort from 22h → 19h.

---

## Executive Summary

This roadmap addresses **7 critical issues** (3 P0 + 4 P1) that are blocking or critical for production deployment. These issues cause:
- Type safety violations
- Event loop blocking (10-100x performance degradation)
- Concurrency bugs
- Resource leaks

**P0 Issues** (Must fix before launch):
1. FlowDelta type export - 2h
2. Sync blocking call - 3h
3. Config mutation - 2h

**P1 Issues** (Must fix Week 1):
4. Async resource cleanup - 4h
5. Remove type ignores - 2h
6. Error handling - 3h
7. Health checks - 2h
8. **New: Serialization verification test - 1h**

**Note**: Command serialization (originally Issue P0 #4) was verified to be **correct implementation**. TypedDict + model_dump() is the recommended LangGraph pattern per [GitHub issue #5733](https://github.com/langchain-ai/langgraph/issues/5733). Added optional verification test instead.

**Risk if not fixed**: Production crashes, data corruption, poor user experience.

---

## Phase 1: P0 - Production Blockers (Day 1-2)

### Milestone 1.1: Type Safety Restoration (Day 1 Morning - 4h)

#### Task 1.1.1: Fix FlowDelta Type Export (2h)
**Priority**: 🔴 P0
**Files**: `src/soni/core/types.py`, `src/soni/flow/manager.py`

**Steps**:
1. Move `FlowDelta` dataclass from `flow/manager.py` to `core/types.py`
2. Update all Protocol return types:
   ```python
   # BEFORE
   def set_slot(...) -> Any | None:

   # AFTER
   def set_slot(...) -> FlowDelta | None:
   ```
3. Update imports in `flow/manager.py`: `from soni.core.types import FlowDelta`
4. Update `FlowStackProvider` and `FlowContextProvider` protocols

**Testing**:
- [ ] Run `mypy src/soni` - should pass without errors
- [ ] Verify IDE autocomplete works on FlowDelta fields
- [ ] Run unit tests: `pytest tests/unit/flow/test_manager.py -v`

**Success Criteria**:
- ✅ No `Any` type in Protocol return signatures
- ✅ Mypy passes with 100% type coverage
- ✅ All tests pass

---

#### Task 1.1.2: Remove Type Ignore Comments (2h)
**Priority**: 🔴 P0
**Files**: `src/soni/runtime/hydrator.py`, `src/soni/runtime/loop.py`

**Steps**:
1. Fix `runtime/hydrator.py:45`:
   ```python
   # BEFORE
   input_payload: DialogueState = {...}  # type: ignore[typeddict-item]

   # AFTER - Create through factory
   input_payload = create_dialogue_state_from_dict({...})
   ```

2. Fix `runtime/loop.py:73, 85`:
   ```python
   # Use proper Optional typing or refactor setter
   @flow_manager.setter
   def flow_manager(self, value: FlowManager) -> None:  # Remove | None
       if self._components:
           self._components = dataclasses.replace(
               self._components,
               flow_manager=value
           )
   ```

**Testing**:
- [ ] Search codebase: `rg "type: ignore"` - should return 0 results
- [ ] Run mypy: `mypy src/soni --strict`
- [ ] Run full test suite

**Success Criteria**:
- ✅ Zero `type: ignore` comments
- ✅ Strict mypy passes

---

### Milestone 1.2: Prevent Event Loop Blocking (Day 1 Afternoon - 6h)

#### Task 1.2.1: Fix Sync Blocking in reset_state (2h)
**Priority**: 🔴 P0 - **PRODUCTION KILLER**
**Files**: `src/soni/runtime/loop.py`

**Steps**:
1. Wrap synchronous `delete()` call:
   ```python
   # BEFORE (LINE 232-233)
   elif hasattr(checkpointer, "delete"):
       checkpointer.delete(config)  # ❌ BLOCKS EVENT LOOP

   # AFTER
   elif hasattr(checkpointer, "delete"):
       import asyncio
       await asyncio.to_thread(checkpointer.delete, config)  # ✅ Non-blocking
   ```

2. Add import at top of file: `import asyncio`

**Testing**:
- [ ] Unit test: Verify async execution with mock checkpointer
- [ ] Load test: 100 concurrent `reset_state()` calls
- [ ] Measure: Should complete in <1s (vs 10s+ before)

**Success Criteria**:
- ✅ No synchronous I/O calls in async functions
- ✅ Load test passes
- ✅ Event loop profiler shows no blocking

---

#### Task 1.2.2: Audit Entire Codebase for Sync Calls (4h)
**Priority**: 🔴 P0
**Files**: All `src/soni/**/*.py`

**Steps**:
1. Run audit command:
   ```bash
   rg 'async def' -A 20 src/soni | \
   rg '\s+((?!await)[a-z_]+)\.(close|delete|commit|execute|read|write)\(' \
   --context 2 > /tmp/sync_calls_audit.txt
   ```

2. Review each match and fix:
   - Database operations → `await asyncio.to_thread(...)`
   - File I/O → Use `aiofiles`
   - Network calls → Use async libraries

3. Document findings in `workflow/analysis/sync-calls-audit.md`

**Testing**:
- [ ] Run async profiler: `py-spy record --native --format speedscope -o profile.json -- python -m pytest`
- [ ] Check for blocking operations >10ms

**Success Criteria**:
- ✅ Audit document lists all sync calls
- ✅ All I/O operations are async or wrapped
- ✅ No blocking operations in profiler

---

### Milestone 1.3: Prevent Concurrency Bugs (Day 2 Morning - 2h)

#### Task 1.3.1: Fix Config Mutation in Compiler (2h)
**Priority**: 🔴 P0
**Files**: `src/soni/compiler/subgraph.py`

**Steps**:
1. Import deepcopy: `from copy import deepcopy`

2. Modify `_compile_while` method (line 110):
   ```python
   def _compile_while(
       self, step: WhileStepConfig, all_steps: list[StepConfig]
   ) -> tuple[StepConfig, dict[str, str]]:
       # Create mutable copy
       mutable_steps = [deepcopy(s) for s in all_steps]

       # ... rest of logic uses mutable_steps ...

       last_step = next(s for s in mutable_steps if s.step == last_step_name)
       if not last_step.jump_to:
           last_step.jump_to = guard_name  # ✅ Mutates copy

       return guard_step, {original_name: guard_name}
   ```

3. Update method signature if needed to return modified steps

**Testing**:
- [ ] Add test: compile same config twice, verify no mutation
- [ ] Add test: concurrent compilation of same config
- [ ] Run existing compiler tests: `pytest tests/unit/compiler/ -v`

**Success Criteria**:
- ✅ No mutations of input parameters
- ✅ Concurrent compilation test passes
- ✅ All existing tests pass

---

### Milestone 1.4: Command Serialization → ✅ Verified Correct

**Update**: This milestone was removed after verification showed the current implementation is **correct**.

Command serialization using TypedDict + `model_dump()` is the **recommended LangGraph pattern** per [GitHub issue #5733](https://github.com/langchain-ai/langgraph/issues/5733). No code changes needed.

Added optional verification test in Phase 2 instead.

---

## Phase 2: P1 - Critical (Day 2-3)

### Milestone 2.1: Resource Management (4h)

#### Task 2.1.1: Add Async Context Manager to RuntimeLoop (4h)
**Priority**: 🟠 P1
**Files**: `src/soni/runtime/loop.py`

**Steps**:
1. Implement `__aenter__` and `__aexit__`:
   ```python
   async def __aenter__(self) -> "RuntimeLoop":
       await self.initialize()
       return self

   async def __aexit__(self, exc_type, exc_val, exc_tb) -> None:
       await self.cleanup()
   ```

2. Make `cleanup()` async:
   ```python
   async def cleanup(self) -> None:
       if not self._components:
           return

       # Close checkpointer
       if checkpointer := self._components.checkpointer:
           if hasattr(checkpointer, "aclose"):
               await checkpointer.aclose()
           elif hasattr(checkpointer, "close"):
               await asyncio.to_thread(checkpointer.close)

       # Add cleanup for other resources
       # ...
   ```

3. Update server to use context manager:
   ```python
   @asynccontextmanager
   async def lifespan(app: FastAPI):
       async with RuntimeLoop(config) as runtime:
           app.state.runtime = runtime
           yield
   ```

**Testing**:
- [ ] Test cleanup is called on server shutdown
- [ ] Test resources are released (check file handles, connections)
- [ ] Test with exceptions during execution

**Success Criteria**:
- ✅ No resource leaks after 1000 requests
- ✅ Graceful shutdown works
- ✅ All cleanup methods called

---

### Milestone 2.2: Error Handling (3h)

#### Task 2.2.1: Add Comprehensive Error Handling (3h)
**Priority**: 🟠 P1
**Files**: `src/soni/server/routes.py`

**Steps**:
1. Create error handler middleware:
   ```python
   @app.exception_handler(Exception)
   async def global_exception_handler(request, exc):
       logger.error(f"Unhandled error: {exc}", exc_info=True)
       return JSONResponse(
           status_code=500,
           content={"error": "Internal server error", "type": type(exc).__name__}
       )
   ```

2. Add specific handlers for known errors:
   - `ActionError` → 400
   - `FlowError` → 422
   - `StateError` → 500

**Testing**:
- [ ] Test each error type returns correct status code
- [ ] Test error is logged with stack trace
- [ ] Test error response format

**Success Criteria**:
- ✅ All errors caught and logged
- ✅ Proper HTTP status codes
- ✅ Client-friendly error messages

---

### Milestone 2.3: Observability (2h)

#### Task 2.3.1: Add Health Checks (2h)
**Priority**: 🟠 P1
**Files**: New file `src/soni/server/health.py`

**Steps**:
1. Create health check endpoint:
   ```python
   @router.get("/health")
   async def health_check():
       return {
           "status": "healthy",
           "timestamp": datetime.now().isoformat(),
           "components": {
               "runtime": "initialized" if runtime._components else "not_ready",
               "checkpointer": "connected" if checkpointer else "none",
           }
       }
   ```

2. Add readiness probe:
   ```python
   @router.get("/ready")
   async def readiness_check():
       if not runtime._components:
           raise HTTPException(503, "Not ready")
       return {"ready": True}
   ```

**Testing**:
- [ ] Test health endpoint returns 200
- [ ] Test ready endpoint returns 503 before init
- [ ] Test Kubernetes probes work

**Success Criteria**:
- ✅ Health endpoint responds
- ✅ Ready probe accurate
- ✅ K8s integration works

---

### Milestone 2.4: Serialization Verification (1h) **NEW**

#### Task 2.4.1: Add State Serialization Round-Trip Test (1h)
**Priority**: 🟡 P1 (Nice-to-have)
**Files**: New file `tests/integration/test_state_serialization.py`

**Rationale**: While command serialization is correct, add explicit test to verify robustness.

**Steps**:
1. Create integration test:
   ```python
   @pytest.mark.asyncio
   async def test_state_serializes_correctly_through_checkpoint():
       """Verify all state fields survive checkpoint round-trip."""
       # Setup with MemorySaver
       checkpointer = MemorySaver()
       runtime = RuntimeLoop(config, checkpointer=checkpointer)

       # Process message and persist state
       response = await runtime.process_message("transfer 100 to Alice", "user_1")

       # Retrieve state from checkpoint
       state = await runtime.get_state("user_1")

       # Verify all fields survived serialization
       assert "flow_stack" in state  # List[FlowContext]
       assert "flow_slots" in state  # Dict[str, Dict[str, Any]]
       assert "messages" in state    # List[AnyMessage]
       assert "commands" in state    # List[dict] (serialized)

       # Verify enums survived (StrEnum → string → StrEnum)
       assert isinstance(state["flow_state"], str)
       assert state["flow_state"] in ["idle", "active", "waiting_input"]
   ```

2. Test with PostgreSQL checkpointer (if available)
3. Verify all TypedDict fields are JSON-serializable

**Testing**:
- [ ] Test with MemorySaver
- [ ] Test with SqliteSaver
- [ ] Test complex state with nested dicts

**Success Criteria**:
- ✅ All state fields survive round-trip
- ✅ No serialization errors
- ✅ Enums deserialize correctly

---

## Daily Breakdown

### Day 1 (7 hours)
**Focus**: Type Safety + Event Loop

- Morning (4h): Type Safety
  - ✅ Fix FlowDelta export (2h)
  - ✅ Remove type ignores (2h)

- Afternoon (3h): Event Loop
  - ✅ Fix blocking call (2h)
  - ✅ Targeted codebase audit (1h)

**Deliverables**:
- Zero `Any` types in Protocols
- Zero `type: ignore` comments
- No blocking calls in critical paths

---

### Day 2 (5 hours)
**Focus**: Concurrency + Production Readiness (Start)

- Morning (2h):
  - ✅ Fix config mutation (2h)

- Afternoon (3h):
  - ✅ Async context manager (3h, continue Day 3)

**Deliverables**:
- Immutable config compilation
- Progress on resource cleanup

---

### Day 3 (7 hours)
**Focus**: Production Readiness

- Morning (4h):
  - ✅ Complete async context manager (1h)
  - ✅ Error handling (3h)

- Afternoon (3h):
  - ✅ Health checks (2h)
  - ✅ Serialization verification test (1h)

**Deliverables**:
- Graceful shutdown
- Production monitoring
- Error tracking
- Serialization robustness verified

---

---

### Day 3 (6 hours)
**Focus**: Production Readiness

- Morning (4h):
  - ✅ Async context manager (4h)

- Afternoon (2h):
  - ✅ Error handling (1h)
  - ✅ Health checks (1h)

**Deliverables**:
- Graceful shutdown
- Production monitoring
- Error tracking

---

## Testing Strategy

### Per-Issue Testing
Each issue fix must include:
1. **Unit test** - Isolated component test
2. **Integration test** - End-to-end scenario
3. **Regression test** - Prevent reoccurrence

### Pre-Merge Checklist
Before merging each PR:
- [ ] All new tests pass
- [ ] No new mypy errors
- [ ] No new ruff violations
- [ ] Manual smoke test in dev environment
- [ ] Performance test (if applicable)
- [ ] Documentation updated

### Final Validation (Day 3 End)
- [ ] Full test suite: `pytest tests/ -v --cov`
- [ ] Type check: `mypy src/soni --strict`
- [ ] Lint: `ruff check src/soni`
- [ ] Load test: 1000 concurrent requests
- [ ] Memory leak test: 10k requests, check RSS
- [ ] Integration test suite passes

---

## Risk Mitigation

### High Risk Areas
1. **FlowDelta refactor** → May break existing code
   - Mitigation: Comprehensive test coverage first

2. **Async audit** → May find many issues
   - Mitigation: Prioritize user-facing paths

3. **Command serialization** → May affect state persistence
   - Mitigation: Test with real checkpointer

### Rollback Plan
Each change should be:
- In separate PR with clear scope
- Easily revertible
- Feature-flagged if high risk

---

## Success Metrics

### Quantitative
- ✅ Type coverage: 100% (currently ~95%)
- ✅ Test coverage: >90% (currently ~85%)
- ✅ Zero blocking I/O in async functions
- ✅ Resource cleanup: 100% (no leaks)
- ✅ Response time: <100ms p95 (under load)

### Qualitative
- ✅ IDE autocomplete works everywhere
- ✅ No production crashes
- ✅ Monitoring shows healthy state
- ✅ Team confident in codebase

---

## Dependencies

### External
- None - all fixes are internal

### Internal
- Must coordinate with any ongoing feature work
- May need to rebase feature branches after fixes

---

## Communication Plan

### Daily Standups
- Status update on current milestone
- Blockers and risks
- Next day plan

### Documentation
- Update CHANGELOG.md with each fix
- Add ADR for architectural decisions
- Update README if needed

---

## Post-Completion

After all P0+P1 fixes:
1. Tag release as `v1.0.0-rc1` (release candidate)
2. Deploy to staging environment
3. Run production-like load tests
4. Get security audit
5. Prepare for production deployment

**Estimated Production Ready**: 2025-12-23 (Week 51 + 1 week staging)
