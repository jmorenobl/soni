# ADR-002 Implementation Review

## Status: Structurally Sound - Minor Bugs Identified

The current implementation of `ADR-002` (Interrupt Architecture) is technically correct and adheres well to the "Invoke Graph from Node" pattern. The move of `interrupt()` to the orchestrator level correctly solves the state isolation issues.

However, a few critical "turn-logic" bugs were identified during integration testing:

### 1. Response Accumulation across Turns
- **Location**: `execute_flow_node.py`
- **Issue**: The `responses` list is a local variable in the node. When the node is suspended via `interrupt()`, its local state is preserved. When it resumes, `responses` still contains messages from previous turns.
- **Result**: Turn 3 includes responses from Turn 1 and 2.
- **Fix**: Clear `responses` immediately after `resume_value = interrupt(prompt)`.

### 2. Intermediate Message Loss
- **Location**: `subgraph.ainvoke` usage in `execute_flow_node.py`
- **Issue**: `ainvoke` only returns the FINAL state after the subgraph hits `END`. If a turn executes multiple `say` nodes (e.g. `Done 100` then `Ended`), the single `response` field is overwritten by the last one.
- **Result**: Only the final message of a turn is visible.
- **Fix**: Use `_pending_responses` (list) with an additive reducer.

### 3. Missing Idempotency in ConfirmNode
- **Location**: `confirm.py`
- **Issue**: While `say` and `action` have idempotency checks, `confirm` relies on command consumption. If re-invoked without a command, it re-prompts.
- **Fix**: Ensure `confirm_node` also checks `_executed_steps` if appropriate, or ensure it correctly yields if already processed.

---

## Proposed Fixes (Implementation Phase 2.1)

1. [x] **types.py**: Add `add_responses` additive reducer and update `_pending_responses` to use it.
2. [ ] **execute_flow_node.py**:
    - Clear `responses` on resume.
    - Collect from `result["_pending_responses"]` instead of `result["response"]`.
3. [ ] **say.py / collect.py / confirm.py**:
    - Stop using `response` field.
    - Return `_pending_responses: [message]` instead.
4. [ ] **subgraph.py**: Ensure it returns `_pending_responses: None` at the start to allow the reducer to pick up only new ones? No, the reducer is in the parent graph.

I am ready to implement these fixes to make the tests pass.
