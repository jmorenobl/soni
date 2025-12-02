# State Machine Design

**Document Version**: 1.0
**Last Updated**: 2025-12-02
**Status**: ✅ Stable

> **Note**: This document represents the final, stable design for the state machine. For implementation details and decision rationale, see [20-consolidated-design-decisions.md](20-consolidated-design-decisions.md).

## Table of Contents

1. [Overview](#overview)
2. [DialogueState Schema](#dialoguestate-schema)
3. [Conversation States](#conversation-states)
4. [State Transitions](#state-transitions)
5. [State Persistence](#state-persistence)
6. [Examples](#examples)

---

## Overview

The Soni Framework implements an **explicit state machine** to track conversation progress. This is a fundamental change from the original design, which had implicit state tracking through graph execution.

### Why an Explicit State Machine?

**Problems Solved**:
1. ❌ **OLD**: System didn't know if it was waiting for a slot, executing an action, or processing an intent
2. ❌ **OLD**: Every message triggered full NLU, even when just collecting a simple value
3. ❌ **OLD**: Debugging was difficult (no clear "current state" to inspect)

**Benefits of Explicit States**:
1. ✅ **Context-aware routing**: Skip NLU when we know what we're waiting for
2. ✅ **Efficient execution**: Resume from current position, not from START
3. ✅ **Better debugging**: Inspect `conversation_state` to understand system status
4. ✅ **Error recovery**: Know where we were when error occurred

---

## DialogueState Schema

### Complete Schema

```python
from enum import Enum
from typing import Any, TypedDict

class ConversationState(str, Enum):
    """
    Explicit conversation states for context-aware processing.
    """
    IDLE = "idle"
    """No active flow, waiting for user to start a task"""

    UNDERSTANDING = "understanding"
    """Processing user intent via NLU"""

    WAITING_FOR_SLOT = "waiting_for_slot"
    """Waiting for user to provide a specific slot value"""

    VALIDATING_SLOT = "validating_slot"
    """Validating a slot value against validators"""

    EXECUTING_ACTION = "executing_action"
    """Running an external action (API call, DB query, etc.)"""

    CONFIRMING = "confirming"
    """Asking user to confirm before proceeding"""

    COMPLETED = "completed"
    """Flow completed successfully"""

    ERROR = "error"
    """Error occurred, system is in error recovery mode"""


class DialogueState(TypedDict):
    """
    Complete dialogue state schema.

    This schema combines:
    - Original fields (messages, slots, current_flow)
    - NEW fields (conversation_state, current_step, waiting_for_slot)
    - Metadata fields (timestamps, counters, trace)
    """

    # ===== Core State Fields =====

    messages: list[dict[str, str]]
    """
    Complete message history for this conversation.
    Each message: {"role": "user" | "assistant", "content": str, "timestamp": float}
    """

    slots: dict[str, Any]
    """
    Collected slot values.
    Keys are slot names, values are normalized slot values.
    Example: {"origin": "New York", "destination": "Los Angeles", "date": "2025-12-10"}
    """

    current_flow: str
    """
    Currently active flow name.
    Examples: "book_flight", "cancel_booking", "none"
    """

    # ===== NEW: Explicit State Tracking =====

    conversation_state: ConversationState
    """
    Current conversation state (NEW).
    Determines how the next message will be processed.
    """

    current_step: str | None
    """
    Current step in the flow (NEW).
    Used to resume execution from the correct position.
    None if no active flow or flow hasn't started yet.
    Examples: "collect_origin", "search_flights", "confirm_booking"
    """

    waiting_for_slot: str | None
    """
    Name of slot we're waiting for (NEW).
    Set when conversation_state == WAITING_FOR_SLOT.
    Enables direct message-to-slot mapping without NLU.
    Examples: "origin", "destination", "departure_date"
    """

    # ===== Metadata Fields =====

    turn_count: int
    """Number of turns in this conversation"""

    last_response: str
    """Last response sent to user (for reference)"""

    last_nlu_call: float | None
    """
    Timestamp of last NLU call (NEW).
    Used for caching and debugging.
    None if NLU hasn't been called yet.
    """

    trace: list[dict[str, Any]]
    """
    Audit trail of events.
    Each event: {"event": str, "timestamp": float, "data": dict}
    """

    metadata: dict[str, Any]
    """
    Additional metadata for custom extensions.
    Framework doesn't use this, available for user code.
    """
```

### Field-by-Field Explanation

#### `conversation_state` (NEW, CRITICAL)

**Purpose**: Tells the system "what are we doing right now?"

**Values**:
- `IDLE`: No active conversation, user can start any flow
- `UNDERSTANDING`: Processing user intent via NLU
- `WAITING_FOR_SLOT`: System asked a question, waiting for answer
- `VALIDATING_SLOT`: Checking if provided value is valid
- `EXECUTING_ACTION`: Running an external action
- `CONFIRMING`: Asking user to confirm before action
- `COMPLETED`: Flow finished successfully
- `ERROR`: Something went wrong

**Usage**:
```python
# In message routing
if state.conversation_state == ConversationState.WAITING_FOR_SLOT:
    # Direct mapping: user is answering our question
    return await self._map_message_to_slot(msg, state.waiting_for_slot)
elif state.conversation_state == ConversationState.IDLE:
    # Call NLU: user starting new task
    return await self._understand_intent(msg, state)
```

#### `current_step` (NEW, CRITICAL)

**Purpose**: Tracks position in the flow execution.

**Usage**:
```python
# Resume execution from current step instead of START
if state.current_step:
    return await self.graph.ainvoke_from_node(state, state.current_step)
```

**Example Values**:
- `"collect_origin"`: Currently collecting origin slot
- `"search_flights"`: About to execute search action
- `"confirm_booking"`: Waiting for confirmation
- `None`: No active step

#### `waiting_for_slot` (NEW, PERFORMANCE)

**Purpose**: Enables direct message-to-slot mapping, skipping NLU.

**Example**:
```python
# System asks: "Where would you like to fly from?"
state.waiting_for_slot = "origin"
state.conversation_state = ConversationState.WAITING_FOR_SLOT

# User responds: "New York"
# System maps directly: slots["origin"] = "New York"
# NO NLU CALL NEEDED!
```

#### `last_nlu_call` (NEW, OPTIMIZATION)

**Purpose**: Timestamp for NLU call tracking and caching.

**Usage**:
```python
# Check if we recently called NLU for this message
if state.last_nlu_call and (time.time() - state.last_nlu_call) < 1.0:
    # Skip NLU, use cached result
    return cached_nlu_result
```

---

## Conversation States

### State Diagram

```
                    ┌─────────────────┐
                    │      IDLE       │
                    │  (No active     │
                    │   flow)         │
                    └────────┬────────┘
                             │
                    User sends message
                             │
                             ▼
                    ┌─────────────────┐
                    │  UNDERSTANDING  │◄─────┐
                    │  (Calling NLU)  │      │
                    └────────┬────────┘      │
                             │                │
                    NLU returns result        │
                             │                │
                 ┌───────────┴──────────┐    │
                 │                      │    │
         Intent detected        Need slot     │
                 │                      │    │
                 ▼                      ▼    │
        ┌────────────────┐    ┌──────────────────┐
        │ EXECUTING_     │    │ WAITING_FOR_     │
        │    ACTION      │    │     SLOT         │
        └───────┬────────┘    └────────┬─────────┘
                │                      │
         Action completes      User provides value
                │                      │
                │                      ▼
                │             ┌──────────────────┐
                │             │  VALIDATING_     │
                │             │     SLOT         │
                │             └────────┬─────────┘
                │                      │
                │              ┌───────┴────────┐
                │              │                │
                │         Valid          Invalid (retry)
                │              │                │
                │              │                │
                └──────────────┤                └──────┐
                               │                       │
                   All slots collected          Need more slots
                               │                       │
                               ▼                       ▼
                      ┌────────────────┐     ┌──────────────────┐
                      │  CONFIRMING    │     │ WAITING_FOR_     │
                      │ (Optional)     │     │     SLOT         │
                      └───────┬────────┘     └──────────────────┘
                              │
                      User confirms
                              │
                              ▼
                     ┌────────────────┐
                     │   COMPLETED    │
                     └────────────────┘


                     Error at any stage
                              │
                              ▼
                     ┌────────────────┐
                     │     ERROR      │
                     └────────────────┘
```

### State Descriptions

#### IDLE

**When**: No active flow, user hasn't started a task yet.

**What system does**:
- Listen for flow-triggering intents
- Show help or available options
- Allow starting any configured flow

**Typical user messages**:
- "I want to book a flight"
- "Help"
- "What can you do?"

**Next states**:
- `UNDERSTANDING` (when user sends a message)

---

#### UNDERSTANDING

**When**: System is calling NLU to understand user intent.

**What system does**:
- Call NLU with current context
- Extract intent and slots
- Activate flow if intent matches
- Update slots with extracted values

**Typical duration**: 200-500ms (LLM call latency)

**Next states**:
- `WAITING_FOR_SLOT` (if slot needed)
- `EXECUTING_ACTION` (if all slots collected)
- `IDLE` (if no intent detected)
- `ERROR` (if NLU fails)

---

#### WAITING_FOR_SLOT

**When**: System needs a specific slot value from user.

**What system does**:
- Show prompt asking for the slot
- Wait for user response
- On next turn: map message to slot (direct, no NLU)

**State data**:
```python
state.conversation_state = ConversationState.WAITING_FOR_SLOT
state.waiting_for_slot = "origin"  # Which slot we're waiting for
state.current_step = "collect_origin"  # Where we are in the flow
```

**Typical user messages**:
- "New York" (simple value)
- "I want to leave from Boston" (contains slot value)

**Next states**:
- `VALIDATING_SLOT` (validate provided value)
- `UNDERSTANDING` (if user changes intent, e.g., "cancel")

**Optimization**:
- If message looks like a simple value (no intent markers), skip NLU
- Map directly: `slots[waiting_for_slot] = normalize(user_message)`

---

#### VALIDATING_SLOT

**When**: System is validating a provided slot value.

**What system does**:
- Run validators (format, business rules)
- If valid: continue to next step
- If invalid: re-prompt user

**Example validators**:
- `city_name`: Check format, maybe verify against city database
- `future_date_only`: Ensure date is in the future
- `booking_ref_format`: Validate booking reference format

**Next states**:
- `WAITING_FOR_SLOT` (if validation fails, retry)
- `UNDERSTANDING` (if all slots collected, need to decide next action)
- `EXECUTING_ACTION` (if ready to execute action)

---

#### EXECUTING_ACTION

**When**: System is running an external action (API call, DB query, etc.).

**What system does**:
- Call action handler with collected slots
- Wait for action to complete
- Update state with action results

**Typical duration**: 100ms - 5s (depends on external API)

**State data**:
```python
state.conversation_state = ConversationState.EXECUTING_ACTION
state.current_step = "search_flights"  # Which action is running
```

**Next states**:
- `CONFIRMING` (if action needs confirmation)
- `COMPLETED` (if action finishes flow)
- `WAITING_FOR_SLOT` (if action revealed missing slots)
- `ERROR` (if action fails)

---

#### CONFIRMING

**When**: System needs user confirmation before proceeding.

**What system does**:
- Show summary of what will happen
- Ask user to confirm (yes/no)
- Wait for confirmation

**Typical prompts**:
- "I found 3 flights. Would you like to book flight #1 for $299?"
- "This will cancel your booking BK-12345. Are you sure?"

**Next states**:
- `EXECUTING_ACTION` (if user confirms)
- `COMPLETED` (if user cancels)
- `UNDERSTANDING` (if user changes request)

---

#### COMPLETED

**When**: Flow finished successfully.

**What system does**:
- Show completion message
- Reset to IDLE for next task
- Save audit log

**State cleanup**:
```python
state.conversation_state = ConversationState.COMPLETED
state.current_flow = "none"
state.current_step = None
state.waiting_for_slot = None
# Keep slots for reference, but mark flow as done
```

**Next states**:
- `IDLE` (ready for next task)

---

#### ERROR

**When**: Something went wrong during processing.

**What system does**:
- Log error details
- Show user-friendly error message
- Offer recovery options (retry, cancel, help)

**Error types**:
- NLU failure
- Validation failure
- Action execution failure
- Unexpected exception

**Next states**:
- `UNDERSTANDING` (if user retries)
- `IDLE` (if user cancels)

---

## State Transitions

### Transition Rules

#### Rule 1: IDLE → UNDERSTANDING

**Trigger**: User sends any message when no active flow.

**Conditions**: None (always allowed).

**State updates**:
```python
state.conversation_state = ConversationState.UNDERSTANDING
# Call NLU to understand intent
```

---

#### Rule 2: UNDERSTANDING → WAITING_FOR_SLOT

**Trigger**: NLU detects intent but slot is missing.

**Conditions**:
- Flow activated (current_flow != "none")
- At least one required slot is empty

**State updates**:
```python
state.conversation_state = ConversationState.WAITING_FOR_SLOT
state.current_step = f"collect_{slot_name}"
state.waiting_for_slot = slot_name
state.last_response = slot_config.prompt
```

---

#### Rule 3: WAITING_FOR_SLOT → VALIDATING_SLOT

**Trigger**: User provides a value for the requested slot.

**Conditions**: User message received.

**State updates**:
```python
state.conversation_state = ConversationState.VALIDATING_SLOT
state.slots[state.waiting_for_slot] = user_message  # Temporary, will be normalized
```

---

#### Rule 4: VALIDATING_SLOT → WAITING_FOR_SLOT (Retry)

**Trigger**: Validation fails.

**Conditions**: Validator returns False or raises ValidationError.

**State updates**:
```python
state.conversation_state = ConversationState.WAITING_FOR_SLOT
# Clear invalid value
state.slots[state.waiting_for_slot] = None
# Show error message
state.last_response = f"Invalid {slot_name}. Please provide a valid value."
```

---

#### Rule 5: VALIDATING_SLOT → EXECUTING_ACTION

**Trigger**: All required slots collected and validated.

**Conditions**:
- All required slots for current action are filled
- All validations passed

**State updates**:
```python
state.conversation_state = ConversationState.EXECUTING_ACTION
state.current_step = action_step_name
state.waiting_for_slot = None  # Clear, no longer waiting
```

---

#### Rule 6: EXECUTING_ACTION → COMPLETED

**Trigger**: Action completes successfully and no more steps.

**Conditions**:
- Action executed without errors
- No more steps in flow

**State updates**:
```python
state.conversation_state = ConversationState.COMPLETED
state.current_flow = "none"
state.current_step = None
```

---

#### Rule 7: ANY → ERROR

**Trigger**: Unexpected error during processing.

**Conditions**: Exception raised during execution.

**State updates**:
```python
state.conversation_state = ConversationState.ERROR
state.metadata["error"] = {
    "type": type(exception).__name__,
    "message": str(exception),
    "timestamp": time.time(),
    "recovery_state": previous_state,  # For recovery
}
```

---

### Transition Matrix

| From State | To State | Trigger | Conditions |
|-----------|----------|---------|------------|
| IDLE | UNDERSTANDING | User message | Always |
| UNDERSTANDING | WAITING_FOR_SLOT | Slot needed | Slot empty |
| UNDERSTANDING | EXECUTING_ACTION | All slots filled | All required slots present |
| UNDERSTANDING | IDLE | No intent | NLU confidence too low |
| WAITING_FOR_SLOT | VALIDATING_SLOT | User responds | Message received |
| WAITING_FOR_SLOT | UNDERSTANDING | User changes intent | Intent markers detected |
| VALIDATING_SLOT | WAITING_FOR_SLOT | Validation fails | Validator returns False |
| VALIDATING_SLOT | UNDERSTANDING | Validation succeeds | Check if more slots needed |
| VALIDATING_SLOT | EXECUTING_ACTION | All slots validated | All required slots present |
| EXECUTING_ACTION | COMPLETED | Action succeeds | No more steps |
| EXECUTING_ACTION | WAITING_FOR_SLOT | Action needs more data | Action returns missing slots |
| EXECUTING_ACTION | CONFIRMING | Action needs confirmation | Action config requires confirm |
| CONFIRMING | EXECUTING_ACTION | User confirms | User says yes |
| CONFIRMING | COMPLETED | User cancels | User says no |
| COMPLETED | IDLE | Flow done | Always |
| ANY | ERROR | Exception | Unexpected error |
| ERROR | UNDERSTANDING | User retries | User sends new message |
| ERROR | IDLE | User cancels | User cancels task |

---

## State Persistence

### Checkpoint Strategy

**When to save state**:
1. ✅ After each successful node execution
2. ✅ After state transitions
3. ✅ Before calling external actions
4. ✅ After generating response to user

**What to save**:
- Complete DialogueState (all fields)
- Message history (with configurable limit)
- Trace events (for debugging)

**Implementation**:
```python
async def save_checkpoint(self, user_id: str, state: DialogueState):
    """Save state to persistent storage"""
    checkpoint_data = {
        "user_id": user_id,
        "timestamp": time.time(),
        "state": state,  # Full state dict
        "version": "1.0",  # Schema version for migrations
    }

    await self.checkpointer.aput(
        config={"configurable": {"thread_id": user_id}},
        checkpoint=checkpoint_data,
    )
```

### State Recovery

**On error**:
```python
async def recover_from_error(self, user_id: str) -> DialogueState:
    """Recover from error state"""
    state = await self.load_state(user_id)

    if state.conversation_state == ConversationState.ERROR:
        # Get recovery state from metadata
        recovery_state = state.metadata.get("error", {}).get("recovery_state")

        if recovery_state:
            # Restore to previous state
            state.conversation_state = ConversationState(recovery_state)
            state.last_response = "I encountered an error. Let's try again."
        else:
            # Reset to IDLE
            state.conversation_state = ConversationState.IDLE
            state.current_flow = "none"
            state.current_step = None

    return state
```

---

## Examples

### Example 1: Complete Flight Booking Flow

```python
# Turn 1: User starts booking
User: "I want to book a flight"

State BEFORE:
{
    "conversation_state": "idle",
    "current_flow": "none",
    "current_step": None,
    "slots": {},
}

# System calls NLU
State AFTER NLU:
{
    "conversation_state": "understanding",
    "current_flow": "book_flight",  # Activated by NLU
    "current_step": None,
    "slots": {},
}

# System checks: need origin slot
State AFTER transition to WAITING_FOR_SLOT:
{
    "conversation_state": "waiting_for_slot",
    "current_flow": "book_flight",
    "current_step": "collect_origin",
    "waiting_for_slot": "origin",
    "slots": {},
    "last_response": "Where would you like to fly from?",
}

Response: "Where would you like to fly from?"

# ===== Turn 2: User provides origin =====
User: "New York"

State BEFORE:
{
    "conversation_state": "waiting_for_slot",
    "waiting_for_slot": "origin",
    "slots": {},
}

# System does direct mapping (NO NLU CALL)
State AFTER direct mapping:
{
    "conversation_state": "validating_slot",
    "waiting_for_slot": "origin",
    "slots": {"origin": "New York"},  # Mapped directly
}

# System validates
State AFTER validation:
{
    "conversation_state": "waiting_for_slot",
    "current_step": "collect_destination",
    "waiting_for_slot": "destination",
    "slots": {"origin": "New York"},
    "last_response": "Where would you like to fly to?",
}

Response: "Where would you like to fly to?"

# ===== Turn 3: User provides destination =====
User: "Los Angeles"

# (Same pattern: direct mapping, validation, next slot)

State AFTER:
{
    "conversation_state": "waiting_for_slot",
    "current_step": "collect_date",
    "waiting_for_slot": "departure_date",
    "slots": {"origin": "New York", "destination": "Los Angeles"},
    "last_response": "When would you like to depart?",
}

Response: "When would you like to depart?"

# ===== Turn 4: User provides date =====
User: "Next Friday"

State AFTER validation:
{
    "conversation_state": "executing_action",
    "current_step": "search_flights",
    "waiting_for_slot": None,
    "slots": {
        "origin": "New York",
        "destination": "Los Angeles",
        "departure_date": "2025-12-12"  # Normalized
    },
}

# System executes action
State AFTER action:
{
    "conversation_state": "completed",
    "current_flow": "none",
    "current_step": None,
    "slots": {
        "origin": "New York",
        "destination": "Los Angeles",
        "departure_date": "2025-12-12",
        "booking_ref": "BK-98765",  # Action output
    },
    "last_response": "Your flight is booked! Booking reference: BK-98765",
}

Response: "Your flight is booked! Booking reference: BK-98765"
```

### Example 2: User Correction Mid-Flow

```python
# Turn 1-2: System collected origin = "New York"
State:
{
    "conversation_state": "waiting_for_slot",
    "waiting_for_slot": "destination",
    "slots": {"origin": "New York"},
}

Response: "Where would you like to fly to?"

# Turn 3: User corrects origin instead of providing destination
User: "Actually, change the origin to Boston"

# System detects intent markers ("change", "actually")
# Routes to UNDERSTANDING instead of direct mapping
State AFTER NLU:
{
    "conversation_state": "understanding",
    "current_flow": "book_flight",
    "slots": {"origin": "Boston"},  # NLU updated the slot
}

# System resumes from collect_destination
State AFTER:
{
    "conversation_state": "waiting_for_slot",
    "current_step": "collect_destination",
    "waiting_for_slot": "destination",
    "slots": {"origin": "Boston"},
    "last_response": "Got it, I've updated your origin to Boston. Where would you like to fly to?",
}

Response: "Got it, I've updated your origin to Boston. Where would you like to fly to?"
```

---

## Summary

This state machine design provides:

1. ✅ **Explicit tracking** of conversation state
2. ✅ **Context-aware routing** based on current state
3. ✅ **Efficient execution** by skipping unnecessary NLU calls
4. ✅ **Clear debugging** with inspectable state
5. ✅ **Robust error recovery** with state restoration

**Key Innovation**: `conversation_state` + `waiting_for_slot` enable direct message-to-slot mapping, avoiding redundant NLU calls while maintaining flexibility to handle intent changes.

---

**Next**: Read [03-message-processing.md](03-message-processing.md) for message routing implementation details.
