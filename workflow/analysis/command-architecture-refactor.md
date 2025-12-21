# Command Architecture Refactor - Pending Issues

**Date**: 2025-12-20
**Commit**: `890ab2c` (refactor: command architecture and digression handling)
**Status**: WIP - Core architecture implemented, several issues remain

## Summary

The refactor changed the command routing architecture from `Command(goto=...)` to state-based `_branch_target` for conditional_edges compatibility. Digression and branch routing now work, but confirm flow and response handling need fixes.

---

## ✅ Resolved Issues

### 1. Branch Routing with Conditional Edges
- **Problem**: `Command(goto=target)` doesn't work with `add_conditional_edges`
- **Solution**: Changed `branch_node` and `collect_node` to set `_branch_target` in state dict
- **Status**: ✅ Working

### 2. Slot Persistence via Reducer
- **Problem**: `flow_slots` appeared empty after slot updates
- **Solution**: `_merge_flow_slots` reducer correctly merges nested dicts
- **Status**: ✅ Working

### 3. Branch Target Clearing
- **Problem**: `_branch_target` persisted across nodes causing infinite loops
- **Solution**: Added `_branch_target: None` in `execute_node` and all node returns
- **Status**: ✅ Working

### 4. Command Persistence Across Turns
- **Problem**: Old commands from previous turns persisted in `state.commands`
- **Solution**: Added `commands: serialized_commands` to `Command(resume=..., update={})` in RuntimeLoop
- **Status**: ✅ Working

---

## ⚠️ Pending Issues

### P1: NLU Not Extracting AffirmConfirmation

**Severity**: High
**Location**: NLU/DU layer

**Problem**: When user says "yes" or "confirm" at a confirmation prompt, NLU extracts `StartFlow(transfer_funds)` instead of `AffirmConfirmation`.

**Evidence**:
```
>>> yes
Commands: [{'type': 'start_flow', 'flow_name': 'transfer_funds', 'slots': {}}]
```

**Expected**:
```
Commands: [{'type': 'affirm'}]
```

**Impact**: `confirm_node` cannot detect affirmation, falls through to interrupt or wrong path.

**Suggested Fix**:
- Add special handling in NLU when `waiting_for_slot_type == CONFIRMATION`
- Or add explicit patterns for affirm/deny in the confirmation context

---

### P2: Confirm Node Modification Detection Too Aggressive

**Severity**: Medium
**Location**: `src/soni/compiler/nodes/confirm.py` L153-164

**Problem**: Any `SetSlot` command in state triggers the modification handler, even if it's an unrelated NLU extraction.

**Evidence**:
```python
# Turn 5: User says "checking" for source_account
# NLU extracts: SetSlot(beneficiary_name="mom")  # Wrong extraction
# confirm_node sees has_modification=True, takes modification path
```

**Current State**: Logic commented out to allow flow to proceed.

**Suggested Fix**:
- Only consider SetSlot as modification if the slot is displayed in the confirmation prompt
- Parse prompt template to extract slot names (e.g., `{amount}`, `{iban}`)
- Check if any SetSlot.slot matches those names

---

### P3: Response Queue Accumulation

**Severity**: Medium
**Location**: `_pending_responses` handling in RuntimeLoop

**Problem**: Multiple prompts accumulate in response queue resulting in long combined messages.

**Evidence**:
```
Bot: How much would you like to transfer?

What should I put as the payment reference or concept?

From which of your accounts should I send this?
```

**Expected**: Single prompt per interrupt.

**Suggested Fix**:
- Verify `_pending_responses` is properly cleared on each turn
- Check if multiple flows are completing in single turn (causing multiple say nodes)
- Review RuntimeLoop's response combination logic

---

### P4: Confirm Interrupt/Resume Flow

**Severity**: Medium
**Location**: `src/soni/compiler/nodes/confirm.py` L200-220

**Problem**: After `interrupt()` pauses execution and resume provides affirm command, the node may not correctly set the confirmation slot and continue.

**Evidence**:
```
>>> checking
[CONFIRM value=None]  # Correct, should interrupt
>>> yes
[CONFIRM value=None]  # Still None - affirm not processed?
Stack: 0 flows        # Flow completed without setting slot
```

**Suggested Fix**:
- Trace the affirm handler path
- Verify `AffirmHandler.handle_interrupt()` sets the slot
- Check if Command(update=...) properly persists slot delta

---

## Architecture Notes

### Current Routing Pattern

```
Node returns dict → Router reads state → Conditional edge
                          ↓
                    _branch_target ?
                          ↓
                    Yes: return target
                    No: return default_next
```

### Key Invariants

1. Every node that can be a branch target MUST clear `_branch_target` in its return
2. `execute_node` clears `_branch_target` before entering any subgraph
3. `end_flow_node` clears `_branch_target` before subgraph exit
4. `Command(resume=..., update={commands: ...})` replaces old commands

---

## Files Modified

| File | Changes |
|------|---------|
| `compiler/nodes/branch.py` | Uses `_branch_target` state |
| `compiler/nodes/collect.py` | Uses `_branch_target`, clears on all paths |
| `compiler/nodes/confirm.py` | Modification detection commented |
| `compiler/nodes/say.py` | Appends to `_pending_responses` |
| `compiler/subgraph.py` | Router reads `_branch_target` |
| `dm/nodes/execute.py` | Clears `_branch_target` before routing |
| `dm/nodes/understand.py` | Extract-only, stores commands in state |
| `runtime/loop.py` | Updates commands on resume |

---

## Next Steps

1. **P1 (High)**: Fix NLU to extract AffirmConfirmation in confirmation context
2. **P4 (Medium)**: Debug confirm_node affirm handling path
3. **P2 (Medium)**: Implement smart modification detection for confirm
4. **P3 (Medium)**: Fix response queue accumulation
