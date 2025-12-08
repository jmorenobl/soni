# Design vs Implementation Inconsistencies

This document tracks inconsistencies between the design documentation and the actual implementation.

## Summary

After investigating the slot correction test failure, several inconsistencies were identified between the design documentation and the implementation.

## Critical Inconsistencies

### 1. Missing Dedicated Correction/Modification Handlers

**Design Specification** (`docs/design/05-message-flow.md` lines 282-285):
```python
case MessageType.CORRECTION:
    return "handle_correction"
case MessageType.MODIFICATION:
    return "handle_modification"
```

**Current Implementation** (`src/soni/dm/routing.py` lines 289-303):
- Corrections and modifications are routed to `validate_slot` (same as `slot_value`)
- No dedicated `handle_correction` or `handle_modification` nodes exist

**Impact**: Corrections and modifications are not handled according to design, leading to incorrect behavior when correcting slots from previous steps.

---

### 2. Incorrect Behavior: "Return to Current Step" Not Implemented

**Design Specification** (`docs/design/10-dsl-specification/06-patterns.md` line 71):
> "Both patterns are handled the same way: **update the slot, return to current step**."

**Design Example** (lines 53-68):
```
Bot: "Flying from Madrid to San Francisco on Dec 15th. Confirm?"
User: "Sorry, I said San Francisco but I meant San Diego"
→ Runtime detects correction of 'destination'
→ Updates destination = "San Diego"
→ Returns to confirmation step (NOT restart)
```

**Current Implementation** (`src/soni/dm/nodes/validate_slot.py` lines 98-134):
- When a slot is corrected, the system:
  1. Updates the slot ✓
  2. Checks if `current_step` is complete
  3. If complete, **advances to next step** ✗ (INCORRECT)
  4. Should **return to current step** (where user was) ✓ (NOT IMPLEMENTED)

**Impact**: When correcting a slot during confirmation or after all slots are filled, the system advances instead of returning to the current step, breaking the expected behavior.

**Example Failure**:
- User provides all slots → system is at confirmation step
- User corrects date → system updates date but then asks for origin (next step) instead of re-showing confirmation

---

### 3. Correction During Confirmation Not Handled Automatically

**Design Specification** (`docs/design/10-dsl-specification/06-patterns.md` lines 162-173):
```
**User says "Change the destination to LA"** →
1. Update `destination = "LA"`
2. Re-display confirmation with updated value
3. Wait for new confirmation

**User says "No wait, I meant December 20th not 15th"** →
1. Detect correction of `departure_date`
2. Update `departure_date = "2024-12-20"`
3. Re-display confirmation with updated value
4. Wait for new confirmation

This happens **automatically**. No DSL configuration needed.
```

**Current Implementation**:
- `handle_confirmation_node` only handles yes/no responses
- Corrections during confirmation are not automatically detected and handled
- No automatic re-display of confirmation after correction

**Impact**: Users cannot correct slots during confirmation as designed.

---

### 4. Missing State Variables for Corrections

**Design Specification** (`docs/design/10-dsl-specification/06-patterns.md` lines 225-228):
| Variable | Type | Description |
|----------|------|-------------|
| `_correction_slot` | string | Slot that was corrected (if any) |
| `_correction_value` | any | New value from correction |
| `_modification_slot` | string | Slot that was modified (if any) |
| `_modification_value` | any | New value from modification |

**Current Implementation**:
- These state variables are not set when corrections/modifications occur
- No tracking of which slot was corrected or its new value

**Impact**: Cannot use these variables in branch conditions or responses as designed.

---

## Medium Priority Inconsistencies

### 5. Routing Logic for Corrections Without Active Flow

**Current Implementation** (`src/soni/dm/routing.py` lines 289-303):
- When correction/modification is detected but no flow is active, system starts flow
- This may not be the intended behavior for corrections (should there be a flow to correct?)

**Design Gap**: Design doesn't specify what happens when correction is detected but no flow is active.

---

### 6. Missing Response Templates

**Design Specification** (`docs/design/10-dsl-specification/02-configuration.md` lines 102-110):
```yaml
correction_acknowledged:
  default: "Got it, I've updated {slot_name} to {new_value}."

modification_acknowledged:
  default: "Done, I've changed {slot_name} to {new_value}."
```

**Current Implementation**:
- These response templates may exist in config but are not used when corrections occur
- System doesn't acknowledge corrections with these messages

**Impact**: Users don't get feedback that their correction was processed.

---

## Recommendations

### High Priority Fixes

1. **Implement "Return to Current Step" Logic**:
   - When a correction/modification occurs, track the step where the user was
   - After updating the slot, return to that step instead of advancing
   - This is critical for corrections during confirmation steps

2. **Create Dedicated Correction/Modification Handlers**:
   - Implement `handle_correction_node` and `handle_modification_node`
   - These should handle the specific logic for corrections vs modifications
   - Route corrections/modifications to these nodes instead of `validate_slot`

3. **Handle Corrections During Confirmation**:
   - Detect corrections in `handle_confirmation_node`
   - Automatically update slot and re-display confirmation
   - This should happen automatically without DSL configuration

### Medium Priority Fixes

4. **Set State Variables**:
   - Set `_correction_slot`, `_correction_value`, `_modification_slot`, `_modification_value` when corrections occur
   - Allow these to be used in branch conditions and responses

5. **Use Response Templates**:
   - Use `correction_acknowledged` and `modification_acknowledged` templates when corrections occur
   - Provide user feedback that correction was processed

---

## Test Evidence

The test `test_e2e_slot_correction` fails because:
1. User provides all slots → system should be at confirmation/action step
2. User corrects date → system updates date but then asks for origin (next step)
3. Expected: System should acknowledge correction and continue from where it was
4. Actual: System advances to next step, asking for already-provided information

This directly demonstrates inconsistency #2 (not returning to current step).

---

## Related Files

- Design: `docs/design/10-dsl-specification/06-patterns.md`
- Design: `docs/design/05-message-flow.md`
- Implementation: `src/soni/dm/routing.py`
- Implementation: `src/soni/dm/nodes/validate_slot.py`
- Implementation: `src/soni/dm/nodes/handle_confirmation.py`
- Test: `tests/integration/test_e2e.py::test_e2e_slot_correction`

---

## Test Backlog

Tests have been created in `tests/integration/test_design_compliance_corrections.py` to validate
that the implementation adheres to the design specification. These tests are expected to FAIL
until the inconsistencies are fixed.

### Test Coverage

1. **test_correction_during_confirmation_returns_to_confirmation**
   - Validates: Corrections during confirmation return to confirmation step
   - Related to: Inconsistency #2, #3

2. **test_modification_during_confirmation_returns_to_confirmation**
   - Validates: Modifications during confirmation return to confirmation step
   - Related to: Inconsistency #2, #3

3. **test_correction_returns_to_current_step_not_next**
   - Validates: Corrections return to current step, not advance to next
   - Related to: Inconsistency #2

4. **test_correction_sets_state_variables**
   - Validates: `_correction_slot` and `_correction_value` are set
   - Related to: Inconsistency #4
   - Status: Skipped (requires state variable access API)

5. **test_modification_sets_state_variables**
   - Validates: `_modification_slot` and `_modification_value` are set
   - Related to: Inconsistency #4
   - Status: Skipped (requires state variable access API)

6. **test_correction_uses_acknowledgment_template**
   - Validates: Uses `correction_acknowledged` response template
   - Related to: Inconsistency #6

7. **test_modification_uses_acknowledgment_template**
   - Validates: Uses `modification_acknowledged` response template
   - Related to: Inconsistency #6

8. **test_correction_automatic_during_confirmation**
   - Validates: Corrections during confirmation are handled automatically
   - Related to: Inconsistency #3

### Running the Tests

```bash
# Run all design compliance tests
uv run pytest tests/integration/test_design_compliance_corrections.py -v

# Run with marker (if configured)
uv run pytest -m design_compliance -v
```

**Note**: These tests are expected to FAIL until the implementation is fixed.
They serve as executable specifications of the expected behavior.

---

**Last Updated**: 2025-12-08
**Status**: Active investigation - inconsistencies identified, tests created, fixes needed
