# LG-006: Interrupt Architecture Refactor

**Status**: In Progress
**Priority**: High
**Created**: 2025-12-20
**References**: `workflow/analysis/ADR-002-Interrupt-Architecture.md`

## Context
Implement the "Invoke Graph from Node" pattern to solve state isolation issues during interrupts. This moves `interrupt()` calls from subgraphs to the central orchestrator (`execute_node`), ensuring all user input passes through NLU.

## Technical Approach
Follow the design in `ADR-002`. Key changes include:
1. Modifying `execute.py` to handle the flow execution loop (invoke subgraph -> interrupt -> NLU).
2. Updating `collect_node` and `confirm_node` to return flags instead of calling interrupt.
3. Adding idempotency checks to `say_node` and `action_node`.
4. Updating `RuntimeLoop` and `builder.py` to pass subgraphs via context.

## Task Breakdown

### Phase 1: Infrastructure & State
- [ ] **DialogueState Updates**: Add `_need_input`, `_pending_prompt`, `_executed_steps` (scoped by flow_id) to `core/types.py`.
- [ ] **RuntimeContext Updates**: Add `subgraphs` and `nlu_service` to `RuntimeContext` in `core/types.py`.
- [ ] **State Initialization**: Update `create_empty_dialogue_state` in `core/state.py`.
- [ ] **Flow Cleanup**: Update `FlowManager.pop_flow` to clean up `_executed_steps`.
- [ ] **Cleanup Constants**: Remove `NodeName.REQUEST_INPUT` from `core/constants.py`.

### Phase 2: Node Idempotency & Refactor
- [ ] **Refactor `collect_node`**: Remove `interrupt()`, return `_need_input` flag.
- [ ] **Refactor `confirm_node`**: Remove `interrupt()`, cleanup handlers in `confirm_handlers.py`.
- [ ] **Update `say_node`**: Add idempotency check using `_executed_steps`.
- [ ] **Update `action_node`**: Add idempotency check using `_executed_steps`.
- [ ] **Update `set_node`**: Add idempotency check (optional but recommended).
- [ ] **Delete Legacy**: Remove `compiler/nodes/request_input.py`.

### Phase 3: Orchestrator Logic
- [ ] **Refactor `execute_node`**: Rewrite `dm/nodes/execute.py` to implement the "Invoke from Node" pattern loop.
- [ ] **Update `build_orchestrator`**: Modify `dm/builder.py` to compile subgraphs but NOT add them as nodes (return separately).
- [ ] **Update `RuntimeLoop`**: Pass compiled subgraphs to `RuntimeContext`.

### Phase 4: Verification
- [ ] **Unit Tests**: Verify new `execute_node` logic and node idempotency.
- [ ] **Integration Tests**: Verify full flow interruption and resumption.
- [ ] **Manual Verification**: Test banking transfer flow with digression.

## Acceptance Criteria
- [ ] `interrupt()` is ONLY called in `execute_node`.
- [ ] `collect_node` and `confirm_node` are pure logic (no checks for interrupt return values).
- [ ] NLU processing happens in `execute_node` after resume.
- [ ] `say_node` does not duplicate messages on re-invoke.
- [ ] `action_node` does not duplicate execution on re-invoke.
- [ ] Digressions (nested flows) work correctly without losing state.
