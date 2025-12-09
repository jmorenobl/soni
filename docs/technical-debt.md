# Technical Debt Register

**Project**: Soni Framework
**Last Updated**: 2025-12-09

---

## Overview

This document tracks known technical debt in the Soni Framework. Technical debt represents intentional shortcuts or suboptimal implementations accepted to meet deadlines or prioritize critical fixes, with the intention of refactoring later.

**Debt Management Strategy**:
1. **Document** debt when incurred
2. **Track** impact and priority
3. **Plan** repayment schedule
4. **Execute** refactoring when appropriate
5. **Close** debt items when resolved

---

## Active Debt Items

### DEBT-001: Retry Logic Duplication (DRY Violation)

**Status**: 🔴 Active
**Priority**: HIGH
**Impact**: Maintainability, Code Quality
**Incurred**: 2025-12-09
**Related Tasks**: Task 204 (Confirmation Flow Fix)
**Estimated Effort to Resolve**: 2-3 hours

#### Description

The retry counter logic for handling unclear user responses is duplicated across multiple node functions:
- `handle_confirmation_node` - Confirmation retry logic
- `handle_correction_node` - Correction retry logic (proposed)
- `handle_modification_node` - Modification retry logic (proposed)
- `collect_next_slot_node` - Collection retry logic (proposed)

**Current Implementation** (duplicated ~4 times):
```python
# Repeated in each node
async def handle_[operation]_node(state, runtime) -> dict:
    metadata = state.get("metadata", {})
    retry_count = metadata.get("_[operation]_retries", 0)

    if retry_count >= MAX_RETRIES:
        logger.error(f"Max retries for [operation] exceeded")
        # ... error handling code ...

    # ... node logic ...

    if should_retry:
        metadata_updated = metadata.copy()
        metadata_updated["_[operation]_retries"] = retry_count + 1
        return {..., "metadata": metadata_updated}
```

**Violations**:
- ❌ **DRY** (Don't Repeat Yourself): Same logic copied 4+ times
- ❌ **SRP** (Single Responsibility): Each node handles both domain logic AND retry logic
- ❌ **DIP** (Dependency Inversion): Nodes depend on concrete metadata structure, not abstraction

#### Why Debt Was Accepted

**Rationale**: Critical bug fix needed urgently

Tasks 201-205 fix a **CRITICAL** infinite loop bug that makes confirmation steps completely unusable. The system hits LangGraph's recursion limit (25 iterations) causing complete failure.

**Business Impact if not fixed immediately**:
- Confirmation flows are broken in production
- Users cannot complete bookings or confirmations
- System appears to hang/timeout

**Decision**: Accept DRY violation in Task 204 to deliver working defensive checks quickly, with plan to refactor immediately after.

#### Impact Assessment

**Severity**: MEDIUM
- Not a runtime bug (code works correctly)
- Affects maintainability and future development
- Makes changes error-prone (must update 4+ places)

**Technical Impact**:
- Changes to retry behavior require updating 4+ nodes
- Inconsistency risk if one node updated but others missed
- Testing requires duplicated test cases
- Increased cognitive load for developers

**Business Impact**:
- Slower feature development (code harder to change)
- Higher risk of bugs in retry logic
- Increased maintenance cost

#### Repayment Plan

**When to Repay**: Immediately after Tasks 201-205 complete

**Proposed Solution**: Create `RetryHandler` abstraction

**Implementation**:
```python
# src/soni/utils/retry_handler.py
class RetryHandler:
    """Centralized retry logic following SOLID principles."""

    def __init__(self, max_retries: int, retry_key: str, error_message: str):
        self.max_retries = max_retries
        self.retry_key = retry_key
        self.error_message = error_message

    def should_fail(self, state: dict) -> bool:
        """Check if max retries exceeded."""
        # ... implementation ...

    def increment_retry(self, state: dict) -> dict:
        """Increment and return metadata updates."""
        # ... implementation ...

    def clear_retry(self, state: dict) -> dict:
        """Clear retry counter on success."""
        # ... implementation ...

# Usage in nodes
CONFIRMATION_RETRY = RetryHandler(
    max_retries=3,
    retry_key="_confirmation_attempts",
    error_message="I'm having trouble understanding..."
)

async def handle_confirmation_node(state, runtime):
    if CONFIRMATION_RETRY.should_fail(state):
        return CONFIRMATION_RETRY.create_error_response(state)
    # ... node logic ...
```

**Refactoring Steps**:
1. Create `RetryHandler` class in `src/soni/utils/retry_handler.py` (1 hour)
2. Update `handle_confirmation_node` to use `RetryHandler` (20 min)
3. Update other nodes if implemented (20 min each)
4. Add unit tests for `RetryHandler` (1 hour)
5. Verify all integration tests still pass (20 min)

**Total Effort**: 2-3 hours

**Success Criteria**:
- [ ] `RetryHandler` class created and tested
- [ ] All nodes using `RetryHandler` (no duplicated retry logic)
- [ ] All tests pass (no regressions)
- [ ] Code review approved
- [ ] Documentation updated

**Assigned To**: TBD
**Target Date**: Immediately after Tasks 201-205 merge

#### References

- **Analysis**: `docs/analysis/ANALISIS_ERROR_CONFIRMACION.md`
- **Improvement Doc**: `workflow/tasks/backlog/MEJORAS_PRINCIPIOS_SOLID_DRY.md`
- **Related Tasks**: Task 204 in `workflow/tasks/backlog/task-204-add-defensive-checks.md`
- **SOLID Principles**: `.cursor/rules/001-architecture.mdc`

---

### DEBT-002: Test-After Instead of TDD

**Status**: 🟡 Active
**Priority**: MEDIUM
**Impact**: Code Quality, Test Coverage
**Incurred**: 2025-12-09
**Related Tasks**: Tasks 201-205 (Confirmation Flow Fix)
**Estimated Effort to Resolve**: N/A (process change, not code)

#### Description

Tasks 201-205 propose implementing code first, then writing tests. This is "test-after" approach, not true Test-Driven Development (TDD).

**TDD Process** (not followed):
1. ✅ **RED**: Write failing test first
2. ✅ **GREEN**: Write minimal code to pass test
3. ✅ **REFACTOR**: Improve implementation

**Current Approach** (used in tasks):
1. ❌ Implement feature/fix
2. ❌ Write tests after
3. ❌ Hope tests pass

**Violations**:
- ❌ **TDD Principle**: Tests should drive design
- ❌ **Design Quality**: Implementation not validated for testability
- ⚠️ **Coverage Risk**: Tests may miss edge cases found during implementation

#### Why Debt Was Accepted

**Rationale**: Critical bug fix urgency + Working with existing codebase

**Reasons**:
1. **Critical Priority**: P0 bug breaking production functionality
2. **Existing Code**: Retrofitting tests to existing architecture (not greenfield)
3. **Time Pressure**: Test-after faster for urgent fixes
4. **Known Pattern**: Fixing bug in existing design, not creating new design

**Decision**: Accept test-after for Tasks 201-205 (critical fix), enforce TDD for new features going forward.

#### Impact Assessment

**Severity**: LOW-MEDIUM
- Does not affect runtime behavior
- Tests will be written (just not first)
- Primarily affects development process

**Technical Impact**:
- May miss testability issues until after implementation
- Harder to refactor (tests not guiding design)
- Potential gaps in test coverage

**Business Impact**:
- Minimal: tests still written, code still tested
- Slightly higher risk of bugs in corner cases

#### Repayment Plan

**When to Repay**: For future features (not retroactive)

**Proposed Solution**: Enforce TDD for new features

**Process Changes**:
1. **New Feature Development**: Strictly follow TDD (Red-Green-Refactor)
2. **Bug Fixes**: Can use test-after if urgent (document why)
3. **Code Review**: Check that tests were written first (or exception documented)
4. **Templates**: Update task templates to include TDD steps

**Success Criteria**:
- [ ] Task template updated with TDD cycle steps
- [ ] Code review checklist includes "Tests written first?"
- [ ] Team training on TDD process
- [ ] 80%+ of new features follow TDD

**Assigned To**: Team Lead / Process Owner
**Target Date**: Before next feature sprint

#### References

- **TDD Guide**: Kent Beck's "Test-Driven Development: By Example"
- **Task Template**: `workflow/tasks/backlog/task-template.md`
- **Improvement Doc**: `workflow/tasks/backlog/MEJORAS_PRINCIPIOS_SOLID_DRY.md`

---

### DEBT-003: Direct Metadata Dependency (DIP Violation)

**Status**: 🟡 Active
**Priority**: LOW
**Impact**: Architecture, Coupling
**Incurred**: 2025-12-09
**Related Tasks**: Task 204
**Estimated Effort to Resolve**: 4-6 hours (included in DEBT-001 refactor)

#### Description

Node functions directly access and manipulate the `metadata` dictionary for storing retry counters, confirmation flags, etc. This creates tight coupling between nodes and the state structure.

**Current Implementation**:
```python
async def handle_confirmation_node(state, runtime):
    # Direct dependency on metadata structure
    metadata = state.get("metadata", {})
    retry_count = metadata.get("_confirmation_attempts", 0)

    # Direct manipulation
    metadata_updated = metadata.copy()
    metadata_updated["_confirmation_attempts"] = retry_count + 1
```

**Violations**:
- ❌ **DIP** (Dependency Inversion): Nodes depend on concrete metadata structure
- ⚠️ **Coupling**: Changes to metadata structure affect all nodes
- ⚠️ **Testability**: Hard to mock/test metadata interactions

#### Why Debt Was Accepted

**Rationale**: Part of Task 204 quick defensive fix

Included as part of DEBT-001 (retry logic duplication). Will be resolved when `RetryHandler` abstraction is implemented.

#### Impact Assessment

**Severity**: LOW
- Code works correctly
- Primarily architectural concern
- Would only matter if metadata structure changes (unlikely)

**Technical Impact**:
- If metadata structure changes, must update many nodes
- Harder to test in isolation
- Tight coupling to state implementation

**Business Impact**:
- Minimal: unlikely to need metadata structure changes
- Slight increase in refactoring cost if structure changes

#### Repayment Plan

**When to Repay**: Automatically resolved when DEBT-001 is paid

The `RetryHandler` abstraction will encapsulate metadata access:
```python
class RetryHandler:
    def get_attempt_count(self, state: dict) -> int:
        # Encapsulates metadata access
        metadata = state.get("metadata", {})
        return metadata.get(self.retry_key, 0)
```

Nodes will depend on `RetryHandler` interface, not concrete metadata structure.

**Effort**: Included in DEBT-001 (no additional work)

**Success Criteria**:
- [ ] Nodes use `RetryHandler` methods (not direct metadata access)
- [ ] Metadata structure hidden behind abstraction
- [ ] Tests mock `RetryHandler`, not metadata dict

**Assigned To**: Same as DEBT-001
**Target Date**: Same as DEBT-001

#### References

- **SOLID Principles**: `.cursor/rules/001-architecture.mdc`
- **Related Debt**: DEBT-001 (Retry Logic Duplication)

---

## Resolved Debt Items

_No resolved debt items yet. This section will track paid-off technical debt for historical reference._

---

## Debt Metrics

### Current Debt Summary

| ID | Title | Priority | Impact | Effort | Status |
|----|-------|----------|--------|--------|--------|
| DEBT-001 | Retry Logic Duplication | HIGH | Maintainability | 2-3h | 🔴 Active |
| DEBT-002 | Test-After Instead of TDD | MEDIUM | Process | N/A | 🟡 Active |
| DEBT-003 | Direct Metadata Dependency | LOW | Architecture | 4-6h | 🟡 Active |

**Total Active Debt**: 3 items
**Estimated Repayment Effort**: 6-9 hours (DEBT-001 and DEBT-003)
**Process Changes Needed**: 1 (DEBT-002)

### Debt by Category

- **Code Quality**: 2 items (DEBT-001, DEBT-003)
- **Process**: 1 item (DEBT-002)

### Debt by Priority

- **HIGH**: 1 item (DEBT-001)
- **MEDIUM**: 1 item (DEBT-002)
- **LOW**: 1 item (DEBT-003)

---

## Debt Management Guidelines

### When to Accept Debt

**Acceptable Reasons**:
- ✅ Critical production bug fix (P0)
- ✅ Time-sensitive business requirement
- ✅ Exploration/prototype code
- ✅ Working with legacy constraints
- ✅ Trade-off explicitly discussed and approved

**Unacceptable Reasons**:
- ❌ Laziness or shortcuts
- ❌ Lack of knowledge (should ask/learn)
- ❌ "We'll fix it later" without plan
- ❌ Avoiding code review feedback

### How to Incur Debt

**Process**:
1. **Identify**: Recognize that a shortcut is being taken
2. **Document**: Add entry to this file with full context
3. **Justify**: Explain why debt is necessary
4. **Plan**: Define repayment approach and timeline
5. **Approve**: Get team lead sign-off
6. **Track**: Add to backlog/sprint planning

### How to Repay Debt

**Process**:
1. **Prioritize**: Include in sprint planning
2. **Assign**: Designate owner
3. **Execute**: Follow refactoring plan
4. **Verify**: Ensure tests pass, no regressions
5. **Close**: Move to "Resolved" section
6. **Learn**: Document lessons learned

### Debt Review Cadence

- **Weekly**: Review active debt in sprint planning
- **Monthly**: Assess debt trends and priorities
- **Quarterly**: Evaluate debt management process

---

## Debt Repayment Schedule

### Immediate (Week 1)

**Target**: After Tasks 201-205 merge

- [ ] **DEBT-001**: Refactor to `RetryHandler` class
  - Owner: TBD
  - Effort: 2-3 hours
  - Blocks: DEBT-003 (will be resolved together)

### Short-term (Sprint)

- [ ] **DEBT-002**: Update process for TDD
  - Owner: Team Lead
  - Effort: Process change + training
  - Impact: Future features only

### Long-term (Backlog)

- [ ] **DEBT-003**: Auto-resolved when DEBT-001 paid
  - No separate action needed

---

## Lessons Learned

### DEBT-001, DEBT-003: DRY Violation

**What Happened**: Rush to implement defensive checks led to duplicated retry logic

**Root Cause**: Time pressure + Focus on getting code working quickly

**Prevention**:
- Always ask: "Will this be needed in multiple places?"
- If yes, create abstraction first (doesn't take much longer)
- Use pair programming for rapid feedback

**Applied Learning**:
- For future urgent fixes, still take 10-15 min to design abstraction
- Better to spend 1 hour on good design than 3 hours refactoring later

### DEBT-002: Test-After

**What Happened**: Implemented fixes before writing tests (test-after, not TDD)

**Root Cause**: Critical bug + Existing codebase constraints

**Prevention**:
- For new features (greenfield): Strictly enforce TDD
- For bug fixes in existing code: Test-after acceptable if documented
- Clear policy: "When is test-after ok?"

**Applied Learning**:
- TDD is ideal but pragmatism sometimes needed
- Document exceptions so they don't become habit
- Retroactively enforce TDD for new code going forward

---

## References

### Internal Documentation

- **Architecture**: `docs/design/02-architecture.md`
- **SOLID Principles**: `.cursor/rules/001-architecture.mdc`
- **Testing Guide**: `.cursor/rules/003-testing.mdc`
- **Code Style**: `.cursor/rules/002-code-style.mdc`

### External Resources

- **Technical Debt**: Martin Fowler's "Technical Debt Quadrant"
- **SOLID Principles**: Robert C. Martin's "Clean Architecture"
- **TDD**: Kent Beck's "Test-Driven Development: By Example"
- **DRY Principle**: "The Pragmatic Programmer" by Hunt & Thomas

---

## Change Log

| Date | Change | Author |
|------|--------|--------|
| 2025-12-09 | Created technical debt register | Claude |
| 2025-12-09 | Added DEBT-001: Retry Logic Duplication | Claude |
| 2025-12-09 | Added DEBT-002: Test-After Instead of TDD | Claude |
| 2025-12-09 | Added DEBT-003: Direct Metadata Dependency | Claude |

---

**Status**: 🔴 3 Active Debt Items
**Next Review**: After Tasks 201-205 complete
**Owner**: Development Team
