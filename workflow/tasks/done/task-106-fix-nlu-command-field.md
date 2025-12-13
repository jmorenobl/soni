## Task: 106 - Fix NLU Command Field (Updated Analysis)

**ID de tarea:** 106
**Prioridad:** MEDIA
**Duración estimada:** 2-3 horas

### Objetivo

Fix NLU to properly generate `command` field:
- Should be `None` for slot_value messages
- Should only be set for: intent changes, cancel, confirmation
- Update type to be optional (`str | None`)
- Add clear instructions in signature

### Problema Identificado

**Current behavior:**
```
User: "Madrid"
NLU Output: {
  message_type: "slot_value",
  command: "provide_origin"  ❌ Invented!
}
```

**Expected behavior:**
```
User: "Madrid"
NLU Output: {
  message_type: "slot_value",
  command: null  ✅ Correct!
}
```

**Root cause:**
1. Field is `command: str` (not optional, no default) - LLM must generate a value
2. LLM "invents" commands to fill required field
3. Solution: Make field optional (`str | None`) so LLM can output `None` when appropriate
4. Optimization: DSPy optimization will learn when to use `None` vs when to set a value

### Análisis del Código

**File:** `src/soni/du/models.py` (line 57)

```python
class NLUOutput(BaseModel):
    message_type: MessageType
    command: str  # ❌ Not optional!
    slots: list[SlotValue]
    confidence: float
```

**Problem:** Field is required (`str`), so LLM always generates something even when it should be `None`.

**File:** `src/soni/du/signatures.py` (line 28-29)

```python
result: NLUOutput = dspy.OutputField(
    desc="Analysis with message_type, command, and all extracted slots (list) with their actions"
)
```

**Note:** Following DSPy best practices, we keep descriptions minimal. The optimization process will learn when to set `command=None` from training examples.

### Solución

**Principio DSPy**: Mantener prompts mínimos y descriptivos. La optimización (MIPROv2, etc.) mejorará los prompts automáticamente. No agregar ejemplos en los prompts manuales.

#### Change 1: Make command optional in model

**File:** `src/soni/du/models.py`

**Current (line 53-60):**
```python
class NLUOutput(BaseModel):
    """Structured NLU output."""

    message_type: MessageType = Field(description="Type of user message")
    command: str = Field(description="User's intent/command")
    slots: list[SlotValue] = Field(default_factory=list, description="Extracted slot values")
    confidence: float = Field(ge=0.0, le=1.0, description="Overall confidence")
```

**Fixed:**
```python
class NLUOutput(BaseModel):
    """Structured NLU output."""

    message_type: MessageType = Field(description="Type of user message")
    command: str | None = Field(
        default=None,
        description="User's intent or command when changing intent, canceling, or confirming. None for slot value messages."
    )
    slots: list[SlotValue] = Field(default_factory=list, description="Extracted slot values")
    confidence: float = Field(ge=0.0, le=1.0, description="Overall confidence")
```

**Key changes:**
- ✅ `str | None` instead of `str` (optional)
- ✅ `default=None` so it's okay to omit
- ✅ Minimal description (no examples - optimization will learn this)

#### Change 2: Update signature with minimal description

**File:** `src/soni/du/signatures.py`

**Current (line 27-30):**
```python
result: NLUOutput = dspy.OutputField(
    desc="Analysis with message_type, command, and all extracted slots (list) with their actions"
)
```

**Fixed:**
```python
result: NLUOutput = dspy.OutputField(
    desc="NLU analysis with message_type, optional command, and extracted slots"
)
```

**Note**: Keep description minimal. DSPy optimization will learn when to set `command=None` vs when to set a value through training examples.

#### Change 3: Keep signature docstring minimal

**File:** `src/soni/du/signatures.py`

**Current (line 8-13):**
```python
class DialogueUnderstanding(dspy.Signature):
    """Analyze user message in dialogue context to determine intent and extract all slot values.

    Extract ALL slot values mentioned in the message. Each slot gets an action
    (provide/correct/modify) based on whether it's new or changing an existing value.
    """
```

**Fixed:**
```python
class DialogueUnderstanding(dspy.Signature):
    """Analyze user message in dialogue context to determine intent and extract all slot values.

    Extract ALL slot values mentioned in the message. Each slot gets an action
    (provide/correct/modify) based on whether it's new or changing an existing value.
    """
```

**Note**: No need to add command rules or examples in docstring. The optimization process will learn this from training data.

### Testing the Fix

After making changes, the LLM should learn:

```python
# Test 1: Slot value - command should be None
user_message = "Madrid"
context = DialogueContext(
    current_flow="book_flight",
    expected_slots=["origin", "destination", "departure_date"],
    current_prompted_slot="origin"
)

result = await nlu.predict(user_message, history, context)

assert result.message_type == MessageType.SLOT_VALUE
assert result.command is None  # ✅ Should be None!
assert len(result.slots) == 1
assert result.slots[0].name == "origin"
assert result.slots[0].value == "Madrid"
```

```python
# Test 2: Intent change - command should be set
user_message = "I want to book a flight"
context = DialogueContext(
    current_flow="none",
    available_flows=["book_flight", "check_booking"]
)

result = await nlu.predict(user_message, history, context)

assert result.message_type == MessageType.CONTINUATION  # or INTERRUPTION
assert result.command == "book_flight"  # ✅ Should be set!
```

### Implementation Steps

1. **Update models.py** - Make command optional (`str | None`) with minimal description
2. **Update signatures.py** - Keep OutputField description minimal (no examples)
3. **Test manually** - Run debug_scenarios.py and check NLU output
4. **Add unit tests** - Test that command is None for slot_value messages
5. **Note**: If behavior is still incorrect after fix, run DSPy optimization (MIPROv2) to learn correct patterns

### Expected Output After Fix

```bash
$ uv run python scripts/debug_scenarios.py 1

Turn 2: Provide origin
User: "Madrid"

NLU Output:
  Type: slot_value
  Command: None  ← ✅ Should be None now!
  Extracted slots:
    - origin: Madrid (conf: 0.95)
```

### Validation Commands

```bash
# 1. Run scenario 1
uv run python scripts/debug_scenarios.py 1

# Check that command is None for turns 2-4

# 2. Run all scenarios
uv run python scripts/debug_scenarios.py

# Verify no regressions

# 3. Unit test (create if doesn't exist)
uv run pytest tests/unit/test_nlu_command.py -v
```

### Unit Test to Add

**File:** `tests/unit/test_nlu_command.py` (new file)

```python
"""Test NLU command field generation."""

import pytest
import dspy
from soni.du.modules import SoniDU
from soni.du.models import DialogueContext, MessageType


@pytest.mark.asyncio
async def test_command_is_none_for_slot_value():
    """Command should be None when user provides slot value."""
    # Setup
    lm = dspy.LM("openai/gpt-4o-mini")
    dspy.configure(lm=lm)
    nlu = SoniDU(use_cot=False)

    # Context: waiting for origin
    context = DialogueContext(
        current_flow="book_flight",
        expected_slots=["origin", "destination", "departure_date"],
        current_prompted_slot="origin"
    )
    history = dspy.History(messages=[])

    # Act
    result = await nlu.predict("Madrid", history, context)

    # Assert
    assert result.message_type == MessageType.SLOT_VALUE
    assert result.command is None  # ✅ Must be None!
    assert len(result.slots) == 1
    assert result.slots[0].name == "origin"


@pytest.mark.asyncio
async def test_command_is_set_for_intent_change():
    """Command should be flow name when user changes intent."""
    # Setup
    lm = dspy.LM("openai/gpt-4o-mini")
    dspy.configure(lm=lm)
    nlu = SoniDU(use_cot=False)

    # Context: no active flow
    context = DialogueContext(
        current_flow="none",
        available_flows=["book_flight", "check_booking"]
    )
    history = dspy.History(messages=[])

    # Act
    result = await nlu.predict("I want to book a flight", history, context)

    # Assert
    assert result.command == "book_flight"  # ✅ Must be set!


@pytest.mark.asyncio
async def test_command_is_cancel_for_cancellation():
    """Command should be 'cancel' for cancellation."""
    # Setup
    lm = dspy.LM("openai/gpt-4o-mini")
    dspy.configure(lm=lm)
    nlu = SoniDU(use_cot=False)

    context = DialogueContext(current_flow="book_flight")
    history = dspy.History(messages=[])

    # Act
    result = await nlu.predict("cancel", history, context)

    # Assert
    assert result.message_type == MessageType.CANCELLATION
    assert result.command == "cancel"  # ✅ Must be 'cancel'!
```

### Success Criteria

- [ ] `command` field is optional (`str | None`) in NLUOutput
- [ ] Minimal description in Field() (no examples - follows DSPy best practices)
- [ ] Signature OutputField description is minimal
- [ ] Command is `None` for slot_value messages in debug output (may require optimization)
- [ ] Command is properly set for intent changes, cancel, confirmation
- [ ] All scenarios still pass
- [ ] Unit tests added and passing
- [ ] If behavior not correct after fix, document need for DSPy optimization

### Why This Matters

**Impact on system:**
- Currently: Low (system works despite incorrect command)
- Clarity: High (logs are confusing with invented commands)
- Future: Medium (might cause bugs if code starts using command field)

**Clean separation:**
- `command`: The **action** to take (change flow, cancel, confirm)
- `slots`: The **data** being provided
- `message_type`: The **type** of message

When user just provides data (slot value), there's no action/command - only data!

### DSPy Optimization Note

**Important**: After making the field optional, if the LLM still generates incorrect values, this is expected. DSPy's philosophy is:

1. **Minimal prompts**: Keep descriptions short and descriptive (no examples)
2. **Optimization learns**: Use MIPROv2 or other optimizers to learn correct patterns from training data
3. **Training examples**: Create examples showing `command=None` for slot_value messages

The fix makes the field optional so the model *can* output `None`. The optimization process will teach it *when* to output `None` vs when to set a value.

#### Training Examples for Optimization

If optimization is needed, create training examples like:

```python
import dspy
from soni.du.models import NLUOutput, DialogueContext, MessageType, SlotValue

# Example 1: Slot value - command should be None
example1 = dspy.Example(
    user_message="Madrid",
    history=dspy.History(messages=[]),
    context=DialogueContext(
        current_flow="book_flight",
        expected_slots=["origin", "destination"],
        current_prompted_slot="origin"
    ),
    current_datetime="2024-12-02T10:00:00",
    result=NLUOutput(
        message_type=MessageType.SLOT_VALUE,
        command=None,  # ✅ None for slot values
        slots=[SlotValue(name="origin", value="Madrid", confidence=0.95)],
        confidence=0.95
    )
).with_inputs("user_message", "history", "context", "current_datetime")

# Example 2: Intent change - command should be set
example2 = dspy.Example(
    user_message="I want to book a flight",
    history=dspy.History(messages=[]),
    context=DialogueContext(
        current_flow="none",
        available_flows=["book_flight", "check_booking"]
    ),
    current_datetime="2024-12-02T10:00:00",
    result=NLUOutput(
        message_type=MessageType.INTERRUPTION,
        command="book_flight",  # ✅ Set for intent changes
        slots=[],
        confidence=0.90
    )
).with_inputs("user_message", "history", "context", "current_datetime")
```

These examples will teach the optimizer when to use `None` vs when to set a command value.

### References

- Models: `src/soni/du/models.py` (line 57)
- Signature: `src/soni/du/signatures.py` (line 8-30)
- Usage: `src/soni/dm/nodes/understand.py`
- Output: `output-fixed.log`
