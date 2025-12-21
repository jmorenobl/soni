# Interrupt Architecture Refactor - Complete Design

**Status**: Ready for Implementation
**Date**: 2025-12-20

---

## 1. Problem Statement

User input processed inside flow subgraphs cannot access NLU commands due to LangGraph subgraph state isolation on resume.

---

## 2. Solution Overview

**Pattern**: "Invoke Graph from Node" - move `interrupt()` to orchestrator level.

```
ORCHESTRATOR: understand → execute_flow_node → resume → respond
                                 │
                                 ▼
                    ┌─────────────────────────┐
                    │  while need_input:      │
                    │    invoke(subgraph)     │
                    │    if _need_input:      │
                    │      interrupt()        │
                    │      NLU(response)      │
                    └─────────────────────────┘
```

---

## 3. All File Changes

| File | Change | Purpose |
|------|--------|---------|
| `dm/nodes/execute_flow.py` | NEW | Central interrupt orchestrator |
| `dm/nodes/execute.py` | DELETE | Replaced by above |
| `dm/builder.py` | MODIFY | Return subgraphs separately |
| `runtime/loop.py` | MODIFY | Pass subgraphs to context |
| `core/types.py` | MODIFY | Add 3 new state fields |
| `core/state.py` | MODIFY | Initialize new fields |
| `compiler/nodes/collect.py` | MODIFY | Return flag, remove interrupt |
| `compiler/nodes/confirm.py` | MODIFY | Return flag, remove interrupt |
| `compiler/nodes/confirm_handlers.py` | MODIFY | Remove interrupt-specific handlers |
| `compiler/nodes/say.py` | MODIFY | Add idempotency |
| `compiler/nodes/action.py` | MODIFY | Add idempotency |
| `compiler/nodes/set.py` | MODIFY | Add idempotency (optional) |
| `compiler/nodes/branch.py` | NO CHANGE | Already idempotent |
| `compiler/nodes/while_loop.py` | NO CHANGE | Already idempotent |
| `compiler/nodes/request_input.py` | DELETE | No longer needed |

---

## 4. New State Fields (core/types.py)

```python
class DialogueState(TypedDict):
    # ... existing ...

    # Subgraph → Orchestrator communication
    _need_input: Annotated[bool, _last_value_bool]
    _pending_prompt: Annotated[dict | None, _last_value_any]

    # Idempotency tracking (key = flow_id)
    _executed_steps: Annotated[dict[str, set[str]], _merge_dicts]
```

**Rationale for `_executed_steps` structure**:
- Keyed by `flow_id` (not `flow_name`) to handle multiple instances of same flow
- Prevents collision when Flow A and Flow B both have `say_hello` step
- Cleaned up when flow is popped from stack

---

## 5. Node-by-Node Idempotency Analysis

### 5.1 Nodes That Are Already Idempotent (No Changes)

| Node | Why Idempotent |
|------|----------------|
| `collect_node` | Checks if slot filled first |
| `confirm_node` | Checks if confirmation slot set |
| `branch_node` | Pure function, no side effects |
| `while_node` | Pure condition evaluation |

### 5.2 Nodes That Need Idempotency Added

#### `say_node` - CRITICAL

**Problem**: Adds message to `_pending_responses` every re-invoke.

**Solution**:
```python
async def say_node(state, runtime) -> dict:
    fm = runtime.context.flow_manager
    flow_id = fm.get_active_flow_id(state)

    # IDEMPOTENT CHECK
    executed = state.get("_executed_steps", {}).get(flow_id, set())
    if step_name in executed:
        return {}

    # EXECUTE
    content = message_template.format(**slots)

    # MARK AS DONE
    new_executed = dict(state.get("_executed_steps", {}))
    new_executed[flow_id] = executed | {step_name}

    return {
        "messages": [AIMessage(content=content)],
        "_pending_responses": state.get("_pending_responses", []) + [content],
        "_executed_steps": new_executed,
    }
```

#### `action_node` - CRITICAL

**Problem**: Executes external action every re-invoke.

**Solution**:
```python
async def action_node(state, runtime) -> dict:
    fm = runtime.context.flow_manager
    flow_id = fm.get_active_flow_id(state)

    # IDEMPOTENT CHECK
    executed = state.get("_executed_steps", {}).get(flow_id, set())
    if step_name in executed:
        return {}

    # EXECUTE
    result = await action_handler.execute(action_name, slots)

    # MARK AS DONE + STORE RESULTS
    new_executed = dict(state.get("_executed_steps", {}))
    new_executed[flow_id] = executed | {step_name}

    updates = {"_executed_steps": new_executed}

    # Map outputs to slots
    if isinstance(result, dict):
        for key, value in result.items():
            slot_name = output_mapping.get(key, key)
            delta = fm.set_slot(state, slot_name, value)
            merge_delta(updates, delta)

    return updates
```

#### `set_node` - OPTIONAL (for efficiency)

**Problem**: Re-sets the same values (benign but wasteful).

**Solution** (same pattern as above, optional):
```python
executed = state.get("_executed_steps", {}).get(flow_id, set())
if step_name in executed:
    return {}
```

### 5.3 `collect_node` - Remove Interrupt

```python
async def collect_node(state, runtime) -> dict:
    fm = runtime.context.flow_manager

    # IDEMPOTENT: Already filled?
    if fm.get_slot(state, slot_name):
        return {}

    # CHECK COMMANDS: SetSlot for this slot?
    for cmd in state.get("commands", []):
        if is_set_slot_for(cmd, slot_name):
            delta = fm.set_slot(state, slot_name, cmd["value"])
            return {"commands": [], **_delta_to_dict(delta)}

    # NEED INPUT: Return flag (NO interrupt here)
    return {
        "_need_input": True,
        "_pending_prompt": {
            "type": "collect",
            "slot": slot_name,
            "prompt": prompt_message,
        }
    }
```

### 5.4 `confirm_node` - Remove Interrupt

Same pattern as collect_node:
- Check if `confirmation_slot` already has value
- Check commands for `AffirmConfirmation` / `DenyConfirmation`
- Return `{_need_input: True, _pending_prompt: {...}}` if needs input

**Note**: `confirm_handlers.py` methods using `handle_interrupt()` become obsolete - use standard `handle()` methods and return flags.

---

## 6. Orchestrator: `execute_flow_node`

```python
async def execute_flow_node(state, runtime) -> dict | Command:
    """Central flow execution with interrupt orchestration."""
    ctx = runtime.context
    fm = ctx.flow_manager
    nlu = ctx.nlu_service
    subgraphs = ctx.subgraphs

    # No active flow?
    stack = state.get("flow_stack", [])
    if not stack:
        return Command(goto=NodeName.RESPOND)

    active = stack[-1]
    flow_name = active["flow_name"]
    flow_id = active["flow_id"]
    subgraph = subgraphs[flow_name]

    # Prepare subgraph state (selected fields only)
    subgraph_state = {
        "flow_stack": state["flow_stack"],
        "flow_slots": state["flow_slots"],
        "commands": state.get("commands", []),
        "_executed_steps": state.get("_executed_steps", {}),
        "_need_input": False,   # Reset each invoke
        "_pending_prompt": None,
    }

    while True:
        # Invoke subgraph
        try:
            result = await subgraph.ainvoke(subgraph_state)
        except Exception as e:
            logger.error(f"Flow {flow_name} failed: {e}")
            raise

        # Flow completed or advanced?
        if not result.get("_need_input"):
            return _merge_result(state, result)

        # Subgraph needs input - interrupt HERE
        prompt = result.get("_pending_prompt", {})
        resume_value = interrupt(prompt)

        # Process NLU on response
        message = _extract_message(resume_value)
        nlu_result = await nlu.process_message(message, state, ctx)
        commands = nlu.serialize_commands(nlu_result.commands)

        # Check for digression/cancellation
        for cmd in commands:
            if cmd.get("type") == "start_flow":
                delta = fm.handle_intent_change(state, cmd["flow_name"])
                return Command(goto=NodeName.RESUME, update={
                    **_delta_to_dict(delta),
                    "_digression_pending": True
                })
            if cmd.get("type") == "cancel_flow":
                _, delta = fm.pop_flow(state)
                return Command(goto=NodeName.RESUME, update=_delta_to_dict(delta))

        # Continue with new commands
        subgraph_state["commands"] = commands
        subgraph_state["flow_slots"] = result.get("flow_slots", subgraph_state["flow_slots"])
        subgraph_state["_executed_steps"] = result.get("_executed_steps", {})


def _merge_result(parent_state: dict, result: dict) -> dict:
    """Merge subgraph result back to parent state."""
    updates = {}

    # Preserve slot changes
    if "flow_slots" in result:
        updates["flow_slots"] = result["flow_slots"]

    # Preserve executed steps
    if "_executed_steps" in result:
        updates["_executed_steps"] = result["_executed_steps"]

    # Collect pending responses
    if "_pending_responses" in result:
        parent_pending = parent_state.get("_pending_responses", [])
        updates["_pending_responses"] = parent_pending + result["_pending_responses"]

    # Messages
    if "messages" in result:
        updates["messages"] = result["messages"]

    # Clear consumed commands
    updates["commands"] = []

    return updates


def _extract_message(resume_value) -> str:
    """Extract message from resume value."""
    if isinstance(resume_value, str):
        return resume_value
    if isinstance(resume_value, dict):
        return resume_value.get("message", str(resume_value))
    return str(resume_value)
```

---

## 7. Orchestrator Changes: `build_orchestrator`

```python
def build_orchestrator(config, checkpointer=None) -> tuple[Runnable, dict]:
    """Build orchestrator and compile subgraphs separately."""

    # Compile subgraphs (NO checkpointer - parent manages state)
    compiler = SubgraphBuilder()
    subgraphs = {}
    for name, flow in config.flows.items():
        subgraphs[name] = compiler.build(flow).compile()

    # Build orchestrator
    builder = StateGraph(DialogueState, context_schema=RuntimeContext)

    builder.add_node(NodeName.UNDERSTAND, understand_node)
    builder.add_node(NodeName.EXECUTE_FLOW, execute_flow_node)  # NEW
    builder.add_node(NodeName.RESUME, resume_node)
    builder.add_node(NodeName.RESPOND, respond_node)

    builder.add_edge(START, NodeName.UNDERSTAND)
    builder.add_edge(NodeName.UNDERSTAND, NodeName.EXECUTE_FLOW)
    builder.add_edge(NodeName.EXECUTE_FLOW, NodeName.RESUME)

    def route_resume(state):
        if state.get("flow_stack"):
            return NodeName.EXECUTE_FLOW
        return NodeName.RESPOND

    builder.add_conditional_edges(
        NodeName.RESUME,
        route_resume,
        {NodeName.EXECUTE_FLOW: NodeName.EXECUTE_FLOW, NodeName.RESPOND: NodeName.RESPOND}
    )

    builder.add_edge(NodeName.RESPOND, END)

    return builder.compile(checkpointer=checkpointer), subgraphs
```

---

## 8. RuntimeContext Changes

```python
class RuntimeContext(TypedDict):
    flow_manager: FlowManagerProtocol
    action_handler: ActionHandlerProtocol
    config: SoniConfig

    # NEW
    subgraphs: dict[str, CompiledStateGraph]
    nlu_service: NLUServiceProtocol
```

---

## 9. RuntimeLoop Changes

```python
async def initialize(self):
    graph, subgraphs = build_orchestrator(self.config, self._checkpointer)
    self._graph = graph
    self._subgraphs = subgraphs

def _create_context(self) -> RuntimeContext:
    return RuntimeContext(
        flow_manager=self._flow_manager,
        action_handler=self._action_handler,
        config=self.config,
        subgraphs=self._subgraphs,
        nlu_service=self._nlu_service,
    )
```

---

## 10. Flow Stack Cleanup

When a flow is popped, clean up its `_executed_steps`:

```python
# In FlowManager.pop_flow()
def pop_flow(self, state):
    stack = state.get("flow_stack", [])
    if not stack:
        return None, None

    popped = stack[-1]
    flow_id = popped["flow_id"]
    new_stack = stack[:-1]

    # Clean up executed steps for this flow
    executed = dict(state.get("_executed_steps", {}))
    executed.pop(flow_id, None)

    delta = FlowDelta(
        flow_stack=new_stack,
        flow_slots=...,
        executed_steps=executed,  # NEW field in FlowDelta
    )
    return popped, delta
```

---

## 11. While Loop Considerations

While loops already documented in `while_loop.py` (lines 50-82) as **problematic with user input**:

> "AVOID using `collect` or any step that pauses for user input inside the `do:` block"

**With new architecture**: This remains true. While loops should only contain:
- `action_node` (API calls)
- `set_node` (calculations)
- `say_node` (messages)
- `branch_node` (conditions)

**NOT**:
- `collect_node` (needs interrupt)
- `confirm_node` (needs interrupt)

**Workaround** (already documented): Use `branch + jump_to` for interactive loops.

---

## 12. Migration Phases

### Phase 1: State Infrastructure
- [ ] Add `_need_input`, `_pending_prompt`, `_executed_steps` to `DialogueState`
- [ ] Add `executed_steps` to `FlowDelta`
- [ ] Update `create_empty_dialogue_state()`
- [ ] Add `subgraphs` and `nlu_service` to `RuntimeContext`

### Phase 2: Node Idempotency
- [ ] `say_node`: Add idempotency check with `_executed_steps`
- [ ] `action_node`: Add idempotency check with `_executed_steps`
- [ ] `set_node`: Add idempotency check (optional)
- [ ] `collect_node`: Remove `interrupt()`, return `_need_input` flag
- [ ] `confirm_node`: Remove `interrupt()`, return `_need_input` flag
- [ ] `confirm_handlers.py`: Remove `handle_interrupt()` methods

### Phase 3: Orchestrator
- [ ] Create `execute_flow_node` in `dm/nodes/execute_flow.py`
- [ ] Modify `build_orchestrator()` to return `(graph, subgraphs)` tuple
- [ ] Update `RuntimeLoop.initialize()` to handle tuple
- [ ] Update `RuntimeLoop._create_context()` to include subgraphs
- [ ] Delete old `execute_node` (or rename)
- [ ] Delete `request_input.py`

### Phase 4: Flow Manager
- [ ] Add `get_active_flow_id()` method
- [ ] Update `pop_flow()` to clean up `_executed_steps`

### Phase 5: Verification
- [ ] `uv run pytest tests/unit/ -v`
- [ ] `uv run pytest tests/integration/ -v`
- [ ] Manual: banking transfer with digression
- [ ] Manual: nested flows
- [ ] Profile: 10+ step flow latency

---

## 13. SOLID Compliance Summary

| Principle | Rating | Evidence |
|-----------|--------|----------|
| **SRP** | ✅ | Each node: one job. `execute_flow_node`: orchestration only. |
| **OCP** | ✅ | New step types don't require orchestrator changes |
| **LSP** | ✅ | All nodes: `(state, runtime) → dict` |
| **ISP** | ✅ | Nodes use only needed RuntimeContext fields |
| **DIP** | ✅ | Depends on interfaces: `subgraph.ainvoke()`, `nlu.process_message()` |
| **DRY** | ✅ | Interrupt in ONE place, NLU in ONE place, idempotency helper reusable |
