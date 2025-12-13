## Task: 106 - Fix Debug Script Display

**ID de tarea:** 106
**Prioridad:** MEDIA
**Duración estimada:** 30 minutos

### Objetivo

Fix debug script to show `current_step` from correct location:
- Script currently shows `state.get("current_step")` which is always `None`
- Should show `state["flow_stack"][-1]["current_step"]`
- The `current_step` IS being updated correctly, just displayed wrong

### Contexto

After implementing Task 101 fix, scenario 1 completes successfully ✅, but the debug script shows incorrect `current_step`:

- Script shows: `state.get("current_step")` which is always `None`
- Should show: `state["flow_stack"][-1]["current_step"]`
- The `current_step` IS being updated correctly, just displayed wrong

**Note:** The NLU command issue is handled separately in `task-106-fix-nlu-command-field.md`.

### Problema: Debug Script - current_step Display

**Archivo a modificar:** `scripts/debug_scenarios.py`

**Current code (line 273):**
```python
print(f"  Current Step: {state.get('current_step', 'None')}")
```

**Fixed code:**
```python
# Get current_step from active flow context
flow_stack = state.get("flow_stack", [])
current_step = flow_stack[-1].get("current_step") if flow_stack else None
print(f"  Current Step: {current_step}")
```

**Additional improvements:**
```python
# Show more flow context details
if flow_stack:
    active_flow = flow_stack[-1]
    print(f"  Flow ID: {active_flow.get('flow_id')}")
    print(f"  Flow State: {active_flow.get('flow_state')}")
    print(f"  Current Step: {active_flow.get('current_step')}")
else:
    print(f"  Flow ID: None")
    print(f"  Flow State: N/A")
    print(f"  Current Step: None")
```

### Implementación

**File:** `scripts/debug_scenarios.py`

**Line 265-278, replace with:**

```python
state = state_from_dict(snapshot.values, allow_partial=True)
current_flow = get_current_flow(state)
slots = get_all_slots(state)
stack_depth = len(state.get("flow_stack", []))

# Get current_step from flow_stack
flow_stack = state.get("flow_stack", [])
flow_id = None
flow_state = None
current_step = None
if flow_stack:
    active_ctx = flow_stack[-1]
    flow_id = active_ctx.get("flow_id")
    flow_state = active_ctx.get("flow_state")
    current_step = active_ctx.get("current_step")

# Show actual state
print(f"\n{C.Y}State:{C.E}")
print(f"  Flow: {C.BOLD}{current_flow}{C.E} (stack depth: {stack_depth})")
print(f"  Flow ID: {flow_id}")
print(f"  Flow State: {flow_state}")
print(f"  Current Step: {current_step}")
print(f"  Conversation State: {state.get('conversation_state', 'N/A')}")
print(f"  Waiting for Slot: {state.get('waiting_for_slot', 'None')}")
print(f"  Current Prompted Slot: {state.get('current_prompted_slot', 'None')}")
print(f"  All Slots Filled: {state.get('all_slots_filled', False)}")
print(f"  Slots: {json.dumps(slots, indent=2) if slots else '{}'}")
```


### Criterios de Éxito

- [ ] Debug script shows correct `current_step` from flow_stack
- [ ] Debug output is more informative (shows flow_id, flow_state)
- [ ] Scenario 1 still passes
- [ ] All scenarios still pass

### Validación Manual

```bash
# 1. Run debug script
uv run python scripts/debug_scenarios.py 1

# Expected output:
#   Turn 2: Provide origin
#   User: "Madrid"
#   State:
#     Flow ID: book_flight_abc123
#     Flow State: active
#     Current Step: collect_destination  ← Should show actual step, not None

# 2. Verify all scenarios pass
uv run python scripts/debug_scenarios.py
```

### Referencias

- Debug script: `scripts/debug_scenarios.py`
- Related task: `task-106-fix-nlu-command-field.md` (NLU command fix)
