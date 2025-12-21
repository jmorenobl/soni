# Comprehensive Flow Analysis: Soni Framework

**Date**: 2025-12-08
**Status**: Critical Issue Identified
**Scenario Affected**: Scenario 1 (Simple Flight Booking)

---

## Executive Summary

The Soni Framework has a **critical flow completion bug**: When all required slots are collected, the system transitions to `idle` state instead of executing the action or requesting confirmation. This analysis documents the root cause, provides a comprehensive state-action matrix for all conversational patterns, and proposes architectural improvements.

### Key Findings

1. ✅ **Design is sound**: The documented architecture in `docs/design/` is well-structured
2. ❌ **Implementation diverges**: Critical logic in `validate_slot.py` is overly complex ("spaghetti code")
3. ❌ **Flow doesn't complete**: `advance_through_completed_steps()` fails to transition to action/confirmation
4. ⚠️ **Multiple sources of truth**: State tracked in 3+ places leads to inconsistencies
5. ⚠️ **Correction handling split**: Logic scattered across validate_slot and dedicated handlers

---

## Part 1: Critical Bug Analysis

### Scenario 1 Failure - Step by Step

**Test**: Simple flight booking with sequential slot provision

```
Turn 1: "I want to book a flight" → ✅ Triggers book_flight flow
Turn 2: "Madrid" → ✅ Sets origin, asks for destination
Turn 3: "Barcelona" → ✅ Sets destination, asks for departure_date
Turn 4: "Tomorrow" → ❌ Sets departure_date but FAILS to complete
```

**Expected after Turn 4:**
```yaml
conversation_state: "ready_for_action" or "executing_action"
all_slots_filled: true
waiting_for_slot: null
current_step: "book_flight_action" or "confirm_booking"
Response: "I've booked your flight from Madrid to Barcelona..."
```

**Actual after Turn 4:**
```yaml
conversation_state: "idle"  # ❌ WRONG
all_slots_filled: false     # ❌ WRONG
waiting_for_slot: "departure_date"  # ❌ Should be null
current_step: None          # ❌ Should be action step
Response: "How can I help you?"  # ❌ Generic fallback
```

**Warning in logs:**
```
WARNING:soni.dm.nodes.generate_response:No confirmation, booking_ref, or action_result found, using default response
```

### Root Cause Analysis

#### Problem Location: `FlowStepManager.advance_through_completed_steps()`

File: `/Users/jorge/Projects/Playground/soni/src/soni/flow/step_manager.py` (lines 66-180)

**What should happen:**
1. Check if current step is complete
2. If complete, advance to next step
3. Repeat until finding incomplete step OR reaching action/confirmation
4. Return appropriate conversation_state

**What actually happens:**
```python
# Line 138-144
iterations = 0
max_iterations = 20

while iterations < max_iterations:
    iterations += 1

    # Get active flow context
    active_ctx = flow_manager.get_active_context(state)
    if not active_ctx:
        # NO FLOW - return idle
        return {"conversation_state": ConversationState.IDLE.value}
```

**Critical Issue #1: Early exit on missing flow**

When the last slot is filled, the code path leads to:
1. `advance_through_completed_steps()` is called
2. Gets active context successfully
3. Processes the slot successfully
4. BUT: On next iteration, somehow `get_active_context()` returns None
5. Function returns `idle` state immediately
6. Never reaches action/confirmation step

**Hypothesis:** The flow is being popped/cleared prematurely during slot validation.

#### Problem Location 2: `validate_slot_node()`

File: `/Users/jorge/Projects/Playground/soni/src/soni/dm/nodes/validate_slot.py` (lines 1-543)

**Overly complex with multiple exit paths:**

1. **Lines 82-119**: Correction detection
2. **Lines 121-267**: Correction handling with nested conditionals
3. **Lines 269-311**: Normal slot processing
4. **Lines 313-465**: Fallback mechanism (second NLU call)
5. **Lines 467-543**: Step advancement

**Each path updates state differently**, making it hard to ensure consistency.

### The Missing Link: Step Type Handling

Looking at `step_manager.py` lines 170-180:

```python
# Determine conversation state based on step type
step_type = current_step_config.type
if step_type == "collect":
    conversation_state = ConversationState.WAITING_FOR_SLOT.value
elif step_type == "action":
    conversation_state = ConversationState.READY_FOR_ACTION.value
elif step_type == "confirm":
    conversation_state = ConversationState.READY_FOR_CONFIRMATION.value
else:
    conversation_state = ConversationState.WAITING_FOR_SLOT.value
```

**This logic is correct**, BUT it's only reached if:
1. A step is found
2. The step is incomplete
3. No early exit occurred

**The bug:** When all slots are filled, the code never reaches the action/confirm step because it exits early with `idle`.

---

## Part 2: Comprehensive Conversational Pattern Analysis

### The Core Problem: Missing Decision Matrix

The current implementation uses **reactive, conditional logic** scattered across multiple files. What's needed is a **state-action matrix** that explicitly defines:

> **Given [current_state] and [message_type] and [context], what [action] should be taken?**

### Proposed State-Action Matrix

#### Dimensions

**States (rows):**
- `idle` - No active flow
- `waiting_for_slot` - Expecting slot value
- `ready_for_action` - All slots collected, ready to execute
- `executing_action` - Action in progress
- `ready_for_confirmation` - Needs user confirmation
- `confirming` - Waiting for yes/no
- `completed` - Flow finished
- `error` - Error state

**Message Types (columns):**
- `slot_value` - Direct answer to slot request
- `multiple_slots` - Multiple slots in one message
- `correction` - User corrects previous slot
- `modification` - User modifies slot mid-flow
- `intent_change` - User triggers new flow
- `cancel` - User cancels current flow
- `confirmation` - User confirms (yes/no)
- `digression_question` - User asks question
- `digression_help` - User requests help
- `chitchat` - Social talk

**Context Modifiers:**
- `has_active_flow`: bool
- `slot_name_mentioned`: bool
- `all_slots_filled`: bool
- `waiting_for_slot`: str | None
- `current_prompted_slot`: str | None
- `flow_requires_confirmation`: bool

---

### Matrix: State × Message Type → Action

| State | slot_value | multiple_slots | correction | modification | intent_change | cancel | confirmation | digression | chitchat |
|-------|-----------|----------------|-----------|--------------|--------------|--------|-------------|-----------|----------|
| **idle** | ❌ Error: no flow | ❌ Error: no flow | ❌ Error: no flow | ❌ Error: no flow | ✅ Push new flow | ⚠️ Nothing to cancel | ❌ Nothing to confirm | ✅ Answer question | ✅ Chitchat response |
| **waiting_for_slot** | ✅ Validate & advance | ✅ Validate all & advance | ✅ Update slot, stay at current | ✅ Update slot, stay at current | ⚠️ Push/switch flow | ✅ Pop flow | ❌ Wrong context | ✅ Answer + reprompt | ✅ Chitchat + reprompt |
| **ready_for_action** | ⚠️ Clarify: already have all | ✅ Update slots, re-check | ✅ Update slot → back to collect | ✅ Update slot → back to collect | ⚠️ Push/switch flow | ✅ Pop flow | ❌ Nothing to confirm yet | ✅ Answer question | ✅ Chitchat response |
| **executing_action** | ⚠️ Wait for action | ⚠️ Wait for action | ⚠️ Wait for action | ⚠️ Wait for action | ⚠️ Can't interrupt | ⚠️ Can't interrupt | ❌ Not confirming | ⚠️ Wait for action | ⚠️ Wait for action |
| **ready_for_confirmation** | ⚠️ Clarify: need confirm | ✅ Update slots, re-check | ✅ Update slot → back to collect | ✅ Update slot → back to collect | ⚠️ Push/switch flow | ✅ Pop flow | ✅ Execute if yes | ✅ Answer + reprompt | ✅ Chitchat + reprompt |
| **confirming** | ⚠️ Interpret as yes/no | ⚠️ Interpret as yes/no | ✅ Update slot → back to collect | ✅ Update slot → back to collect | ⚠️ Push/switch flow | ✅ Pop flow | ✅ Execute if yes | ✅ Answer + reprompt | ✅ Chitchat + reprompt |
| **completed** | ⚠️ Context: flow done | ⚠️ Context: flow done | ❌ Flow completed | ❌ Flow completed | ✅ Push new flow | ⚠️ Nothing active | ❌ Nothing to confirm | ✅ Answer question | ✅ Chitchat response |
| **error** | ⚠️ Attempt recovery | ⚠️ Attempt recovery | ⚠️ Attempt recovery | ⚠️ Attempt recovery | ✅ Cancel & start new | ✅ Cancel & clear | ❌ Can't confirm | ✅ Answer question | ✅ Chitchat response |

**Legend:**
- ✅ Standard action - well-defined behavior
- ⚠️ Context-dependent - needs additional logic
- ❌ Invalid - should not happen or reject gracefully

---

## Part 3: Detailed Pattern Breakdown

### Pattern 1: Simple Sequential Flow (The Bug Case)

**Scenario:** User provides slots one at a time in order

```
User: "I want to book a flight"
Bot: "Where are you departing from?"
User: "Madrid"
Bot: "Where would you like to go?"
User: "Barcelona"
Bot: "What is your departure date?"
User: "Tomorrow"
Bot: [SHOULD EXECUTE ACTION]
```

**Current State Transitions:**
```
idle → [intent] → waiting_for_slot (origin)
waiting_for_slot (origin) → [slot_value] → waiting_for_slot (destination)
waiting_for_slot (destination) → [slot_value] → waiting_for_slot (departure_date)
waiting_for_slot (departure_date) → [slot_value] → idle ❌ BUG!
```

**Expected State Transitions:**
```
idle → [intent] → waiting_for_slot (origin)
waiting_for_slot (origin) → [slot_value] → waiting_for_slot (destination)
waiting_for_slot (destination) → [slot_value] → waiting_for_slot (departure_date)
waiting_for_slot (departure_date) → [slot_value] → ready_for_action → executing_action → completed
```

**Fix Required:**
- `advance_through_completed_steps()` must continue advancing after last slot
- Must detect when all required slots are filled
- Must transition to action/confirmation step
- Must NOT return to idle

---

### Pattern 2: Multiple Slots at Once

**Scenario:** User provides multiple pieces of info in one message

```
User: "I want to fly from New York to Los Angeles"
Bot: "What is your departure date?"
User: "Next Friday"
Bot: [SHOULD EXECUTE ACTION]
```

**NLU should extract:**
```python
{
    "message_type": "slot_value",
    "command": "book_flight",
    "slots": [
        {"name": "origin", "value": "New York", "confidence": 0.95},
        {"name": "destination", "value": "Los Angeles", "confidence": 0.9}
    ]
}
```

**Required Logic:**
1. Validate ALL extracted slots
2. Set ALL slots in flow_slots
3. Call `advance_through_completed_steps()` which should:
   - Skip collect_origin (complete)
   - Skip collect_destination (complete)
   - Stop at collect_departure_date (incomplete)
   - Return conversation_state=waiting_for_slot, waiting_for_slot=departure_date
4. After next turn with departure_date: advance to action

**Current Status:** Likely works but needs verification

---

### Pattern 3: Slot Correction

**Scenario:** User realizes they made a mistake

```
User: "Book a flight"
Bot: "Where are you departing from?"
User: "Chicago"
Bot: "Where would you like to go?"
User: "Actually, I meant Denver not Chicago"
Bot: [SHOULD UPDATE origin=Denver, STAY at destination collection]
```

**NLU should detect:**
```python
{
    "message_type": "correction",
    "command": None,
    "slots": [
        {"name": "origin", "value": "Denver", "action": "correction"}
    ]
}
```

**Required Logic:**
1. Update the corrected slot: origin=Denver
2. Stay at current conversation position (still collecting destination)
3. Acknowledge: "Got it, updated your departure city to Denver. Where would you like to go?"

**Current Status:** ❌ BROKEN - Complex logic in `_handle_correction_flow()` tries to guess target step

**Correct Approach:**
```python
def handle_correction(state, corrected_slot_name, new_value):
    # Update the slot
    flow_manager.set_slot(state, corrected_slot_name, new_value)

    # Stay at current step
    current_step = state["current_step"]
    waiting_for = state["waiting_for_slot"]

    return {
        "flow_slots": updated_slots,
        "current_step": current_step,  # DON'T CHANGE
        "waiting_for_slot": waiting_for,  # DON'T CHANGE
        "conversation_state": state["conversation_state"]  # DON'T CHANGE
    }
```

**Simple rule:** Correction updates data but doesn't change position.

---

### Pattern 4: Slot Modification

**Scenario:** User wants to change a slot while at a different collection point

```
User: "Book a flight from Boston to Miami on December 15"
Bot: "How many passengers?"
User: "Change the date to December 20"
Bot: [SHOULD UPDATE departure_date, STAY at passengers collection]
```

**Difference from Correction:**
- **Correction:** User realizes they made an error → immediate fix
- **Modification:** User wants to change something → intentional edit

**Both should behave similarly:**
1. Update the slot
2. Stay at current position
3. Acknowledge and continue

**Current Status:** Similar to correction - likely over-engineered

---

### Pattern 5: Digression (Question)

**Scenario:** User asks a question mid-flow

```
User: "Book a flight"
Bot: "Where are you departing from?"
User: "What airports do you support?"
Bot: "We support all major airports including JFK, LAX, ORD..."
Bot: "Where are you departing from?" [RE-PROMPT]
```

**NLU should detect:**
```python
{
    "message_type": "digression_question",
    "command": None,
    "slots": [],
    "topic": "airports"
}
```

**Required Logic:**
1. Recognize this is NOT a slot value
2. Delegate to knowledge base / QA system
3. Generate response to question
4. Re-prompt for the slot we're waiting for
5. **DO NOT** change flow stack
6. **DO NOT** change current_step or waiting_for_slot

**Current Status:** ✅ Should work - has dedicated handler

---

### Pattern 6: Intent Change (Flow Switch)

**Scenario:** User wants to do something else mid-flow

```
User: "Book a flight"
Bot: "Where are you departing from?"
User: "Actually, I want to check my existing booking first"
Bot: "What is your booking reference?"
```

**NLU should detect:**
```python
{
    "message_type": "intent_change",
    "command": "check_booking",
    "slots": []
}
```

**Required Logic:**
1. Pause current flow (don't cancel)
2. Push new flow onto stack
3. Start new flow from beginning
4. When new flow completes, resume original flow

**Stack after intent change:**
```python
flow_stack = [
    {"flow_name": "book_flight", "flow_id": "bf_1", "state": "paused", "current_step": "collect_origin"},
    {"flow_name": "check_booking", "flow_id": "cb_1", "state": "active", "current_step": "collect_reference"}  # Top
]
```

**Current Status:** ✅ Should work - FlowManager handles push/pop

---

### Pattern 7: Cancel

**Scenario:** User wants to abort the current flow

```
User: "Book a flight"
Bot: "Where are you departing from?"
User: "Cancel this"
Bot: "Booking cancelled. How can I help you?"
```

**NLU should detect:**
```python
{
    "message_type": "cancel",
    "command": "cancel",
    "slots": []
}
```

**Required Logic:**
1. Pop current flow from stack with result="cancelled"
2. Clear slots for that flow_id
3. If stack empty: return to idle
4. If stack not empty: resume previous flow

**Current Status:** ✅ Should work

---

### Pattern 8: Confirmation

**Scenario:** Flow requires user confirmation before action

```
[All slots collected]
Bot: "Book a flight from Madrid to Barcelona on 2025-12-09 for 1 passenger?"
User: "Yes"
Bot: [EXECUTE ACTION]
```

**NLU should detect:**
```python
{
    "message_type": "confirmation",
    "command": "yes",  # or "no"
    "slots": []
}
```

**Required Logic:**
1. Check conversation_state is "confirming"
2. If "yes": advance to action step
3. If "no": ask what to change or cancel

**Current Status:** Likely works but needs testing

---

### Pattern 9: Correction During Confirmation

**Scenario:** User spots error during confirmation

```
Bot: "Book a flight from Madrid to Barcelona on 2025-12-09?"
User: "No, change the destination to Valencia"
Bot: [UPDATE destination, GO BACK to waiting_for_slot, ASK for confirmation again]
```

**NLU should detect:**
```python
{
    "message_type": "correction",
    "command": None,
    "slots": [
        {"name": "destination", "value": "Valencia", "action": "correction"}
    ]
}
```

**Required Logic:**
1. Update corrected slot
2. Set all_slots_filled = True (still have all required slots)
3. Transition back to ready_for_confirmation
4. Re-generate confirmation prompt with updated data

**Current Status:** ❌ Likely broken - needs specific handling

---

## Part 4: Architectural Recommendations

### Root Problem: Imperative Control Flow

**Current Approach:**
```python
# Scattered across multiple files
if correction_detected:
    if all_slots_filled:
        if flow_requires_confirmation:
            target_step = find_confirmation_step()
        else:
            target_step = find_action_step()
    else:
        target_step = find_slot_step()
```

**This is spaghetti code because:**
- Logic duplicated across nodes
- Hard to test all branches
- Easy to miss edge cases
- Difficult to add new patterns

### Proposed Solution: State Machine + Decision Table

**1. Explicit State Machine**

Create `src/soni/dm/state_machine.py`:

```python
from enum import Enum
from typing import Protocol, TypedDict

class ConversationState(str, Enum):
    IDLE = "idle"
    WAITING_FOR_SLOT = "waiting_for_slot"
    READY_FOR_ACTION = "ready_for_action"
    EXECUTING_ACTION = "executing_action"
    READY_FOR_CONFIRMATION = "ready_for_confirmation"
    CONFIRMING = "confirming"
    COMPLETED = "completed"
    ERROR = "error"

class MessageType(str, Enum):
    SLOT_VALUE = "slot_value"
    MULTIPLE_SLOTS = "multiple_slots"
    CORRECTION = "correction"
    MODIFICATION = "modification"
    INTENT_CHANGE = "intent_change"
    CANCEL = "cancel"
    CONFIRMATION = "confirmation"
    DIGRESSION_QUESTION = "digression_question"
    DIGRESSION_HELP = "digression_help"
    CHITCHAT = "chitchat"

class StateContext(TypedDict):
    """Context information for state transition decisions."""
    has_active_flow: bool
    all_slots_filled: bool
    waiting_for_slot: str | None
    current_prompted_slot: str | None
    flow_requires_confirmation: bool
    action_in_progress: bool
    digression_depth: int

class TransitionResult(TypedDict):
    """Result of a state transition."""
    next_state: ConversationState
    action: str  # Name of action to execute
    updates: dict[str, Any]  # State updates to apply

class TransitionHandler(Protocol):
    """Handler for a specific state × message_type combination."""
    async def handle(
        self,
        state: DialogueState,
        nlu_result: NLUOutput,
        context: StateContext
    ) -> TransitionResult:
        ...
```

**2. Decision Table Registry**

```python
class StateTransitionRegistry:
    """Central registry for all state transitions."""

    def __init__(self):
        self._handlers: dict[tuple[ConversationState, MessageType], TransitionHandler] = {}

    def register(
        self,
        from_state: ConversationState,
        message_type: MessageType,
        handler: TransitionHandler
    ):
        """Register a handler for a specific transition."""
        key = (from_state, message_type)
        self._handlers[key] = handler

    async def handle_transition(
        self,
        current_state: ConversationState,
        message_type: MessageType,
        state: DialogueState,
        nlu_result: NLUOutput,
        context: StateContext
    ) -> TransitionResult:
        """Execute the appropriate handler for this transition."""
        key = (current_state, message_type)
        handler = self._handlers.get(key)

        if not handler:
            # Fallback to default handler
            handler = self._get_default_handler(current_state, message_type)

        return await handler.handle(state, nlu_result, context)
```

**3. Specific Transition Handlers**

```python
class WaitingForSlotToSlotValueHandler:
    """Handle: waiting_for_slot + slot_value → validate & advance."""

    async def handle(
        self,
        state: DialogueState,
        nlu_result: NLUOutput,
        context: StateContext
    ) -> TransitionResult:
        # Extract slots from NLU
        slots = nlu_result.slots

        # Validate and normalize all slots
        validated_slots = await self._validate_all_slots(slots)

        # Update state
        for slot_name, slot_value in validated_slots.items():
            flow_manager.set_slot(state, slot_name, slot_value)

        # Advance through completed steps
        advancement = await step_manager.advance_through_completed_steps(state)

        return TransitionResult(
            next_state=advancement["conversation_state"],
            action="respond_to_slot_collection",
            updates=advancement
        )

class WaitingForSlotToCorrectionHandler:
    """Handle: waiting_for_slot + correction → update slot, stay."""

    async def handle(
        self,
        state: DialogueState,
        nlu_result: NLUOutput,
        context: StateContext
    ) -> TransitionResult:
        # Extract corrected slot
        corrected_slot = nlu_result.slots[0]  # Should be exactly one

        # Update the slot value
        flow_manager.set_slot(state, corrected_slot.name, corrected_slot.value)

        # DON'T change current position
        return TransitionResult(
            next_state=ConversationState.WAITING_FOR_SLOT,
            action="acknowledge_correction",
            updates={
                "flow_slots": state["flow_slots"],
                "current_step": state["current_step"],  # Stay here
                "waiting_for_slot": state["waiting_for_slot"],  # Still waiting
                "metadata": {
                    **state.get("metadata", {}),
                    "_last_correction": {
                        "slot": corrected_slot.name,
                        "value": corrected_slot.value,
                        "timestamp": datetime.now().isoformat()
                    }
                }
            }
        )
```

**4. Main Transition Router**

Replace validate_slot_node with:

```python
async def transition_node(
    state: DialogueState,
    runtime: Runtime[RuntimeContext]
) -> dict[str, Any]:
    """Main transition node - routes based on state machine."""

    # Get dependencies
    registry = runtime.context["transition_registry"]
    flow_manager = runtime.context["flow_manager"]

    # Get NLU result
    nlu_result = NLUOutput.model_validate(state["nlu_result"])

    # Build context
    active_flow = flow_manager.get_active_context(state)
    context = StateContext(
        has_active_flow=active_flow is not None,
        all_slots_filled=state.get("all_slots_filled", False),
        waiting_for_slot=state.get("waiting_for_slot"),
        current_prompted_slot=state.get("current_prompted_slot"),
        flow_requires_confirmation=_requires_confirmation(active_flow),
        action_in_progress=state.get("conversation_state") == "executing_action",
        digression_depth=state.get("digression_depth", 0)
    )

    # Execute transition
    current_state = ConversationState(state["conversation_state"])
    message_type = MessageType(nlu_result.message_type)

    result = await registry.handle_transition(
        current_state,
        message_type,
        state,
        nlu_result,
        context
    )

    # Apply updates
    return result["updates"]
```

---

### Benefits of State Machine Approach

1. **Explicit**: Every possible transition is registered upfront
2. **Testable**: Each handler can be tested in isolation
3. **Maintainable**: Adding new patterns means adding new handlers
4. **Debuggable**: Clear execution path, easy to log
5. **Documented**: The registry IS the documentation

---

## Part 5: Immediate Fixes

### Fix 1: Repair `advance_through_completed_steps()`

**File:** `src/soni/flow/step_manager.py`

**Problem:** Early exit returns idle when flow is still active

**Fix:**
```python
def advance_through_completed_steps(
    self,
    state: DialogueState,
    runtime_context: RuntimeContext
) -> dict[str, Any]:
    """Advance through completed steps until finding incomplete step or action."""

    iterations = 0
    max_iterations = 20

    while iterations < max_iterations:
        iterations += 1

        # Get active flow context
        active_ctx = flow_manager.get_active_context(state)
        if not active_ctx:
            # ❌ OLD: return {"conversation_state": ConversationState.IDLE.value}
            # ✅ NEW: This should only happen if flow was intentionally cleared
            logger.warning("advance_through_completed_steps called with no active flow")
            return {"conversation_state": ConversationState.IDLE.value}

        flow_name = active_ctx["flow_name"]
        flow_id = active_ctx["flow_id"]
        current_step_name = active_ctx.get("current_step")

        # Get flow configuration
        flow_config = config_manager.get_flow_by_name(flow_name)
        if not flow_config or not flow_config.steps:
            logger.error(f"No flow config or steps for {flow_name}")
            return {"conversation_state": ConversationState.ERROR.value}

        # Find current step in configuration
        if not current_step_name:
            # First step
            current_step_config = flow_config.steps[0]
            current_step_name = current_step_config.step
        else:
            current_step_config = self._get_step_config(flow_config, current_step_name)
            if not current_step_config:
                logger.error(f"Step {current_step_name} not found in {flow_name}")
                return {"conversation_state": ConversationState.ERROR.value}

        # Check if current step is complete
        if self._is_step_complete(state, flow_id, current_step_config):
            # Advance to next step
            next_step = self._get_next_step(flow_config, current_step_name)

            if not next_step:
                # NO MORE STEPS - flow should complete
                logger.info(f"No more steps in {flow_name}, flow should complete")
                return {
                    "conversation_state": ConversationState.COMPLETED.value,
                    "all_slots_filled": True,
                    "current_step": None,
                    "waiting_for_slot": None
                }

            # Update to next step
            flow_manager.update_flow_step(state, flow_id, next_step.step)
            current_step_name = next_step.step
            current_step_config = next_step
            # Continue loop to check if this step is also complete
        else:
            # Found incomplete step - determine conversation state
            step_type = current_step_config.type

            if step_type == "collect":
                slot_name = current_step_config.slot
                return {
                    "conversation_state": ConversationState.WAITING_FOR_SLOT.value,
                    "waiting_for_slot": slot_name,
                    "current_prompted_slot": slot_name,
                    "current_step": current_step_name,
                    "all_slots_filled": False
                }

            elif step_type == "action":
                return {
                    "conversation_state": ConversationState.READY_FOR_ACTION.value,
                    "current_step": current_step_name,
                    "all_slots_filled": True,
                    "waiting_for_slot": None
                }

            elif step_type == "confirm":
                return {
                    "conversation_state": ConversationState.READY_FOR_CONFIRMATION.value,
                    "current_step": current_step_name,
                    "all_slots_filled": True,
                    "waiting_for_slot": None
                }

            else:
                logger.warning(f"Unknown step type: {step_type}")
                return {
                    "conversation_state": ConversationState.WAITING_FOR_SLOT.value,
                    "current_step": current_step_name
                }

    # Max iterations reached
    logger.error("Max iterations reached in advance_through_completed_steps")
    return {"conversation_state": ConversationState.ERROR.value}
```

**Key Changes:**
1. Better logging
2. Handle "no more steps" case → COMPLETED
3. Don't return idle unless truly no flow
4. Always set `all_slots_filled` when appropriate

---

### Fix 2: Simplify Correction Handling

**File:** `src/soni/dm/nodes/handle_correction.py`

**New implementation:**
```python
async def handle_correction_node(
    state: DialogueState,
    runtime: Runtime[RuntimeContext]
) -> dict[str, Any]:
    """Handle slot correction - update slot, stay at current position.

    Corrections don't change the conversation flow position.
    They update data but maintain context.
    """

    # Get dependencies
    flow_manager = runtime.context["flow_manager"]
    validator_registry = runtime.context["validator_registry"]

    # Get NLU result
    nlu_result = NLUOutput.model_validate(state["nlu_result"])

    # Extract corrected slots
    corrected_slots = [s for s in nlu_result.slots if s.action == "correction"]

    if not corrected_slots:
        logger.warning("handle_correction_node called but no correction slots found")
        # Treat as normal slot value
        return await validate_slot_node(state, runtime)

    # Get active flow
    active_ctx = flow_manager.get_active_context(state)
    if not active_ctx:
        return {
            "last_response": "I'm not sure what you want to correct. Can you please clarify?",
            "conversation_state": ConversationState.IDLE.value
        }

    flow_id = active_ctx["flow_id"]

    # Validate and update each corrected slot
    updates = []
    for slot in corrected_slots:
        # Validate new value
        validated_value = await validator_registry.validate(
            slot.name, slot.value, context={"flow_id": flow_id}
        )

        # Update slot
        flow_manager.set_slot(state, slot.name, validated_value)
        updates.append(f"{slot.name} to {validated_value}")

    # Generate acknowledgment
    if len(updates) == 1:
        ack = f"Got it, I've updated {updates[0]}."
    else:
        ack = f"Got it, I've updated: {', '.join(updates)}."

    # Stay at current position
    current_state = state.get("conversation_state")
    waiting_for = state.get("waiting_for_slot")

    # Generate re-prompt based on where we are
    if current_state == ConversationState.WAITING_FOR_SLOT.value and waiting_for:
        slot_config = _get_slot_config(active_ctx["flow_name"], waiting_for)
        reprompt = slot_config.prompt if slot_config else f"What is the {waiting_for}?"
        response = f"{ack} {reprompt}"
    elif current_state == ConversationState.READY_FOR_CONFIRMATION.value:
        # Re-generate confirmation with updated data
        response = await _generate_confirmation_prompt(state, flow_manager)
    else:
        response = ack

    return {
        "flow_slots": state["flow_slots"],  # Already updated
        "last_response": response,
        "conversation_state": current_state,  # DON'T CHANGE
        "current_step": state["current_step"],  # DON'T CHANGE
        "waiting_for_slot": waiting_for,  # DON'T CHANGE
        "metadata": {
            **state.get("metadata", {}),
            "_last_correction": {
                "slots": [{"name": s.name, "value": s.value} for s in corrected_slots],
                "timestamp": datetime.now().isoformat()
            }
        }
    }
```

**Key Principle:** Corrections are **data updates**, not **flow changes**.

---

### Fix 3: Remove Complexity from validate_slot.py

**Current:** 543 lines with nested conditionals

**Proposed:** Split into focused modules

```
src/soni/dm/nodes/
├── validate_slot.py          # 100 lines - main validation logic
├── correction_detector.py    # 50 lines - detect corrections
├── handle_correction.py      # 80 lines - correction handler (above)
├── handle_modification.py    # 80 lines - modification handler
├── slot_normalizer.py        # 60 lines - normalize slot values
└── fallback_handler.py       # 100 lines - fallback NLU call
```

**Each module has ONE responsibility:**
- `validate_slot.py`: Validate provided slots, delegate to others
- `correction_detector.py`: Detect if message is correction
- `handle_correction.py`: Update slot, stay at position
- `handle_modification.py`: Similar to correction
- `slot_normalizer.py`: Type conversion, formatting
- `fallback_handler.py`: Second NLU call when needed

---

## Part 6: Testing Strategy

### Unit Tests Needed

**Test `advance_through_completed_steps()`:**
```python
def test_advance_with_all_slots_filled():
    """When last slot is filled, should advance to action."""
    state = {
        "flow_stack": [{"flow_name": "book_flight", "flow_id": "bf_1", "current_step": "collect_date"}],
        "flow_slots": {"bf_1": {"origin": "Madrid", "destination": "Barcelona", "departure_date": "2025-12-09"}}
    }

    result = step_manager.advance_through_completed_steps(state, runtime_context)

    assert result["conversation_state"] == "ready_for_action"
    assert result["all_slots_filled"] is True
    assert result["waiting_for_slot"] is None

def test_advance_with_remaining_slots():
    """When some slots still needed, should stop at next collect."""
    state = {
        "flow_stack": [{"flow_name": "book_flight", "flow_id": "bf_1", "current_step": "collect_origin"}],
        "flow_slots": {"bf_1": {"origin": "Madrid"}}
    }

    result = step_manager.advance_through_completed_steps(state, runtime_context)

    assert result["conversation_state"] == "waiting_for_slot"
    assert result["waiting_for_slot"] == "destination"
    assert result["all_slots_filled"] is False
```

**Test Correction Handling:**
```python
def test_correction_stays_at_current_position():
    """Correction should update slot but not change position."""
    state = {
        "conversation_state": "waiting_for_slot",
        "waiting_for_slot": "destination",
        "current_step": "collect_destination",
        "flow_stack": [{"flow_name": "book_flight", "flow_id": "bf_1"}],
        "flow_slots": {"bf_1": {"origin": "Chicago"}}
    }

    nlu_result = {
        "message_type": "correction",
        "slots": [{"name": "origin", "value": "Denver", "action": "correction"}]
    }

    result = await handle_correction_node(state, runtime)

    assert result["conversation_state"] == "waiting_for_slot"
    assert result["waiting_for_slot"] == "destination"  # Unchanged
    assert result["current_step"] == "collect_destination"  # Unchanged
    assert state["flow_slots"]["bf_1"]["origin"] == "Denver"  # Updated
```

### Integration Tests Needed

Use `debug_scenarios.py` as a base:

1. ✅ Scenario 1: Simple sequential - MUST COMPLETE ACTION
2. ✅ Scenario 2: Multiple slots at once
3. ✅ Scenario 3: Correction mid-flow
4. ✅ Scenario 4: Digression question
5. ✅ Scenario 5: Cancel flow
6. ❌ NEW: Correction during confirmation
7. ❌ NEW: Modification with all slots filled
8. ❌ NEW: Intent change mid-slot-collection
9. ❌ NEW: Multiple corrections in sequence
10. ❌ NEW: Invalid slot value handling

---

## Part 7: Migration Plan

### Phase 1: Fix Critical Bug (Immediate)
- [ ] Fix `advance_through_completed_steps()` to handle completion
- [ ] Add logging to track state transitions
- [ ] Test scenario 1 completes successfully
- [ ] Verify `all_slots_filled` is set correctly

**Estimated effort:** 4 hours

### Phase 2: Simplify Correction Handling (Short-term)
- [ ] Implement simple correction handler (stay at position)
- [ ] Remove complex heuristics from `_handle_correction_flow()`
- [ ] Test correction scenarios work
- [ ] Update routing to use new handler

**Estimated effort:** 8 hours

### Phase 3: State Machine Refactor (Medium-term)
- [ ] Design state machine architecture
- [ ] Create transition registry
- [ ] Implement core transition handlers
- [ ] Migrate existing nodes to use state machine
- [ ] Add comprehensive tests

**Estimated effort:** 3-5 days

### Phase 4: Split validate_slot.py (Medium-term)
- [ ] Extract slot normalizer
- [ ] Extract correction detector
- [ ] Extract fallback handler
- [ ] Update imports and dependencies
- [ ] Verify all tests pass

**Estimated effort:** 2 days

### Phase 5: Complete State-Action Matrix (Long-term)
- [ ] Implement all transition handlers
- [ ] Add missing patterns (correction during confirmation, etc.)
- [ ] Create decision table documentation
- [ ] Performance optimization
- [ ] Production deployment

**Estimated effort:** 1-2 weeks

---

## Conclusion

The Soni Framework has excellent architectural design but suffers from **implementation complexity** accumulated during development. The primary issue is the lack of an **explicit state machine** and **decision table** for handling all conversational patterns.

### Critical Issues Identified

1. **Scenario 1 Failure**: Flow doesn't complete after last slot
2. **Spaghetti Code**: `validate_slot.py` has 543 lines of nested conditionals
3. **Correction Handling**: Overly complex heuristics instead of simple "stay at position"
4. **Multiple Truth Sources**: State tracked in 3+ places
5. **Missing Patterns**: No handling for correction during confirmation, modification edge cases

### Recommended Approach

1. **Immediate**: Fix `advance_through_completed_steps()` bug
2. **Short-term**: Simplify correction to "update data, stay at position"
3. **Medium-term**: Implement explicit state machine with transition registry
4. **Long-term**: Complete state-action matrix for all patterns

The state machine approach will:
- Make all transitions explicit and testable
- Eliminate spaghetti code
- Enable easy addition of new patterns
- Improve maintainability significantly

---

**Next Steps:**
1. Review and approve this analysis
2. Prioritize fixes (suggest starting with Phase 1 immediately)
3. Create GitHub issues for each phase
4. Begin implementation

---

**Document Version**: 1.0
**Author**: Claude (Sonnet 4.5)
**Review Status**: Pending
