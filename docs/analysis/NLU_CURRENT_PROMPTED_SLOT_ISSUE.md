# NLU Issue: current_prompted_slot Not Being Used Correctly

## Problem

When the system is waiting for a specific slot (e.g., `origin`) and the user provides a simple value (e.g., "Madrid"), the NLU sometimes extracts it as a different slot (e.g., `destination: Madrid` instead of `origin: Madrid`).

## Root Cause

The NLU module (`SoniDU`) is not optimized with training examples that demonstrate how to use `current_prompted_slot` correctly. The context is being passed correctly (verified in `src/soni/dm/nodes/understand.py:182`), but the LLM hasn't learned to prioritize `current_prompted_slot` when extracting slots.

## Verification

The context is correctly passed to NLU:

```python
# src/soni/dm/nodes/understand.py:182
dialogue_context = DialogueContext(
    current_slots=(...),
    available_actions=available_actions,
    available_flows=available_flows,
    current_flow=current_flow_name,
    expected_slots=expected_slots,
    current_prompted_slot=waiting_for_slot,  # ✅ Correctly passed
)
```

## Solution

**DO NOT** add workarounds in post-processing. The correct solution is to optimize the NLU with training examples that include `current_prompted_slot`.

### Required Training Examples

Add examples like this to the training dataset:

```python
dspy.Example(
    user_message="Madrid",
    history=dspy.History(messages=[
        {"role": "assistant", "content": "Which city are you departing from?"}
    ]),
    context=DialogueContext(
        current_slots={},
        available_actions=["book_flight"],
        available_flows=["book_flight"],
        current_flow="book_flight",
        expected_slots=["origin", "destination", "departure_date"],
        current_prompted_slot="origin"  # ✅ Key field
    ),
    current_datetime="2024-12-08T10:00:00",
    result=NLUOutput(
        message_type=MessageType.SLOT_VALUE,
        command="book_flight",
        slots=[
            SlotValue(name="origin", value="Madrid", confidence=0.95)  # ✅ Correct slot
        ],
        confidence=0.95
    )
).with_inputs("user_message", "history", "context", "current_datetime")
```

### Optimization Steps

1. **Collect training examples** that include `current_prompted_slot` scenarios:
   - Simple slot values when `current_prompted_slot` is set
   - Multiple slots when `current_prompted_slot` is set (should prioritize the prompted slot)
   - Corrections when `current_prompted_slot` is set

2. **Run optimization**:
   ```bash
   uv run soni optimize --trainset training_data.json --optimizer MIPROv2 --trials 50
   ```

3. **Validate** that Scenario 1 passes after optimization

## Why Not Workarounds?

- **DSPy philosophy**: Prompts are optimized automatically, not manually engineered
- **Maintainability**: Workarounds add complexity and technical debt
- **Scalability**: Optimization learns patterns that work across all scenarios
- **Correctness**: The LLM should learn the correct behavior, not be patched

## Related Files

- `src/soni/du/signatures.py` - Signature definition (minimal, informational)
- `src/soni/du/modules.py` - SoniDU module (no workarounds)
- `src/soni/du/optimizers.py` - Optimization utilities
- `src/soni/cli/optimize.py` - CLI for optimization
- `docs/design/09-dspy-optimization.md` - Optimization guide

## Status

- ✅ Context correctly passed to NLU
- ❌ NLU not optimized with `current_prompted_slot` examples
- 📋 TODO: Create training examples and optimize
