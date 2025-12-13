## Task: 334 - Document NLU Data Structures and Injection Flow

**ID de tarea:** 334
**Hito:** NLU Improvements
**Dependencias:** Ninguna
**Duración estimada:** 2-3 horas

### Objetivo

Create comprehensive documentation explaining what data structures are injected into the DialogueUnderstanding signature, with concrete examples and format specifications.

**IMPORTANT**: This documentation is for DEVELOPER REFERENCE only. It is NOT included in the prompt sent to the LLM. The signature docstring must be self-contained.

### Contexto

Currently, there is no centralized developer documentation explaining the data structures used in the NLU module (`dspy.History`, `DialogueContext`, `NLUOutput`, etc.). This makes it harder for developers to understand:
- What fields exist in each structure
- What format/type each field has
- Example values that represent typical usage
- How these structures relate to each other

**CRITICAL DISTINCTION**:
- This documentation (DATA_STRUCTURES.md) is for **developers** reading the code
- It is **NOT sent to the LLM** during DSPy optimization or inference
- The signature docstring (task-335) must be **self-contained** as it's what the LLM sees
- This file provides detailed reference that the docstring cannot include

### Entregables

- [ ] New documentation file: `src/soni/du/DATA_STRUCTURES.md`
- [ ] Documentation includes structure definition for all injected types
- [ ] Documentation includes concrete examples for each structure
- [ ] Added reference comments in `signatures.py` pointing to documentation
- [ ] Documentation follows English-only policy

### Implementación Detallada

#### Paso 1: Create DATA_STRUCTURES.md

**Archivo(s) a crear:** `src/soni/du/DATA_STRUCTURES.md`

**Estructura del documento:**

```markdown
# NLU Data Structures Reference

This document describes the data structures injected into the DialogueUnderstanding signature.

## Overview

The NLU module receives the following inputs:
1. `user_message`: Raw user input (string)
2. `history`: Conversation history (dspy.History)
3. `context`: Current dialogue state (DialogueContext)
4. `current_datetime`: Current timestamp (ISO string)

And produces:
- `result`: NLU analysis output (NLUOutput)

## Input Structures

### 1. user_message: str
[Detailed explanation with examples]

### 2. history: dspy.History
[Structure explanation with examples]

### 3. context: DialogueContext
[Field-by-field explanation with examples]

### 4. current_datetime: str
[Format explanation with examples]

## Output Structure

### NLUOutput
[Complete structure with examples for each MessageType]

## Complete Example Flow
[End-to-end example showing input → output]
```

**Explicación:**
- Use clear headings and structure
- Include concrete examples from flight_booking scenario
- Show both simple and complex cases
- Reference the models in `models.py`

#### Paso 2: Document Each Data Structure

**Contenido específico para cada sección:**

**user_message**:
```markdown
### 1. user_message: str

Raw user input message to analyze.

**Type**: `str`

**Examples**:
- `"I want to book a flight"` (intent initiation)
- `"Madrid"` (slot value response)
- `"No, I meant Barcelona"` (correction)
- `"Yes, that's correct"` (confirmation)
- `"What destinations are available?"` (digression)
```

**history**:
```markdown
### 2. history: dspy.History

Conversation history as a list of message dictionaries.

**Type**: `dspy.History` (contains list of message dicts)

**Structure**:
```python
History(messages=[
    {"role": "user", "content": "message text"},
    {"role": "assistant", "content": "response text"},
    ...
])
```

**Example** (flight booking):
```python
History(messages=[
    {"role": "user", "content": "I want to book a flight"},
    {"role": "assistant", "content": "Where would you like to fly to?"},
    {"role": "user", "content": "Madrid"}
])
```

**Notes**:
- Messages are ordered chronologically (oldest first)
- Only user/assistant roles are used
- Content is always a string
```

**context**:
```markdown
### 3. context: DialogueContext

Current dialogue state providing context for NLU analysis.

**Type**: `DialogueContext` (Pydantic model, see `models.py:84`)

**Fields**:
- `current_flow` (str): Active flow name (e.g., "book_flight", "none")
- `expected_slots` (list[str]): Slots expected in current flow
- `current_slots` (dict[str, Any]): Already filled slots {slot_name: value}
- `current_prompted_slot` (str | None): Slot being explicitly asked for
- `conversation_state` (str | None): Current conversation phase
- `available_flows` (dict[str, str]): Available flows {name: description}
- `available_actions` (list[str]): Available action names

**Example** (waiting for destination):
```python
DialogueContext(
    current_flow="book_flight",
    expected_slots=["destination", "departure_date", "return_date"],
    current_slots={},
    current_prompted_slot="destination",
    conversation_state="waiting_for_slot",
    available_flows={
        "book_flight": "Book a flight from origin to destination",
        "cancel_booking": "Cancel an existing booking"
    },
    available_actions=["search_flights", "confirm_booking"]
)
```

**Example** (confirming values):
```python
DialogueContext(
    current_flow="book_flight",
    expected_slots=["destination", "departure_date", "return_date"],
    current_slots={
        "destination": "Madrid",
        "departure_date": "2025-12-15",
        "return_date": "2025-12-20"
    },
    current_prompted_slot=None,
    conversation_state="confirming",
    available_flows={...},
    available_actions=[...]
)
```

**Key Usage Notes**:
- Use `conversation_state` to determine if user is responding to confirmation
- Use `current_prompted_slot` to prioritize which slot user is providing
- Check `current_slots` to detect corrections (new value != existing value)
- Use `expected_slots` to validate extracted slot names
- Use `available_flows` descriptions to map user intent to flow name
```

**current_datetime**:
```markdown
### 4. current_datetime: str

Current timestamp in ISO 8601 format for resolving temporal expressions.

**Type**: `str`

**Format**: ISO 8601 (YYYY-MM-DDTHH:MM:SS)

**Examples**:
- `"2025-12-11T10:30:00"`
- `"2025-01-15T14:22:15"`

**Usage**:
Used to resolve relative dates like:
- "tomorrow" → calculate based on current_datetime
- "next Monday" → calculate based on current_datetime
- "in 3 days" → calculate based on current_datetime
```

#### Paso 3: Document Output Structure

**NLUOutput documentation:**

```markdown
## Output Structure

### NLUOutput

Structured NLU analysis result.

**Type**: `NLUOutput` (Pydantic model, see `models.py:53`)

**Fields**:
- `message_type` (MessageType): Classification of message intent
- `command` (str | None): Intent/flow name for intent changes, None for slot values
- `slots` (list[SlotValue]): Extracted slot values with metadata
- `confidence` (float): Overall confidence score (0.0-1.0)
- `confirmation_value` (bool | None): For CONFIRMATION type only - True=yes, False=no, None=unclear

**Examples by MessageType**:

**SLOT_VALUE** (providing slot value):
```python
NLUOutput(
    message_type=MessageType.SLOT_VALUE,
    command=None,
    slots=[
        SlotValue(
            name="destination",
            value="Madrid",
            confidence=0.95,
            action=SlotAction.PROVIDE,
            previous_value=None
        )
    ],
    confidence=0.95,
    confirmation_value=None
)
```

**CORRECTION** (fixing previous value):
```python
NLUOutput(
    message_type=MessageType.CORRECTION,
    command=None,
    slots=[
        SlotValue(
            name="destination",
            value="Barcelona",
            confidence=0.90,
            action=SlotAction.CORRECT,
            previous_value="Madrid"
        )
    ],
    confidence=0.90,
    confirmation_value=None
)
```

**CONFIRMATION** (responding to confirmation prompt):
```python
NLUOutput(
    message_type=MessageType.CONFIRMATION,
    command=None,
    slots=[],
    confidence=0.95,
    confirmation_value=True  # User confirmed
)
```

**INTERRUPTION** (changing intent):
```python
NLUOutput(
    message_type=MessageType.INTERRUPTION,
    command="cancel_booking",
    slots=[],
    confidence=0.90,
    confirmation_value=None
)
```

**DIGRESSION** (asking question):
```python
NLUOutput(
    message_type=MessageType.DIGRESSION,
    command=None,
    slots=[],
    confidence=0.85,
    confirmation_value=None
)
```

### SlotValue

Individual extracted slot with metadata.

**Fields**:
- `name` (str): Slot name - must be in context.expected_slots
- `value` (Any): Extracted value
- `confidence` (float): Extraction confidence (0.0-1.0)
- `action` (SlotAction): What this slot represents (provide/correct/modify/confirm)
- `previous_value` (Any | None): Previous value if correction/modification

**See examples above in NLUOutput.**
```

#### Paso 4: Add Complete Example Flow

```markdown
## Complete Example Flow

### Scenario: User booking flight to Madrid

**Initial State**:
- User has started booking flow
- System is asking for destination

**Input**:
```python
user_message = "I want to fly to Madrid tomorrow"

history = History(messages=[
    {"role": "user", "content": "I want to book a flight"},
    {"role": "assistant", "content": "Where would you like to fly to?"},
])

context = DialogueContext(
    current_flow="book_flight",
    expected_slots=["destination", "departure_date", "return_date"],
    current_slots={},
    current_prompted_slot="destination",
    conversation_state="waiting_for_slot",
    available_flows={"book_flight": "Book a flight..."},
    available_actions=["search_flights"]
)

current_datetime = "2025-12-11T10:00:00"
```

**Expected Output**:
```python
NLUOutput(
    message_type=MessageType.SLOT_VALUE,
    command=None,
    slots=[
        SlotValue(
            name="destination",
            value="Madrid",
            confidence=0.95,
            action=SlotAction.PROVIDE,
            previous_value=None
        ),
        SlotValue(
            name="departure_date",
            value="2025-12-12",  # "tomorrow" resolved
            confidence=0.90,
            action=SlotAction.PROVIDE,
            previous_value=None
        )
    ],
    confidence=0.92,
    confirmation_value=None
)
```

**Analysis**:
- Message type: SLOT_VALUE (user providing values, not changing intent)
- Command: None (not a new intent)
- Slots: Extracted both destination and departure_date
  - Destination: "Madrid" (explicit in message)
  - Departure date: "2025-12-12" (resolved "tomorrow" using current_datetime)
- Actions: Both PROVIDE (new values, not corrections)
- Confidence: High (clear extraction)
```

#### Paso 5: Add Module-Level Reference in signatures.py

**Archivo a modificar:** `src/soni/du/signatures.py`

**Cambio:**

Añadir al inicio del archivo (después de imports):

```python
"""DSPy signatures for Dialogue Understanding.

For detailed developer documentation of data structures used in these signatures,
see DATA_STRUCTURES.md in this directory.

Note: Signature class docstrings are sent to the LLM and must be self-contained.
      DATA_STRUCTURES.md is for developer reference only.
"""
```

**IMPORTANT:**
- Add reference ONLY in module-level docstring (for developers reading code)
- DO NOT add reference in DialogueUnderstanding class docstring (sent to LLM)
- The class docstring must be self-contained (see task-335 for refactoring)

### Exception: Test-After

**Reason for test-after:**
- [x] Other: Documentation task - no implementation code

**Justification:**
This is a documentation task that creates reference material. No tests are needed as there is no executable code to test.

### Tests Requeridos

N/A - Documentation task

### Criterios de Éxito

- [ ] DATA_STRUCTURES.md created with all sections
- [ ] All input structures documented with examples
- [ ] All output structures documented with examples
- [ ] Complete example flow included
- [ ] Module-level reference comment added to signatures.py (for developers)
- [ ] NO reference to DATA_STRUCTURES.md in DialogueUnderstanding class docstring (LLM won't see it)
- [ ] Documentation is clear, comprehensive, and in English
- [ ] Examples use flight_booking scenario for consistency
- [ ] All Pydantic models referenced correctly (with file:line references)

### Validación Manual

**Comandos para validar:**

```bash
# Verify file exists and is well-formed markdown
cat src/soni/du/DATA_STRUCTURES.md

# Verify module-level reference added to signatures.py
grep -A 2 "DATA_STRUCTURES.md" src/soni/du/signatures.py

# Verify NO reference in class docstring (should return nothing)
grep -A 30 "class DialogueUnderstanding" src/soni/du/signatures.py | grep "DATA_STRUCTURES"

# Check markdown formatting
uv run python -m markdown src/soni/du/DATA_STRUCTURES.md > /dev/null
```

**Resultado esperado:**
- DATA_STRUCTURES.md displays complete documentation
- Module-level reference found in signatures.py
- NO reference found in DialogueUnderstanding class docstring
- Markdown parses without errors

### Referencias

- `src/soni/du/models.py` - Pydantic models definitions
- `src/soni/du/signatures.py` - Current signature implementation
- `ref/dspy/dspy/adapters/types/history.py` - dspy.History implementation
- `examples/flight_booking/soni.yaml` - Example scenario for concrete examples

### Notas Adicionales

- Use flight_booking as the canonical example throughout
- Keep examples simple but realistic
- This documentation will be referenced by subsequent tasks (335-337)
- Consider this the foundation for improving signature docstrings
