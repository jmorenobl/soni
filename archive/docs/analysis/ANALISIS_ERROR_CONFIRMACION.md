# Analysis: Confirmation Step Infinite Loop Error

**Date**: 2025-12-09
**Scenario**: Simple: Complete Flight Booking (debug_scenarios.py #1)
**Error**: GraphRecursionError - Recursion limit of 25 reached
**Status**: Critical Bug - Breaks confirmation flow

---

## Executive Summary

Adding a confirmation step (`type: confirm`) to the flight booking flow causes an infinite loop when the user responds with confirmation (e.g., "Yes, please confirm"). The system enters a recursion cycle between `understand` → `handle_confirmation` → `understand`, hitting LangGraph's recursion limit of 25.

**Root Cause**: The NLU module does not extract a `confirmation_value` field, but the `handle_confirmation_node` requires it to determine if the user confirmed (yes/no). This causes the confirmation handler to always fail and re-prompt, creating an infinite loop.

---

## Error Manifestation

### Turn 4: Action Execution Issue
```
User: "Tomorrow"
State:
  Current Step: ask_confirmation
  Conversation State: idle
  All Slots Filled: True

WARNING: No confirmation, booking_ref, or action_result found, using default response
Agent: "How can I help you?"
```

**Issue 1**: After executing `search_flights` action, the system should display the confirmation message defined in the `ask_confirmation` step, but instead shows default response "How can I help you?".

### Turn 5: Infinite Loop
```
User: "Yes, please confirm"

WARNING: Confirmation value unclear: None, asking again
WARNING: Confirmation value unclear: None, asking again
...
(repeated 12 times)

ERROR: GraphRecursionError: Recursion limit of 25 reached
```

**Issue 2**: When user provides confirmation, the system enters infinite loop because `confirmation_value` is always `None`.

---

## Technical Analysis

### 1. Missing NLU Field: `confirmation_value`

**Location**: `src/soni/du/models.py:53-63`

```python
class NLUOutput(BaseModel):
    """Structured NLU output."""

    message_type: MessageType = Field(description="Type of user message")
    command: str | None = Field(...)
    slots: list[SlotValue] = Field(default_factory=list, ...)
    confidence: float = Field(ge=0.0, le=1.0, ...)
    # ❌ NO confirmation_value FIELD
```

**Expected**: When `message_type = MessageType.CONFIRMATION`, the NLU should extract a boolean `confirmation_value` indicating whether the user confirmed (True), denied (False), or was unclear (None).

**Actual**: No such field exists in the model.

### 2. Confirmation Handler Expects Missing Field

**Location**: `src/soni/dm/nodes/handle_confirmation.py:49-75`

```python
async def handle_confirmation_node(state: DialogueState, runtime: Any) -> dict:
    nlu_result = state.get("nlu_result") or {}
    message_type = nlu_result.get("message_type") if nlu_result else None

    # Get confirmation value from NLU result
    confirmation_value = nlu_result.get("confirmation_value") if nlu_result else None
    # ⚠️ ALWAYS None because field doesn't exist in NLUOutput

    if confirmation_value is True:
        return {"conversation_state": "ready_for_action", ...}
    elif confirmation_value is False:
        return {"conversation_state": "understanding", ...}
    else:
        # ⚠️ ALWAYS hits this branch
        logger.warning(f"Confirmation value unclear: {confirmation_value}, asking again")
        return {
            "conversation_state": "confirming",
            "last_response": "I didn't understand. Is this information correct? (yes/no)",
        }
```

**Problem**: Since `confirmation_value` is always `None`, the handler always returns `conversation_state = "confirming"`, which triggers the infinite loop.

### 3. Routing Creates Infinite Loop

**Location**: `src/soni/dm/routing.py:568-588`

```python
def route_after_confirmation(state: DialogueStateType) -> str:
    conv_state = state.get("conversation_state")

    if conv_state == "ready_for_action":
        return "execute_action"
    elif conv_state == "confirming":
        # ⚠️ Routes back to understand
        return "understand"
    else:
        return "understand"
```

**Flow Path (Infinite Loop)**:
```
1. handle_confirmation (returns conv_state="confirming")
   ↓
2. route_after_confirmation (sees "confirming", routes to "understand")
   ↓
3. understand (NLU detects message_type="confirmation")
   ↓
4. route_after_understand (routes to "handle_confirmation")
   ↓
5. handle_confirmation (confirmation_value=None, returns "confirming")
   ↓
6. LOOP TO STEP 2
```

This cycles 25 times until hitting the recursion limit.

### 4. Missing Confirmation Message Display

**Location**: `src/soni/dm/nodes/generate_response.py:11-74`

After the `search_flights` action completes in Turn 4, the system should:
1. Advance to the `ask_confirmation` step
2. Display the confirmation message from the step config
3. Set `conversation_state = "ready_for_confirmation"`

**Actual Behavior**:
- Current Step is correctly set to `ask_confirmation`
- But `conversation_state` is set to `idle` instead of `ready_for_confirmation`
- `generate_response_node` is called but finds no confirmation/booking_ref/action_result
- Shows default "How can I help you?" response

**Root Cause**: The flow advancement logic in `step_manager.advance_through_completed_steps` correctly identifies that the next step is a `confirm` type and sets `conversation_state = "ready_for_confirmation"`, but somewhere in the routing this gets lost or overridden.

---

## Configuration Context

### YAML Configuration
**File**: `examples/flight_booking/soni.yaml:119-131`

```yaml
# Step 5: Ask for confirmation
- step: ask_confirmation
  type: confirm
  message: |
    I found flights for your trip:
    - From: {origin}
    - To: {destination}
    - Date: {departure_date}
    - Price: ${price}

    Would you like to confirm this booking?

# Step 6: Confirm booking
- step: confirm_booking
  type: action
  call: confirm_flight_booking
  map_outputs:
    booking_ref: booking_ref
    confirmation: confirmation
```

### Graph Flow for Confirmation

**Designed Flow** (according to builder.py):
```
execute_action (search_flights)
  ↓ route_after_action (sees conversation_state)
  ↓ (should be "ready_for_confirmation")
confirm_action (displays confirmation message, uses interrupt())
  ↓ edge to understand
understand (user says "yes")
  ↓ route_after_understand (detects message_type="confirmation")
handle_confirmation (extracts confirmation_value)
  ↓ route_after_confirmation (user confirmed)
execute_action (confirm_booking)
```

**Actual Flow**:
```
execute_action (search_flights)
  ↓ route_after_action (conversation_state="idle"???)
generate_response (shows default message)
  ↓ END

[Next Turn]
understand (user says "yes")
  ↓ detects message_type="confirmation"
handle_confirmation (confirmation_value=None)
  ↓ returns conversation_state="confirming"
  ↓ route_after_confirmation (routes to "understand")
  ↓ INFINITE LOOP
```

---

## Step Manager Analysis

### Confirmation Step Handling

**Location**: `src/soni/flow/step_manager.py:186-187, 222-224, 411-414`

```python
def advance_to_next_step(self, state, context) -> dict[str, Any]:
    # Line 186-187:
    elif step_type == "confirm":
        conversation_state = "ready_for_confirmation"

def is_step_complete(self, state, step_config, context) -> bool:
    # Line 222-224:
    # Action and confirm steps are never "pre-completed" - they execute when reached
    if step_config.type in ("action", "confirm"):
        return False

def advance_through_completed_steps(self, state, context) -> dict[str, Any]:
    # Line 411-414:
    elif step_type == "confirm":
        updates["conversation_state"] = "ready_for_confirmation"
        updates["all_slots_filled"] = True
        updates["waiting_for_slot"] = None
```

**Expected Behavior**: When advancing to a `confirm` step, the system should:
1. Set `conversation_state = "ready_for_confirmation"`
2. Route to `confirm_action` node
3. Display confirmation message
4. Wait for user response

**Issue**: The conversation_state is being set correctly in the step manager, but somewhere between step advancement and routing, it gets lost or overridden to "idle".

---

## Solution Requirements

### 1. Add `confirmation_value` to NLU Output (CRITICAL)

**File**: `src/soni/du/models.py`

```python
class NLUOutput(BaseModel):
    """Structured NLU output."""

    message_type: MessageType
    command: str | None = None
    slots: list[SlotValue] = Field(default_factory=list)
    confidence: float

    # ✅ ADD THIS FIELD
    confirmation_value: bool | None = Field(
        default=None,
        description="For CONFIRMATION message_type: True=yes, False=no, None=unclear"
    )
```

### 2. Update NLU Module to Extract Confirmation Value

**File**: `src/soni/du/modules.py` (or relevant NLU provider)

The NLU should:
- Detect when `message_type = MessageType.CONFIRMATION`
- Extract `confirmation_value`:
  - `True` for "yes", "confirm", "correct", "that's right", etc.
  - `False` for "no", "not correct", "wrong", etc.
  - `None` for unclear responses

### 3. Fix Confirmation Message Display (Turn 4 Issue)

**Investigation Needed**: Trace why after `execute_action` (search_flights), the system:
- Correctly sets current_step to "ask_confirmation"
- But sets conversation_state to "idle" instead of routing to "confirm_action"

**Potential Locations**:
- `src/soni/dm/nodes/execute_action.py` - Check what it returns
- `src/soni/dm/routing.py:route_after_action` - Check routing logic
- `src/soni/dm/nodes/collect_next_slot.py` - If it's called after action

### 4. Prevent Infinite Loop (Defensive Programming)

Even with the fix, add safety check in `handle_confirmation_node`:

```python
async def handle_confirmation_node(state, runtime) -> dict:
    # Track attempts to prevent infinite loop
    metadata = state.get("metadata", {})
    confirmation_attempts = metadata.get("_confirmation_attempts", 0)

    if confirmation_attempts >= 3:
        logger.error("Too many confirmation attempts, aborting")
        return {
            "conversation_state": "error",
            "last_response": "I'm having trouble understanding. Let's start over."
        }

    confirmation_value = nlu_result.get("confirmation_value")

    if confirmation_value is None:
        metadata["_confirmation_attempts"] = confirmation_attempts + 1
        return {
            "conversation_state": "confirming",
            "metadata": metadata,
            "last_response": "I didn't understand. Is this information correct? (yes/no)",
        }
```

---

## Testing Checklist

After implementing fixes, verify:

1. ✅ NLU extracts `confirmation_value` correctly:
   - "yes" → `True`
   - "no" → `False`
   - "maybe" → `None`

2. ✅ Turn 4: After action execution, confirmation message is displayed

3. ✅ Turn 5: User confirmation is processed without infinite loop

4. ✅ User can deny confirmation and modify slots

5. ✅ Unclear responses are handled gracefully (max 3 attempts)

---

## Related Files

### Core Files to Modify
- `src/soni/du/models.py` - Add `confirmation_value` field
- `src/soni/du/modules.py` - Extract confirmation value in NLU
- `src/soni/dm/nodes/handle_confirmation.py` - Add safety check (optional)

### Files to Investigate
- `src/soni/dm/nodes/execute_action.py` - Turn 4 issue
- `src/soni/dm/routing.py:route_after_action` - Turn 4 routing
- `src/soni/dm/nodes/collect_next_slot.py` - Flow advancement

### Related Design Docs
- `docs/design/04-state-machine.md` - Conversation states
- `docs/design/05-message-flow.md` - Message flow patterns
- `docs/design/06-nlu-system.md` - NLU architecture
- `docs/design/07-flow-management.md` - Flow step management

---

## Impact Assessment

**Severity**: CRITICAL
**Impact**: Breaks all flows with confirmation steps
**Workaround**: None - confirmation steps are completely unusable
**Priority**: P0 - Must fix before any production use

---

## Implementation Order

1. **First** (Immediate): Add `confirmation_value` to `NLUOutput` model
2. **Second**: Update NLU module to extract confirmation value
3. **Third**: Investigate and fix Turn 4 confirmation message display
4. **Fourth**: Add defensive checks to prevent infinite loops
5. **Fifth**: Add comprehensive tests for confirmation flow

---

## Additional Notes

### Why This Wasn't Caught Earlier

The confirmation step type (`type: confirm`) appears to be a relatively recent addition or was not fully tested end-to-end. The infrastructure exists (nodes, routing), but the critical piece (NLU extraction of confirmation value) was never implemented.

### Design vs Implementation Gap

This is another case of design-implementation mismatch:
- **Design**: Assumes NLU can extract yes/no confirmation
- **Implementation**: NLU only extracts `message_type` but not `confirmation_value`

This should be added to the backlog of design compliance issues.

---

**End of Analysis**
