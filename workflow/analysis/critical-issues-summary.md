# Soni Framework - Critical Issues Summary

## P0 - Production Blockers (Fix Immediately)

| # | Issue | Severity | Impact | Effort | Files |
|---|-------|----------|--------|--------|-------|
| 1 | FlowDelta type not exported | 🔴 CRITICAL | Type safety broken, IDE autocomplete fails | 2h | `core/types.py`, `flow/manager.py` |
| 2 | Sync blocking call in async | 🔴 CRITICAL | Event loop blocking, 10-100x slowdown | 3h | `runtime/loop.py:232-233` |
| 3 | Config mutation in compiler | 🔴 HIGH | Concurrency bugs, unpredictable behavior | 2h | `compiler/subgraph.py:171-176` |

~~4. Command serialization~~ → ✅ **VERIFIED CORRECT** (TypedDict + model_dump() is recommended LangGraph pattern)

**P0 Total Effort**: ~7 hours (reduced from 11h)

---

## P1 - Critical (Fix This Week)

| # | Issue | Severity | Impact | Effort | Files |
|---|-------|----------|--------|--------|-------|
| 5 | Missing async resource cleanup | 🟠 HIGH | Resource leaks in production | 4h | `runtime/loop.py:254-285` |
| 6 | Type ignore comments (3x) | 🟡 MEDIUM | Incomplete type safety | 2h | `runtime/hydrator.py:45`, `runtime/loop.py:73,85` |
| 7 | Missing error handling | 🟠 HIGH | Poor debugging experience | 3h | `server/routes.py` |
| 8 | No health checks | 🟠 HIGH | Can't monitor production | 2h | New: `server/health.py` |

**P1 Total Effort**: ~11 hours

---

## P2 - High Priority (Next Sprint)

| # | Issue | Severity | Impact | Effort | Files |
|---|-------|----------|--------|--------|-------|
| 9 | understand_node too large (355 LOC) | 🟡 MEDIUM | Hard to test, violates SRP | 8h | `dm/nodes/understand.py` |
| 10 | Hardcoded CommandHandlerRegistry | 🟡 MEDIUM | Violates Open/Closed | 4h | `dm/nodes/command_registry.py` |
| 11 | Missing integration tests | 🟡 MEDIUM | Low confidence in changes | 8h | New: `tests/integration/` |
| 12 | No observability | 🟡 MEDIUM | Difficult to debug production | 6h | Multiple files |

**P2 Total Effort**: ~26 hours

---

## Quick Wins (< 2 hours each)

✅ **Remove type: ignore comments** - 2h
✅ **Fix FlowDelta export** - 2h
✅ **Fix config mutation** - 2h
✅ **Add health checks** - 2h

**Total Quick Wins**: 8 hours → **4 critical issues fixed**

---

## Summary

- **Total Critical Issues**: 8 (reduced from 9 after verification)
- **Production Blockers (P0)**: 3 issues, 7 hours
- **Must Fix This Week (P1)**: 5 issues, 12 hours (includes new test)
- **High Priority (P2)**: 4 issues, 26 hours

**Recommendation**: Dedicate **1.5 engineer-days** to P0 fixes before any production deployment.

**Key Update**: Command serialization was verified to be correct implementation (TypedDict + model_dump() is the recommended LangGraph pattern), reducing P0 effort from 11h → 7h.

---

## Issue Resolution Order

### Day 1 (Morning)
1. ✅ Fix FlowDelta type export (2h)
2. ✅ Fix config mutation (2h)

### Day 1 (Afternoon)
3. ✅ Remove type: ignore (2h)
4. ✅ Add health checks (2h)

### Day 2 (Morning)
5. ✅ Fix sync blocking call + audit (4h)

### Day 2 (Afternoon)
6. ✅ Clarify command serialization (3h)
7. ⚠️ Start async cleanup (1h + continue next day)

---

## Testing Strategy

For each fix:
1. Write failing test first (TDD)
2. Implement fix
3. Verify test passes
4. Run full test suite
5. Manual smoke test

---

## Risk Assessment

| Issue | Risk if Not Fixed | Probability | Severity |
|-------|-------------------|-------------|----------|
| Sync blocking in async | Production crashes under load | HIGH | CRITICAL |
| FlowDelta type safety | Silent bugs during refactoring | MEDIUM | HIGH |
| Config mutation | Flaky tests, concurrency bugs | MEDIUM | HIGH |
| Command serialization | Runtime crashes | LOW | CRITICAL |
| Resource leaks | Memory exhaustion after hours | MEDIUM | HIGH |

**Overall Risk**: 🔴 **HIGH** - Do not deploy to production without P0 fixes
