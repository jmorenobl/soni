# Handling Multiple Slots in One Message

## Overview

Soni Framework supports processing multiple slots provided in a single user message (e.g., "I want to fly from New York to Los Angeles"). This is implemented using an iterative step advancement pattern that automatically advances through completed steps.

## Pattern: Iterative Step Advancement

### When to Use

Use `advance_through_completed_steps` when:
- Multiple slots are extracted from a single NLU result
- You need to automatically advance through completed steps
- After saving slots in `validate_slot_node` or `handle_intent_change_node`

### How It Works

1. **Process all slots** using `_process_all_slots` helper
2. **Save slots to state** via `flow_slots[flow_id]`
3. **Call `advance_through_completed_steps`** to iterate through completed steps
4. **Stop at first incomplete step** or when flow completes

### Example Implementation

```python
# In validate_slot_node or handle_intent_change_node

# 1. Process all slots from NLU result
flow_slots = await _process_all_slots(slots, state, active_ctx, normalizer)
state["flow_slots"] = flow_slots

# 2. Advance through completed steps
updates = step_manager.advance_through_completed_steps(state, context)
updates["flow_slots"] = flow_slots

return updates
```

## Helper Functions

### _process_all_slots

Processes and normalizes all slots from NLU result. Handles different formats:

```python
# Dict format
slots = [{"name": "origin", "value": "New York"}]

# SlotValue model format
from soni.du.models import SlotValue
slots = [SlotValue(name="origin", value="New York", confidence=0.9)]

# String format (uses waiting_for_slot as name)
slots = ["New York"]  # Requires waiting_for_slot in state

flow_slots = await _process_all_slots(slots, state, active_ctx, normalizer)
```

### _detect_correction_or_modification

Detects if message is a correction/modification:

```python
is_correction = _detect_correction_or_modification(slots, message_type)

if is_correction:
    return _handle_correction_flow(state, runtime, flow_slots, previous_step)
```

### _handle_correction_flow

Handles correction flow, restoring the correct step:

```python
# Automatically determines target step based on:
# - Previous step
# - All slots filled status
# - Conversation state

return _handle_correction_flow(state, runtime, flow_slots, previous_step)
```

## Integration Points

### validate_slot_node

```python
async def validate_slot_node(state: DialogueState, runtime: Any) -> dict:
    # ... fallback logic ...

    # Process all slots
    flow_slots = await _process_all_slots(slots, state, active_ctx, normalizer)
    state["flow_slots"] = flow_slots

    # Detect corrections
    is_correction = _detect_correction_or_modification(slots, message_type)

    if is_correction:
        return _handle_correction_flow(state, runtime, flow_slots, previous_step)

    # Normal flow: advance through completed steps
    updates = step_manager.advance_through_completed_steps(state, runtime.context)
    updates["flow_slots"] = flow_slots
    return updates
```

### handle_intent_change_node

```python
async def handle_intent_change_node(state: DialogueState, runtime: Any) -> dict:
    # ... flow activation logic ...

    # Extract and save slots
    extracted_slots = _extract_slots_from_nlu(nlu_result)
    if extracted_slots:
        current_slots = get_all_slots(state)
        current_slots.update(extracted_slots)
        set_all_slots(state, current_slots)

    # Advance through completed steps
    updates = step_manager.advance_through_completed_steps(state, runtime.context)
    updates["flow_stack"] = state["flow_stack"]
    updates["flow_slots"] = state["flow_slots"]

    return updates
```

## Safety Mechanisms

### Max Iterations Limit

`advance_through_completed_steps` has a safety limit of 20 iterations to prevent infinite loops:

```python
max_iterations = 20  # Safety limit

while iterations < max_iterations:
    # ... advancement logic ...

# If limit reached, returns error state
if iterations >= max_iterations:
    return {"conversation_state": "error"}
```

### Step Completion Check

Each step is verified before advancement:

```python
is_complete = step_manager.is_step_complete(state, current_step_config, context)

if not is_complete:
    # Stop here - found incomplete step
    return updates
```

## Testing

### Unit Tests

Test `advance_through_completed_steps` with:
- Single step advancement
- Multiple steps advancement
- Flow completion
- Max iterations safety limit

### Integration Tests

Test complete scenarios:
- Multiple slots in one message
- All slots at once
- Mix of new slots and corrections

See `tests/integration/test_all_scenarios.py` for examples.

## Best Practices

1. **Always use `_process_all_slots`** for processing multiple slots
2. **Use `advance_through_completed_steps`** instead of manual step advancement
3. **Handle corrections separately** using `_handle_correction_flow`
4. **Preserve existing fallback logic** when refactoring
5. **Test with real NLU** to verify slot extraction works correctly

## References

- `docs/design/03-components.md` - FlowStepManager documentation
- `docs/design/07-flow-management.md` - Flow management patterns
- `docs/analysis/SOLUCION_MULTIPLES_SLOTS.md` - Solution design
- `src/soni/flow/step_manager.py` - Implementation
- `src/soni/dm/nodes/validate_slot.py` - Helper functions
