# Backlog: Design Compliance Fixes

This document tracks the backlog of work needed to make the implementation comply with the design specification.

## Overview

The implementation has several inconsistencies with the design documentation. This backlog tracks the work needed to fix them, organized by priority.

**Reference**: See `DESIGN_IMPLEMENTATION_INCONSISTENCIES.md` for detailed analysis.

**Tests**: See `tests/integration/test_design_compliance_corrections.py` for executable specifications.

---

## High Priority Fixes

### 1. Implement "Return to Current Step" Logic

**Priority**: 🔴 Critical
**Estimated Effort**: Medium
**Related Tests**:
- `test_correction_during_confirmation_returns_to_confirmation`
- `test_modification_during_confirmation_returns_to_confirmation`
- `test_correction_returns_to_current_step_not_next`

**Description**:
When a correction or modification occurs, the system must return to the step where the user was, not advance to the next step.

**Current Behavior**:
- System updates the slot ✓
- System checks if `current_step` is complete
- If complete, advances to next step ✗ (INCORRECT)

**Expected Behavior**:
- System updates the slot ✓
- System tracks the step where the user was
- System returns to that step (re-displays confirmation, continues from action, etc.) ✓

**Implementation Tasks**:
1. Track the step where user was when correction/modification occurs
2. Modify `validate_slot_node` to return to tracked step instead of advancing
3. Handle case where correction occurs during confirmation (return to confirmation)
4. Handle case where correction occurs during action (return to action or confirmation)

**Files to Modify**:
- `src/soni/dm/nodes/validate_slot.py`
- `src/soni/core/state.py` (may need to add step tracking)
- `src/soni/dm/routing.py` (may need routing changes)

**Acceptance Criteria**:
- [ ] Corrections during confirmation return to confirmation step
- [ ] Modifications during confirmation return to confirmation step
- [ ] Corrections after all slots filled return to current step (not advance)
- [ ] All related tests pass

---

### 2. Create Dedicated Correction/Modification Handlers

**Priority**: 🔴 Critical
**Estimated Effort**: Medium
**Related Tests**: None yet (internal routing test needed)

**Description**:
The design specifies dedicated nodes `handle_correction` and `handle_modification`, but the current implementation routes both to `validate_slot`.

**Current Behavior**:
- Corrections/modifications routed to `validate_slot` (same as `slot_value`)

**Expected Behavior**:
- Corrections routed to `handle_correction_node`
- Modifications routed to `handle_modification_node`
- These nodes handle correction/modification-specific logic

**Implementation Tasks**:
1. Create `src/soni/dm/nodes/handle_correction.py`
2. Create `src/soni/dm/nodes/handle_modification.py`
3. Update routing in `src/soni/dm/routing.py` to route to these nodes
4. Update graph builder to include these nodes
5. Implement correction-specific logic (return to step, set state variables)
6. Implement modification-specific logic (return to step, set state variables)

**Files to Create**:
- `src/soni/dm/nodes/handle_correction.py`
- `src/soni/dm/nodes/handle_modification.py`

**Files to Modify**:
- `src/soni/dm/routing.py`
- `src/soni/dm/builder.py`
- `src/soni/dm/node_factory_registry.py`

**Acceptance Criteria**:
- [ ] Corrections route to `handle_correction_node`
- [ ] Modifications route to `handle_modification_node`
- [ ] Routing logic matches design specification
- [ ] Nodes handle correction/modification-specific behavior

---

### 3. Handle Corrections During Confirmation Automatically

**Priority**: 🔴 Critical
**Estimated Effort**: Medium
**Related Tests**:
- `test_correction_automatic_during_confirmation`
- `test_correction_during_confirmation_returns_to_confirmation`

**Description**:
The design specifies that corrections during confirmation should be handled automatically - detect correction, update slot, re-display confirmation.

**Current Behavior**:
- `handle_confirmation_node` only handles yes/no responses
- Corrections during confirmation are not detected

**Expected Behavior**:
- `handle_confirmation_node` detects corrections/modifications
- Automatically updates slot
- Re-displays confirmation with updated value
- Waits for new confirmation

**Implementation Tasks**:
1. Modify `handle_confirmation_node` to check for corrections/modifications in NLU result
2. If correction/modification detected:
   - Extract slot and value from NLU result
   - Update slot in state
   - Re-display confirmation message with updated values
   - Set conversation_state back to "confirming"
3. Ensure this happens automatically (no DSL configuration needed)

**Files to Modify**:
- `src/soni/dm/nodes/handle_confirmation.py`

**Acceptance Criteria**:
- [ ] Corrections during confirmation are automatically detected
- [ ] Slots are updated automatically
- [ ] Confirmation is re-displayed with updated values
- [ ] No DSL configuration required
- [ ] All related tests pass

---

## Medium Priority Fixes

### 4. Set State Variables for Corrections/Modifications

**Priority**: 🟡 Medium
**Estimated Effort**: Low
**Related Tests**:
- `test_correction_sets_state_variables` (skipped - needs API)
- `test_modification_sets_state_variables` (skipped - needs API)

**Description**:
The design specifies state variables that should be set when corrections/modifications occur:
- `_correction_slot`: Slot that was corrected
- `_correction_value`: New value from correction
- `_modification_slot`: Slot that was modified
- `_modification_value`: New value from modification

**Current Behavior**:
- These variables are not set

**Expected Behavior**:
- When correction occurs, set `_correction_slot` and `_correction_value`
- When modification occurs, set `_modification_slot` and `_modification_value`
- These should be available for use in branch conditions and responses

**Implementation Tasks**:
1. Set `_correction_slot` and `_correction_value` in correction handler
2. Set `_modification_slot` and `_modification_value` in modification handler
3. Clear these variables after they're used (or at start of next turn)
4. Add API to access state variables for testing (if needed)

**Files to Modify**:
- `src/soni/dm/nodes/handle_correction.py` (when created)
- `src/soni/dm/nodes/handle_modification.py` (when created)
- `src/soni/core/state.py` (may need to add to state schema)

**Acceptance Criteria**:
- [ ] `_correction_slot` and `_correction_value` are set on correction
- [ ] `_modification_slot` and `_modification_value` are set on modification
- [ ] Variables are accessible in branch conditions
- [ ] Variables are accessible in response templates
- [ ] Tests can verify these variables are set

---

### 5. Use Response Templates for Corrections/Modifications

**Priority**: 🟡 Medium
**Estimated Effort**: Low
**Related Tests**:
- `test_correction_uses_acknowledgment_template`
- `test_modification_uses_acknowledgment_template`

**Description**:
The design specifies response templates that should be used when corrections/modifications occur:
- `correction_acknowledged`: "Got it, I've updated {slot_name} to {new_value}."
- `modification_acknowledged`: "Done, I've changed {slot_name} to {new_value}."

**Current Behavior**:
- Templates may exist in config but are not used
- System doesn't acknowledge corrections with these messages

**Expected Behavior**:
- When correction occurs, use `correction_acknowledged` template
- When modification occurs, use `modification_acknowledged` template
- Interpolate `{slot_name}` and `{new_value}` in templates

**Implementation Tasks**:
1. Load response templates from config
2. Use `correction_acknowledged` template when correction occurs
3. Use `modification_acknowledged` template when modification occurs
4. Interpolate slot name and value in templates
5. Include acknowledgment in response (may be combined with re-display of confirmation)

**Files to Modify**:
- `src/soni/dm/nodes/handle_correction.py` (when created)
- `src/soni/dm/nodes/handle_modification.py` (when created)
- `src/soni/core/config.py` (ensure templates are loaded)

**Acceptance Criteria**:
- [ ] `correction_acknowledged` template is used for corrections
- [ ] `modification_acknowledged` template is used for modifications
- [ ] Templates are properly interpolated with slot name and value
- [ ] Users receive feedback that correction/modification was processed
- [ ] All related tests pass

---

## Low Priority / Future Work

### 6. Routing Logic for Corrections Without Active Flow

**Priority**: 🟢 Low
**Estimated Effort**: Low
**Related Tests**: None

**Description**:
Current implementation starts a flow when correction is detected but no flow is active. Design doesn't specify what should happen in this case.

**Tasks**:
- [ ] Clarify expected behavior with design team
- [ ] Implement appropriate behavior
- [ ] Add tests

---

## Implementation Order

Recommended order for implementing fixes:

1. **Fix #1** (Return to Current Step) - Most critical, fixes main test failure
2. **Fix #3** (Handle Corrections During Confirmation) - Depends on #1
3. **Fix #2** (Dedicated Handlers) - Can be done in parallel or after #1
4. **Fix #4** (State Variables) - Low effort, can be done anytime
5. **Fix #5** (Response Templates) - Low effort, can be done anytime
6. **Fix #6** (Routing Without Flow) - Low priority, clarify first

---

## Testing Strategy

1. **Run existing tests**: `test_e2e_slot_correction` should pass after fixes
2. **Run design compliance tests**: All tests in `test_design_compliance_corrections.py` should pass
3. **Regression testing**: Ensure existing tests still pass
4. **Integration testing**: Test full flows with corrections at various points

---

## Success Criteria

All fixes are complete when:
- [ ] All tests in `test_design_compliance_corrections.py` pass
- [ ] `test_e2e_slot_correction` passes
- [ ] No regressions in existing tests
- [ ] Implementation matches design specification
- [ ] Documentation updated if needed

---

**Last Updated**: 2025-12-08
**Status**: Backlog created, ready for implementation
