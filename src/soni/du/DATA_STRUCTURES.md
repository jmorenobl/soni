# NLU Data Structures Reference (v2.0 Command-Driven)

This document describes the data structures used by the DialogueUnderstanding signature.

**IMPORTANT**: This documentation is for **DEVELOPER REFERENCE only**. It is **NOT included** in the prompt sent to the LLM.

## Overview

The NLU module receives the following inputs:
1. `user_message`: Raw user input (string)
2. `history`: Conversation history (dspy.History)
3. `context`: Current dialogue state (DialogueContext)
4. `current_datetime`: Current timestamp (ISO string)

And produces:
- `result`: NLU analysis output (NLUOutput with Commands)

## Input Structures

### 1. user_message: str

Raw user input message to analyze.

**Examples**:
- `"I want to book a flight"` (intent initiation → StartFlow)
- `"Madrid"` (slot value response → SetSlot)
- `"No, I meant Barcelona"` (correction → CorrectSlot)
- `"Yes, that's correct"` (confirmation → AffirmConfirmation)
- `"What destinations are available?"` (digression → ChitChat)

### 2. history: dspy.History

Conversation history as a list of message dictionaries.

**Structure**:
```python
History(messages=[
    {"role": "user", "content": "message text"},
    {"role": "assistant", "content": "response text"},
    ...
])
```

### 3. context: DialogueContext

Current dialogue state providing context for NLU analysis.

**Fields**:
- `current_flow` (str): Active flow name (e.g., "book_flight", "none")
- `expected_slots` (list[str]): Slots expected in current flow
- `current_slots` (dict[str, Any]): Already filled slots {slot_name: value}
- `current_prompted_slot` (str | None): Slot being explicitly asked for
- `conversation_state` (str | None): Current conversation phase
- `available_flows` (dict[str, str]): Available flows {name: description}
- `available_actions` (list[str]): Available action names

### 4. current_datetime: str

Current timestamp in ISO 8601 format for resolving temporal expressions.

## Output Structure

### NLUOutput (Command-Driven)

The NLU produces a list of **Commands** instead of message types.

**Fields**:
- `commands` (list[Command]): List of executable commands
- `entities` (list[ExtractedEntity]): Raw extracted entities for debugging
- `confidence` (float): Overall confidence score (0.0-1.0)
- `reasoning` (str): Chain-of-thought reasoning

### Available Commands

| Command | Description | Fields |
|---------|-------------|--------|
| `StartFlow` | Start a new flow | `flow_name`, `slots` (optional dict) |
| `SetSlot` | Provide a slot value | `slot_name`, `value` |
| `CorrectSlot` | Correct a previous value | `slot_name`, `new_value` |
| `AffirmConfirmation` | User says "yes" | - |
| `DenyConfirmation` | User says "no" | `slot_to_change` (optional) |
| `CancelFlow` | Cancel current flow | `reason` (optional) |
| `Clarify` | Ask clarification | `topic` |
| `ChitChat` | Off-topic conversation | `response_hint` |
| `HumanHandoff` | Request human agent | `reason` |
| `OutOfScope` | Out of scope query | `topic` |

## Examples by Command Type

### SetSlot (providing slot value)
```python
NLUOutput(
    commands=[
        SetSlot(slot_name="destination", value="Madrid")
    ],
    confidence=0.95
)
```

### CorrectSlot (fixing previous value)
```python
NLUOutput(
    commands=[
        CorrectSlot(slot_name="destination", new_value="Barcelona")
    ],
    confidence=0.90
)
```

### AffirmConfirmation (responding yes)
```python
NLUOutput(
    commands=[
        AffirmConfirmation()
    ],
    confidence=0.95
)
```

### StartFlow (changing intent)
```python
NLUOutput(
    commands=[
        StartFlow(flow_name="cancel_booking")
    ],
    confidence=0.90
)
```

### ChitChat (off-topic question)
```python
NLUOutput(
    commands=[
        ChitChat(response_hint="destinations")
    ],
    confidence=0.85
)
```

### Multiple Commands (slot + start)
```python
# "Book a flight to Madrid tomorrow"
NLUOutput(
    commands=[
        StartFlow(flow_name="book_flight"),
        SetSlot(slot_name="destination", value="Madrid"),
        SetSlot(slot_name="departure_date", value="2025-12-12")
    ],
    confidence=0.92
)
```

## Complete Example Flow

### Scenario: User booking flight to Madrid

**Input**:
```python
user_message = "I want to fly to Madrid tomorrow"

context = DialogueContext(
    current_flow="book_flight",
    expected_slots=["destination", "departure_date", "return_date"],
    current_slots={},
    current_prompted_slot="destination",
    conversation_state="waiting_for_slot",
)

current_datetime = "2025-12-11T10:00:00"
```

**Expected Output**:
```python
NLUOutput(
    commands=[
        SetSlot(slot_name="destination", value="Madrid"),
        SetSlot(slot_name="departure_date", value="2025-12-12")  # "tomorrow" resolved
    ],
    confidence=0.92
)
```

**Analysis**:
- Commands: Two SetSlot commands for destination and departure_date
- Departure date resolved from "tomorrow" using current_datetime
- Confidence: High (clear extraction)
