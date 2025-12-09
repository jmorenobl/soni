# Technical Debt Register

**Project**: Soni Framework
**Last Updated**: 2025-12-10

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

### DEBT-001: Test-After Instead of TDD

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

### DEBT-002: Extensive Use of `Any` Type Instead of Specific Types (Type Safety Violation)

**Status**: 🟡 Active
**Priority**: MEDIUM
**Impact**: Type Safety, Maintainability
**Incurred**: 2025-12-10
**Related Tasks**: General codebase improvement
**Estimated Effort to Resolve**: 4-6 hours

#### Description

All node functions use `runtime: Any` instead of a specific type. Although there are explanatory comments, this violates type safety principles.

**Current Implementation** (12 files):
```python
# Repeated pattern across all nodes
async def handle_confirmation_node(
    state: DialogueState,
    runtime: Any,  # Runtime[RuntimeContext] - using Any to avoid import issues
) -> dict:
```

**Affected Files**:
- `handle_confirmation.py`, `generate_response.py`, `understand.py`, `confirm_action.py`
- `handle_intent_change.py`, `validate_slot.py`, `collect_next_slot.py`
- `handle_correction.py`, `handle_modification.py`, `execute_action.py`
- `handle_error.py`, `handle_digression.py`

**Violations**:
- ❌ **Type Safety**: No static type checking for runtime parameter
- ❌ **IDE Support**: Limited autocomplete and error detection
- ⚠️ **Maintainability**: Interface changes not caught at compile time
- ⚠️ **Documentation**: Type information only in comments (not enforced)

#### Why Debt Was Accepted

**Rationale**: LangGraph internal types complexity + Circular import concerns

**Reasons**:
1. **LangGraph Internals**: `Runtime` type is complex internal LangGraph type
2. **Circular Imports**: Using proper types might cause circular import issues
3. **Working Solution**: Code works correctly with comments explaining types
4. **Low Priority**: Not blocking functionality, primarily developer experience

**Decision**: Accept `Any` with comments for now, improve gradually with `TYPE_CHECKING` guards.

#### Impact Assessment

**Severity**: MEDIUM
- Does not affect runtime behavior
- Primarily affects developer experience and maintainability
- Makes refactoring riskier (type errors not caught early)

**Technical Impact**:
- Type errors only discovered at runtime
- IDE autocomplete less helpful
- Refactoring requires manual verification
- New developers may misuse runtime parameter

**Business Impact**:
- Slightly slower development (less IDE assistance)
- Higher risk of bugs from type mismatches
- Increased onboarding time

#### Repayment Plan

**When to Repay**: Gradually during refactoring cycles

**Proposed Solution**: Use `TYPE_CHECKING` guards for proper types

**Implementation**:
```python
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from langgraph.graph import Runtime
    from soni.core.state import RuntimeContext

async def handle_confirmation_node(
    state: DialogueState,
    runtime: Runtime[RuntimeContext],  # Proper type in TYPE_CHECKING
) -> dict:
    # Runtime code uses Any to avoid import issues
    pass
```

**Alternative Solution**: Create type alias for node function signature
```python
from typing import TypeAlias

if TYPE_CHECKING:
    from langgraph.graph import Runtime
    from soni.core.state import RuntimeContext

    NodeRuntime: TypeAlias = Runtime[RuntimeContext]
else:
    NodeRuntime: TypeAlias = Any

async def handle_confirmation_node(
    state: DialogueState,
    runtime: NodeRuntime,
) -> dict:
```

**Refactoring Steps**:
1. Create type aliases in `src/soni/core/types.py` (30 min)
2. Update imports in node files (1 hour)
3. Add `TYPE_CHECKING` guards (1 hour)
4. Update type hints gradually (2-3 hours)
5. Verify mypy passes (30 min)

**Total Effort**: 4-6 hours

**Success Criteria**:
- [ ] Type aliases created for node runtime types
- [ ] All nodes use proper types (with `TYPE_CHECKING`)
- [ ] Mypy passes without errors
- [ ] IDE autocomplete works correctly
- [ ] No circular import issues

**Assigned To**: TBD
**Target Date**: Next refactoring cycle

#### References

- **Type Hints Guide**: `docs/architecture.md` (Type Hints Guidelines section)
- **Python Typing**: PEP 484, PEP 563
- **LangGraph Types**: LangGraph documentation

---

### DEBT-003: Metadata Manipulation Logic Duplication (DRY Violation)

**Status**: 🔴 Active
**Priority**: HIGH
**Impact**: Maintainability, Consistency
**Incurred**: 2025-12-10
**Related Tasks**: General codebase improvement
**Estimated Effort to Resolve**: 2-3 hours

#### Description

The logic for clearing/updating metadata flags is duplicated across multiple nodes. The same pattern of copying metadata and popping specific keys is repeated 6+ times.

**Current Implementation** (duplicated 6+ times):
```python
# Repeated pattern in multiple nodes
metadata = state.get("metadata", {}).copy()
metadata.pop("_correction_slot", None)
metadata.pop("_correction_value", None)
metadata.pop("_modification_slot", None)
metadata.pop("_modification_value", None)
```

**Affected Files**:
- `handle_confirmation.py` (lines 55-58, 95-98, 121-124, 137-140, 164-167, 256-268)
- `handle_correction.py` (lines 90-95)
- `handle_modification.py` (lines 87-92)
- `understand.py` (lines 208-212)

**Violations**:
- ❌ **DRY** (Don't Repeat Yourself): Same logic copied 6+ times
- ❌ **Consistency**: Risk of inconsistencies if updated in one place but not others
- ⚠️ **Maintainability**: Changes require updating multiple files
- ⚠️ **Error-Prone**: Easy to miss a location when adding new flags

#### Why Debt Was Accepted

**Rationale**: Incremental development + Focus on functionality first

**Reasons**:
1. **Incremental Development**: Features added one at a time
2. **Working Code**: Logic works correctly in each location
3. **Low Priority Initially**: Not blocking functionality
4. **Pattern Recognition**: Only became obvious after multiple similar implementations

**Decision**: Accept duplication for now, refactor when pattern is clear.

#### Impact Assessment

**Severity**: MEDIUM-HIGH
- Code works correctly
- High risk of inconsistencies
- Makes maintenance error-prone

**Technical Impact**:
- Adding new metadata flags requires updating 6+ places
- Risk of bugs if one location missed
- Testing requires duplicated test cases
- Harder to understand metadata lifecycle

**Business Impact**:
- Slower feature development
- Higher risk of bugs
- Increased maintenance cost

#### Repayment Plan

**When to Repay**: Next refactoring cycle (high priority due to maintenance burden)

**Proposed Solution**: Create `MetadataManager` utility class

**Implementation**:
```python
# src/soni/utils/metadata_manager.py
class MetadataManager:
    """Centralized metadata manipulation following DRY principle."""

    @staticmethod
    def clear_correction_flags(metadata: dict) -> dict:
        """Clear correction-related flags from metadata."""
        updated = metadata.copy()
        updated.pop("_correction_slot", None)
        updated.pop("_correction_value", None)
        return updated

    @staticmethod
    def clear_modification_flags(metadata: dict) -> dict:
        """Clear modification-related flags from metadata."""
        updated = metadata.copy()
        updated.pop("_modification_slot", None)
        updated.pop("_modification_value", None)
        return updated

    @staticmethod
    def clear_confirmation_flags(metadata: dict) -> dict:
        """Clear confirmation-related flags from metadata."""
        updated = metadata.copy()
        updated.pop("_confirmation_attempts", None)
        updated.pop("_confirmation_processed", None)
        updated.pop("_confirmation_unclear", None)
        return updated

    @staticmethod
    def clear_all_flow_flags(metadata: dict) -> dict:
        """Clear all flow-related flags."""
        updated = metadata.copy()
        for key in [
            "_correction_slot", "_correction_value",
            "_modification_slot", "_modification_value",
            "_confirmation_attempts", "_confirmation_processed",
            "_confirmation_unclear"
        ]:
            updated.pop(key, None)
        return updated

# Usage in nodes
async def handle_confirmation_node(state, runtime):
    metadata = state.get("metadata", {})
    metadata_cleared = MetadataManager.clear_confirmation_flags(metadata)
    return {"metadata": metadata_cleared}
```

**Refactoring Steps**:
1. Create `MetadataManager` class (30 min)
2. Update `handle_confirmation.py` (30 min)
3. Update `handle_correction.py` (15 min)
4. Update `handle_modification.py` (15 min)
5. Update `understand.py` (15 min)
6. Add unit tests (1 hour)
7. Verify all tests pass (30 min)

**Total Effort**: 2-3 hours

**Success Criteria**:
- [ ] `MetadataManager` class created and tested
- [ ] All nodes use `MetadataManager` (no duplicated metadata logic)
- [ ] All tests pass (no regressions)
- [ ] Code review approved
- [ ] Documentation updated

**Assigned To**: TBD
**Target Date**: Next sprint (high priority)

#### References

- **DRY Principle**: "The Pragmatic Programmer" by Hunt & Thomas
- **SOLID Principles**: `.cursor/rules/001-architecture.mdc`

---

### DEBT-004: `generate_response_node` Violates SRP (Multiple Responsibilities)

**Status**: 🟡 Active
**Priority**: MEDIUM
**Impact**: Maintainability, Testability
**Incurred**: 2025-12-10
**Related Tasks**: General codebase improvement
**Estimated Effort to Resolve**: 3-4 hours

#### Description

The `generate_response_node` function has multiple responsibilities mixed together:

1. **Generate response** to user (primary responsibility)
2. **Manage conversation_state** (state management)
3. **Clean up completed flows** from stack (flow lifecycle)
4. **Archive flows** in metadata (data persistence)

**Current Implementation**:
```python
async def generate_response_node(state, runtime) -> dict:
    # Responsibility 1: Generate response
    response = _generate_response_from_slots(state)

    # Responsibility 2: Manage conversation_state
    if current_conv_state == "completed":
        # Responsibility 3: Clean up flow stack
        flow_stack = state.get("flow_stack", [])
        completed_flow = flow_stack.pop()

        # Responsibility 4: Archive in metadata
        state["metadata"]["completed_flows"].append(completed_flow)
```

**Violations**:
- ❌ **SRP** (Single Responsibility Principle): 4 responsibilities in one function
- ⚠️ **Testability**: Difficult to test each responsibility separately
- ⚠️ **Maintainability**: Changes to one responsibility affect others
- ⚠️ **Reusability**: Cannot reuse response generation without state management

#### Why Debt Was Accepted

**Rationale**: Convenience + Single node for response generation

**Reasons**:
1. **Convenience**: All response-related logic in one place
2. **Working Code**: Function works correctly
3. **Low Priority**: Not blocking functionality
4. **Incremental Growth**: Responsibilities added over time

**Decision**: Accept for now, refactor when adding new response generation features.

#### Impact Assessment

**Severity**: MEDIUM
- Code works correctly
- Makes testing and maintenance harder
- Limits reusability

**Technical Impact**:
- Cannot test response generation without state management
- Changes to state management affect response generation
- Harder to add new response types
- Function is harder to understand

**Business Impact**:
- Slightly slower feature development
- Higher risk of bugs when modifying
- Increased maintenance cost

#### Repayment Plan

**When to Repay**: When adding new response generation features

**Proposed Solution**: Split into specialized functions

**Implementation**:
```python
# src/soni/utils/response_generator.py
class ResponseGenerator:
    """Generate responses from state (single responsibility)."""

    @staticmethod
    def generate_from_priority(state: DialogueState) -> str:
        """Generate response based on priority order."""
        slots = get_all_slots(state)

        # Priority: confirmation > booking_ref > action_result > existing > default
        if "confirmation" in slots and slots["confirmation"]:
            return slots["confirmation"]
        elif "booking_ref" in slots and slots["booking_ref"]:
            return f"Booking confirmed! Your reference is: {slots['booking_ref']}"
        # ... rest of priority logic
        return "How can I help you?"

# src/soni/utils/flow_cleanup.py
class FlowCleanupManager:
    """Manage flow cleanup and archiving (single responsibility)."""

    @staticmethod
    def cleanup_completed_flow(state: DialogueState) -> dict:
        """Clean up completed flow from stack and archive."""
        flow_stack = state.get("flow_stack", []).copy()
        if not flow_stack:
            return {}

        completed_flow = flow_stack[-1]
        if completed_flow.get("flow_state") != "completed":
            return {}

        flow_stack.pop()

        # Archive in metadata
        metadata = state.get("metadata", {}).copy()
        if "completed_flows" not in metadata:
            metadata["completed_flows"] = []
        metadata["completed_flows"].append(completed_flow)

        return {
            "flow_stack": flow_stack,
            "metadata": metadata
        }

# Updated node (single responsibility)
async def generate_response_node(state, runtime) -> dict:
    """Generate response to user (single responsibility)."""
    response = ResponseGenerator.generate_from_priority(state)
    return {"last_response": response}
```

**Refactoring Steps**:
1. Create `ResponseGenerator` class (1 hour)
2. Create `FlowCleanupManager` class (1 hour)
3. Update `generate_response_node` to use generators (30 min)
4. Create separate node for flow cleanup (optional) (30 min)
5. Add unit tests (1 hour)
6. Verify all tests pass (30 min)

**Total Effort**: 3-4 hours

**Success Criteria**:
- [ ] `ResponseGenerator` class created and tested
- [ ] `FlowCleanupManager` class created and tested
- [ ] `generate_response_node` has single responsibility
- [ ] All tests pass (no regressions)
- [ ] Code review approved

**Assigned To**: TBD
**Target Date**: Next refactoring cycle

#### References

- **SOLID Principles**: `.cursor/rules/001-architecture.mdc`
- **SRP**: Robert C. Martin's "Clean Architecture"
- **File**: `src/soni/dm/nodes/generate_response.py`

---

### DEBT-005: Direct `state.get()` Access Instead of Abstractions (DIP Violation)

**Status**: 🟡 Active
**Priority**: LOW
**Impact**: Architecture, Coupling
**Incurred**: 2025-12-10
**Related Tasks**: General codebase improvement
**Estimated Effort to Resolve**: 4-6 hours

#### Description

Nodes directly access state using `state.get()` instead of using helper functions or abstractions. This creates tight coupling between nodes and the state structure.

**Current Implementation** (throughout codebase):
```python
# Direct access pattern repeated everywhere
nlu_result = state.get("nlu_result") or {}
metadata = state.get("metadata", {})
flow_stack = state.get("flow_stack", [])
conversation_state = state.get("conversation_state")
```

**Violations**:
- ⚠️ **DIP** (Dependency Inversion): Direct dependency on state structure
- ⚠️ **Coupling**: Changes to state structure require updating many places
- ⚠️ **Testability**: Harder to mock state for testing
- ⚠️ **Consistency**: No centralized validation or defaults

#### Why Debt Was Accepted

**Rationale**: Simplicity + TypedDict compatibility

**Reasons**:
1. **Simplicity**: Direct access is straightforward
2. **TypedDict**: State is TypedDict, direct access is natural
3. **Working Code**: Code works correctly
4. **Low Priority**: Not blocking functionality

**Note**: Some helpers already exist (`get_slot`, `get_all_slots`) but are not used consistently.

#### Impact Assessment

**Severity**: LOW
- Code works correctly
- Primarily architectural concern
- Would only matter if state structure changes significantly

**Technical Impact**:
- If state structure changes, must update many nodes
- Harder to add validation or transformation
- Inconsistent default values
- Harder to test in isolation

**Business Impact**:
- Minimal: unlikely to need major state structure changes
- Slight increase in refactoring cost if structure changes

#### Repayment Plan

**When to Repay**: Gradually during refactoring cycles

**Proposed Solution**: Create consistent helper functions

**Implementation**:
```python
# src/soni/core/state.py (extend existing helpers)
def get_nlu_result(state: DialogueState) -> dict:
    """Get NLU result from state with consistent defaults."""
    return state.get("nlu_result") or {}

def get_metadata(state: DialogueState) -> dict:
    """Get metadata from state with consistent defaults."""
    return state.get("metadata", {})

def get_conversation_state(state: DialogueState, default: str = "idle") -> str:
    """Get conversation state with consistent defaults."""
    return state.get("conversation_state", default)

def get_flow_stack(state: DialogueState) -> list:
    """Get flow stack from state with consistent defaults."""
    return state.get("flow_stack", [])

# Usage in nodes
async def understand_node(state, runtime):
    nlu_result = get_nlu_result(state)  # Use helper
    metadata = get_metadata(state)  # Use helper
    # ...
```

**Refactoring Steps**:
1. Add helper functions to `src/soni/core/state.py` (1 hour)
2. Update nodes gradually (2-3 hours)
3. Add unit tests for helpers (1 hour)
4. Verify all tests pass (30 min)

**Total Effort**: 4-6 hours

**Success Criteria**:
- [ ] Helper functions created and tested
- [ ] Nodes use helpers consistently (no direct `state.get()`)
- [ ] All tests pass (no regressions)
- [ ] Code review approved

**Assigned To**: TBD
**Target Date**: Next refactoring cycle

#### References

- **SOLID Principles**: `.cursor/rules/001-architecture.mdc`
- **Existing Helpers**: `src/soni/core/state.py` (get_slot, get_all_slots)
- **DIP**: Robert C. Martin's "Clean Architecture"

---

### DEBT-006: Response Generation Logic Duplication (DRY Violation)

**Status**: 🟡 Active
**Priority**: LOW
**Impact**: Maintainability
**Incurred**: 2025-12-10
**Related Tasks**: General codebase improvement
**Estimated Effort to Resolve**: 2-3 hours

#### Description

Response generation logic is duplicated across multiple nodes. Similar patterns for generating confirmation messages and responses appear in different places.

**Current Implementation** (duplicated in 3 places):
- `generate_response.py`: Priority-based response generation (lines 28-76)
- `handle_confirmation.py`: `_generate_confirmation_message()` function (lines 313-353)
- `handle_digression.py`: Simple response generation (lines 28-30)

**Violations**:
- ❌ **DRY** (Don't Repeat Yourself): Similar logic in multiple places
- ⚠️ **Consistency**: Risk of inconsistent response formats
- ⚠️ **Maintainability**: Changes require updating multiple places

#### Why Debt Was Accepted

**Rationale**: Incremental development + Different contexts

**Reasons**:
1. **Incremental Development**: Features added one at a time
2. **Different Contexts**: Each node has slightly different needs
3. **Working Code**: Logic works correctly in each location
4. **Low Priority**: Not blocking functionality

#### Impact Assessment

**Severity**: LOW
- Code works correctly
- Makes maintenance slightly harder
- Risk of inconsistent responses

**Technical Impact**:
- Changes to response format require updating multiple places
- Risk of bugs if one location missed
- Harder to maintain consistent tone/style

**Business Impact**:
- Minimal: responses work correctly
- Slight increase in maintenance cost

#### Repayment Plan

**When to Repay**: Together with DEBT-004 (related response generation)

**Proposed Solution**: Centralize in `ResponseGenerator` class

**Implementation**:
```python
# src/soni/utils/response_generator.py
class ResponseGenerator:
    """Centralized response generation logic."""

    @staticmethod
    def generate_from_priority(state: DialogueState) -> str:
        """Generate response based on priority order."""
        # Centralized priority logic
        pass

    @staticmethod
    def generate_confirmation(
        slots: dict,
        step_config: Any,
        context: RuntimeContext
    ) -> str:
        """Generate confirmation message with slot values."""
        # Centralized confirmation logic
        pass

    @staticmethod
    def generate_digression_response(command: str) -> str:
        """Generate response for digression."""
        # Centralized digression logic
        pass
```

**Refactoring Steps**:
1. Create `ResponseGenerator` class (1 hour)
2. Move logic from `generate_response.py` (30 min)
3. Move logic from `handle_confirmation.py` (30 min)
4. Move logic from `handle_digression.py` (15 min)
5. Add unit tests (1 hour)
6. Verify all tests pass (30 min)

**Total Effort**: 2-3 hours

**Success Criteria**:
- [ ] `ResponseGenerator` class created and tested
- [ ] All response generation uses `ResponseGenerator`
- [ ] All tests pass (no regressions)
- [ ] Code review approved

**Assigned To**: TBD
**Target Date**: Together with DEBT-006 repayment

#### References

- **DRY Principle**: "The Pragmatic Programmer" by Hunt & Thomas
- **Related Debt**: DEBT-006 (generate_response_node SRP)
- **Files**: `generate_response.py`, `handle_confirmation.py`, `handle_digression.py`

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
| DEBT-004 | Extensive Use of `Any` Type | MEDIUM | Type Safety | 4-6h | 🟡 Active |
| DEBT-005 | Metadata Manipulation Duplication | HIGH | Maintainability | 2-3h | 🔴 Active |
| DEBT-006 | `generate_response_node` SRP Violation | MEDIUM | Maintainability | 3-4h | 🟡 Active |
| DEBT-007 | Direct `state.get()` Access | LOW | Architecture | 4-6h | 🟡 Active |
| DEBT-008 | Response Generation Duplication | LOW | Maintainability | 2-3h | 🟡 Active |

**Total Active Debt**: 8 items
**Estimated Repayment Effort**: 23-33 hours (code refactoring)
**Process Changes Needed**: 1 (DEBT-002)

### Debt by Category

- **Code Quality**: 5 items (DEBT-001, DEBT-005, DEBT-006, DEBT-008)
- **Architecture**: 2 items (DEBT-003, DEBT-007)
- **Type Safety**: 1 item (DEBT-004)
- **Process**: 1 item (DEBT-002)

### Debt by Priority

- **HIGH**: 2 items (DEBT-001, DEBT-005)
- **MEDIUM**: 3 items (DEBT-002, DEBT-004, DEBT-006)
- **LOW**: 3 items (DEBT-003, DEBT-007, DEBT-008)

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
  - Blocks: DEBT-003, DEBT-005 (will be resolved together)

- [ ] **DEBT-005**: Create `MetadataManager` class
  - Owner: TBD
  - Effort: 2-3 hours
  - Related: DEBT-001 (metadata manipulation)

### Short-term (Sprint)

- [ ] **DEBT-002**: Update process for TDD
  - Owner: Team Lead
  - Effort: Process change + training
  - Impact: Future features only

- [ ] **DEBT-006**: Split `generate_response_node` responsibilities
  - Owner: TBD
  - Effort: 3-4 hours
  - Related: DEBT-008 (response generation)

- [ ] **DEBT-008**: Centralize response generation logic
  - Owner: TBD
  - Effort: 2-3 hours
  - Related: DEBT-006 (response generation)

### Medium-term (Next Sprint)

- [ ] **DEBT-004**: Improve type hints with `TYPE_CHECKING`
  - Owner: TBD
  - Effort: 4-6 hours
  - Can be done gradually

- [ ] **DEBT-007**: Create consistent state access helpers
  - Owner: TBD
  - Effort: 4-6 hours
  - Can be done gradually

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
| 2025-12-10 | Added DEBT-004: Extensive Use of `Any` Type | Claude |
| 2025-12-10 | Added DEBT-005: Metadata Manipulation Duplication | Claude |
| 2025-12-10 | Added DEBT-006: `generate_response_node` SRP Violation | Claude |
| 2025-12-10 | Added DEBT-007: Direct `state.get()` Access | Claude |
| 2025-12-10 | Added DEBT-008: Response Generation Duplication | Claude |

---

**Status**: 🔴 8 Active Debt Items (2 HIGH, 3 MEDIUM, 3 LOW)
**Total Estimated Effort**: 23-33 hours
**Next Review**: After Tasks 201-205 complete
**Owner**: Development Team
