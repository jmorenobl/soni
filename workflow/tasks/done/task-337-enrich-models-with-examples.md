## Task: 337 - Enrich NLU Models with Examples and Documentation

**ID de tarea:** 337
**Hito:** NLU Improvements
**Dependencias:** task-334 (DATA_STRUCTURES.md for consistency)
**Duración estimada:** 2-3 horas

### Objetivo

Enhance documentation in `src/soni/du/models.py` by adding concrete examples to enums and model docstrings, explaining when to use each value, and documenting relationships between models.

### Contexto

The current models.py file (src/soni/du/models.py) has minimal documentation:
- Enums have brief one-line comments
- No examples showing which user messages correspond to each MessageType
- No guidance on when to use each SlotAction
- Relationships between models not documented (e.g., confirmation_value only used with CONFIRMATION)

Good model documentation should include:
- Concrete examples for each enum value
- Explanation of when/why to use each value
- Relationships between fields (e.g., which fields are used together)
- Edge cases and special considerations

This helps:
- DSPy optimizer understand what each type represents
- Developers understand the data model
- Maintain consistency in NLU outputs
- Debug issues more easily

### Entregables

- [ ] Enhanced MessageType enum with examples
- [ ] Enhanced SlotAction enum with examples
- [ ] Enhanced SlotValue model documentation
- [ ] Enhanced NLUOutput model documentation
- [ ] Enhanced DialogueContext model documentation
- [ ] Documented relationships between models
- [ ] All documentation in English

### Implementación Detallada

#### Paso 1: Enhance MessageType Enum

**Archivo a modificar:** `src/soni/du/models.py`

**Current MessageType (lines 9-21):**
```python
class MessageType(str, Enum):
    """Type of user message."""

    SLOT_VALUE = "slot_value"  # Direct answer to current prompt
    CORRECTION = "correction"  # Fixing a previous value
    MODIFICATION = "modification"  # Requesting to change a slot
    INTERRUPTION = "interruption"  # New intent/flow
    DIGRESSION = "digression"  # Question without flow change
    CLARIFICATION = "clarification"  # Asking for explanation
    CANCELLATION = "cancellation"  # Wants to stop
    CONFIRMATION = "confirmation"  # Yes/no to confirm prompt
    CONTINUATION = "continuation"  # General continuation
```

**Enhanced MessageType:**
```python
class MessageType(str, Enum):
    """Classification of user message based on dialogue context and intent.

    The message type determines how the dialogue manager processes the user's input.
    It is inferred from the message content combined with the conversation state.

    Examples below use flight booking scenario for clarity.
    """

    SLOT_VALUE = "slot_value"
    """Direct answer to current slot prompt.

    User is providing a value for the slot being asked about.

    Examples:
        - System: "Where would you like to fly to?"
        - User: "Madrid" → SLOT_VALUE (providing destination)

        - System: "When do you want to depart?"
        - User: "tomorrow" → SLOT_VALUE (providing departure_date)

    Context indicators:
        - conversation_state = "waiting_for_slot"
        - current_prompted_slot is set
        - Message contains value matching expected slot type

    Expected NLUOutput:
        - message_type = SLOT_VALUE
        - command = None
        - slots = [one or more SlotValue with action=PROVIDE]
        - confirmation_value = None
    """

    CORRECTION = "correction"
    """User is correcting a previously provided value (reactive).

    This is a reactive correction - user realizes previous value was wrong
    and provides the correct value. Usually triggered by phrases like
    "No, I meant...", "Actually it's...", "I said X but I meant Y".

    Examples:
        - System: "You want to fly to Madrid, correct?"
        - User: "No, I meant Barcelona" → CORRECTION

        - System: "Departure date is tomorrow, is that right?"
        - User: "Actually, I want to leave next Monday" → CORRECTION

    Context indicators:
        - Negative confirmation response
        - Phrases: "no", "actually", "I meant", "wrong"
        - Slot already exists in current_slots
        - New value differs from existing value

    Expected NLUOutput:
        - message_type = CORRECTION
        - command = None
        - slots = [SlotValue with action=CORRECT, previous_value set]
        - confirmation_value = None

    Note:
        Different from MODIFICATION (proactive request to change).
    """

    MODIFICATION = "modification"
    """User is requesting to modify a slot value (proactive).

    This is a proactive request - user explicitly asks to change a value
    that was previously confirmed. Usually phrased as a request:
    "Can I change...", "I want to modify...", "Change X to Y".

    Examples:
        - User: "Can I change the destination to London?" → MODIFICATION
        - User: "I want to modify the departure date" → MODIFICATION
        - User: "Change the return date to next Friday" → MODIFICATION

    Context indicators:
        - Request phrases: "change", "modify", "update", "can I..."
        - Slot already exists in current_slots
        - User initiates the change (not responding to question)

    Expected NLUOutput:
        - message_type = MODIFICATION
        - command = None
        - slots = [SlotValue with action=MODIFY, previous_value set]
        - confirmation_value = None

    Note:
        Different from CORRECTION (reactive, error-based).
    """

    INTERRUPTION = "interruption"
    """User is changing intent/flow mid-conversation.

    User wants to switch to a different flow or intent while in the middle
    of another flow. This causes flow stack changes.

    Examples:
        - During flight booking:
        - User: "Actually, I want to cancel my booking instead" → INTERRUPTION
        - User: "Never mind, I want to check flight status" → INTERRUPTION

    Context indicators:
        - User initiates new intent/flow
        - Different from current_flow
        - Phrases: "actually", "instead", "I want to...", "let's..."

    Expected NLUOutput:
        - message_type = INTERRUPTION
        - command = new_flow_name (e.g., "cancel_booking")
        - slots = [] (usually empty)
        - confirmation_value = None

    Note:
        Causes flow stack push/pop (handled by dialogue manager).
    """

    DIGRESSION = "digression"
    """User asks question without changing flow.

    User asks for information or help while staying in the current flow.
    Does NOT change flow stack.

    Examples:
        - During flight booking:
        - User: "What destinations do you fly to?" → DIGRESSION
        - User: "Can you explain the baggage policy?" → DIGRESSION
        - User: "How much does a ticket cost?" → DIGRESSION

    Context indicators:
        - Question format: "what", "how", "can you", "tell me"
        - No intent to change flow
        - Informational request

    Expected NLUOutput:
        - message_type = DIGRESSION
        - command = None
        - slots = [] (usually empty)
        - confirmation_value = None

    Note:
        DigressionHandler processes without modifying flow stack.
    """

    CLARIFICATION = "clarification"
    """User asks for explanation or help about current step.

    User doesn't understand current prompt and asks for clarification.

    Examples:
        - System: "Where would you like to fly to?"
        - User: "What destinations are available?" → CLARIFICATION
        - User: "I don't understand" → CLARIFICATION
        - User: "Can you explain that?" → CLARIFICATION

    Context indicators:
        - Phrases: "what do you mean", "I don't understand", "explain", "help"
        - Related to current step/prompt
        - Not providing a value

    Expected NLUOutput:
        - message_type = CLARIFICATION
        - command = None
        - slots = []
        - confirmation_value = None
    """

    CANCELLATION = "cancellation"
    """User wants to cancel/abort current flow.

    User wants to stop the current process entirely.

    Examples:
        - User: "Cancel" → CANCELLATION
        - User: "Never mind" → CANCELLATION
        - User: "I want to stop" → CANCELLATION
        - User: "Exit" → CANCELLATION

    Context indicators:
        - Phrases: "cancel", "stop", "never mind", "exit", "abort"
        - Intent to terminate current flow

    Expected NLUOutput:
        - message_type = CANCELLATION
        - command = "cancel" or None
        - slots = []
        - confirmation_value = None
    """

    CONFIRMATION = "confirmation"
    """User responding to confirmation prompt (yes/no).

    User is confirming or denying values proposed by system.
    ONLY when conversation_state = "confirming" or "ready_for_confirmation".

    Examples:
        - System: "You want to fly to Madrid on 2025-12-15. Is that correct?"
        - User: "Yes" → CONFIRMATION (confirmation_value=True)
        - User: "That's right" → CONFIRMATION (confirmation_value=True)
        - User: "No" → CONFIRMATION (confirmation_value=False)
        - User: "Not quite" → CONFIRMATION (confirmation_value=False)

    Context indicators:
        - conversation_state = "confirming" or "ready_for_confirmation"
        - User message is yes/no response
        - Phrases: "yes", "no", "correct", "wrong", "that's right"

    Expected NLUOutput:
        - message_type = CONFIRMATION
        - command = None
        - slots = [] (unless correcting specific slot)
        - confirmation_value = True | False | None
          * True: User confirmed
          * False: User denied
          * None: Ambiguous response

    Note:
        CRITICAL: confirmation_value should ONLY be set for CONFIRMATION type.
        For all other types, confirmation_value should be None.
    """

    CONTINUATION = "continuation"
    """General continuation message without specific classification.

    Catch-all for messages that don't fit other categories but indicate
    user wants to continue the conversation.

    Examples:
        - User: "Okay" → CONTINUATION
        - User: "Sure" → CONTINUATION
        - User: "Go ahead" → CONTINUATION

    Context indicators:
        - General affirmative without specific intent
        - Not fitting other categories

    Expected NLUOutput:
        - message_type = CONTINUATION
        - command = None
        - slots = []
        - confirmation_value = None
    """
```

**Explicación:**
- Each enum value now has detailed docstring
- Includes concrete examples from flight_booking
- Explains context indicators (how to detect)
- Shows expected NLUOutput structure for each type
- Documents edge cases and notes
- Clear distinction between similar types (CORRECTION vs MODIFICATION)

#### Paso 2: Enhance SlotAction Enum

**Current SlotAction (lines 23-34):**
```python
class SlotAction(str, Enum):
    """Action type for each individual slot extraction.

    This distinguishes between providing a new value vs correcting/modifying an existing one.
    Critical for proper dialogue management.
    """

    PROVIDE = "provide"  # Providing new slot value
    CORRECT = "correct"  # Correcting previous value (reactive)
    MODIFY = "modify"  # Explicitly requesting modification (proactive)
    CONFIRM = "confirm"  # Confirming a value
```

**Enhanced SlotAction:**
```python
class SlotAction(str, Enum):
    """Action type for individual slot extraction.

    Distinguishes between providing new values vs correcting/modifying existing ones.
    This is critical for dialogue management to handle slot changes correctly.

    The action is determined by:
    1. Whether slot already exists in current_slots
    2. Message type (CORRECTION, MODIFICATION, etc.)
    3. User intent (providing vs changing)
    """

    PROVIDE = "provide"
    """Providing a new slot value for the first time.

    Used when slot doesn't exist in current_slots yet.

    Examples:
        - System: "Where do you want to fly?"
        - User: "Madrid" → SlotValue(name="destination", value="Madrid", action=PROVIDE)

        - User: "I want to fly to Barcelona tomorrow"
          → SlotValue(name="destination", value="Barcelona", action=PROVIDE)
          → SlotValue(name="departure_date", value="2025-12-12", action=PROVIDE)

    Context:
        - Slot name NOT in current_slots
        - Or slot in current_slots but value is None/empty
        - Message type usually SLOT_VALUE

    Fields:
        - previous_value = None (no previous value)
    """

    CORRECT = "correct"
    """Correcting a previously provided value (reactive).

    Used when user realizes previous value was wrong and provides correction.
    Triggered by negative confirmation or correction phrases.

    Examples:
        - current_slots = {"destination": "Madrid"}
        - User: "No, I meant Barcelona"
          → SlotValue(name="destination", value="Barcelona", action=CORRECT, previous_value="Madrid")

        - System: "Departure is tomorrow, correct?"
        - User: "No, next Monday"
          → SlotValue(name="departure_date", value="2025-12-16", action=CORRECT, previous_value="2025-12-12")

    Context:
        - Slot already exists in current_slots
        - Message type = CORRECTION
        - User is reacting to error/misunderstanding
        - Phrases: "no", "actually", "I meant"

    Fields:
        - previous_value = current_slots[slot_name] (must be set)
    """

    MODIFY = "modify"
    """Explicitly requesting to modify a value (proactive).

    Used when user proactively requests to change a previously confirmed value.
    This is different from CORRECT (reactive error fix).

    Examples:
        - current_slots = {"destination": "Madrid", "departure_date": "2025-12-15"}
        - User: "Can I change the destination to London?"
          → SlotValue(name="destination", value="London", action=MODIFY, previous_value="Madrid")

        - User: "I want to modify the departure date to next week"
          → SlotValue(name="departure_date", value="2025-12-18", action=MODIFY, previous_value="2025-12-15")

    Context:
        - Slot already exists in current_slots
        - Message type = MODIFICATION
        - User is making deliberate change (not error)
        - Phrases: "change", "modify", "update", "can I..."

    Fields:
        - previous_value = current_slots[slot_name] (must be set)
    """

    CONFIRM = "confirm"
    """Confirming an existing value (rare).

    Used when user explicitly confirms a slot value during confirmation phase.
    This is rarely used - usually entire confirmation is handled by message_type=CONFIRMATION
    with confirmation_value=True/False.

    Examples:
        - System: "Is Madrid correct for destination?"
        - User: "Yes, Madrid is correct"
          → SlotValue(name="destination", value="Madrid", action=CONFIRM)

    Context:
        - Slot already exists in current_slots
        - conversation_state = "confirming"
        - User explicitly confirms specific slot
        - Rare: usually confirmation is at message level, not slot level

    Fields:
        - previous_value = None or current_slots[slot_name]
    """
```

**Explicación:**
- Each action has detailed docstring
- Concrete examples showing when to use each
- Context indicators explained
- Field requirements documented (previous_value)
- Clear distinction between similar actions (CORRECT vs MODIFY)

#### Paso 3: Enhance SlotValue Model

**Current SlotValue (lines 36-51):**
```python
class SlotValue(BaseModel):
    """Extracted slot value with metadata."""

    name: str = Field(description="Slot name - MUST be one of the names in context.expected_slots")
    value: Any = Field(description="Extracted value from user message")
    confidence: float = Field(ge=0.0, le=1.0, description="Extraction confidence")
    action: SlotAction = Field(
        default=SlotAction.PROVIDE,
        description="What action this slot represents: provide new, correct previous, modify, confirm",
    )
    previous_value: Any | None = Field(
        default=None, description="Previous value if this is a correction/modification"
    )
```

**Enhanced SlotValue:**
```python
class SlotValue(BaseModel):
    """Individual slot extraction with metadata.

    Represents a single extracted slot value from user message, including
    what action the user is taking (provide new, correct, modify, confirm).

    Examples:
        Providing new value:
        >>> SlotValue(
        ...     name="destination",
        ...     value="Madrid",
        ...     confidence=0.95,
        ...     action=SlotAction.PROVIDE,
        ...     previous_value=None
        ... )

        Correcting existing value:
        >>> SlotValue(
        ...     name="destination",
        ...     value="Barcelona",
        ...     confidence=0.90,
        ...     action=SlotAction.CORRECT,
        ...     previous_value="Madrid"
        ... )
    """

    name: str = Field(
        description="Slot name - MUST be in context.expected_slots. "
        "Example: 'destination', 'departure_date', 'return_date'"
    )

    value: Any = Field(
        description="Extracted value from user message. "
        "Type depends on slot definition. "
        "Examples: 'Madrid' (str), '2025-12-15' (str for date), 2 (int for passengers)"
    )

    confidence: float = Field(
        ge=0.0,
        le=1.0,
        description="Extraction confidence (0.0-1.0). "
        "Higher is better. Typical: 0.8-0.95 for clear extractions, "
        "0.5-0.7 for ambiguous, <0.5 for very uncertain"
    )

    action: SlotAction = Field(
        default=SlotAction.PROVIDE,
        description="Action type for this slot: "
        "PROVIDE (new value), CORRECT (fix error), MODIFY (change), CONFIRM (affirm). "
        "Determines how dialogue manager processes this slot."
    )

    previous_value: Any | None = Field(
        default=None,
        description="Previous value if action is CORRECT or MODIFY. "
        "Must be None for PROVIDE. "
        "Example: If correcting 'Madrid' to 'Barcelona', previous_value='Madrid'"
    )
```

**Explicación:**
- Enhanced class docstring with examples
- Field descriptions more detailed
- Includes example values and types
- Explains confidence ranges
- Documents when previous_value should be set

#### Paso 4: Enhance NLUOutput Model

**Current NLUOutput (lines 53-81):**
```python
class NLUOutput(BaseModel):
    """Structured NLU output.

    Attributes:
        message_type: Type of user message (slot_value, confirmation, correction, etc.)
        command: User's intent or command for intent changes, cancellations, confirmations
        slots: List of extracted slot values with metadata
        confidence: Overall extraction confidence (0.0 to 1.0)
        confirmation_value: For CONFIRMATION messages - True=yes, False=no, None=unclear

    Note:
        The confirmation_value field is only relevant when message_type is CONFIRMATION.
        It should be None for all other message types.
    """

    message_type: MessageType = Field(description="Type of user message")
    command: str | None = Field(
        default=None,
        description="User's intent or command when changing intent, canceling, or confirming. None for slot value messages.",
    )
    slots: list[SlotValue] = Field(default_factory=list, description="Extracted slot values")
    confidence: float = Field(ge=0.0, le=1.0, description="Overall confidence")
    confirmation_value: bool | None = Field(
        default=None,
        description=(
            "For CONFIRMATION message_type: True if user confirmed (yes/correct/confirm), "
            "False if user denied (no/wrong/incorrect), None if unclear or not a confirmation message."
        ),
    )
```

**Enhanced NLUOutput:**
```python
class NLUOutput(BaseModel):
    """Complete NLU analysis result.

    Contains classification of message type, extracted slots, and metadata.
    This is the primary output of the SoniDU module.

    Field Relationships:
        - confirmation_value is ONLY set when message_type = CONFIRMATION
        - command is ONLY set when message_type = INTERRUPTION or CANCELLATION
        - slots is populated for SLOT_VALUE, CORRECTION, MODIFICATION
        - slots is usually empty for CONFIRMATION, DIGRESSION, CLARIFICATION

    Examples:
        Slot value extraction:
        >>> NLUOutput(
        ...     message_type=MessageType.SLOT_VALUE,
        ...     command=None,
        ...     slots=[SlotValue(name="destination", value="Madrid", ...)],
        ...     confidence=0.95,
        ...     confirmation_value=None
        ... )

        Confirmation response:
        >>> NLUOutput(
        ...     message_type=MessageType.CONFIRMATION,
        ...     command=None,
        ...     slots=[],
        ...     confidence=0.90,
        ...     confirmation_value=True  # User said yes
        ... )

        Intent change:
        >>> NLUOutput(
        ...     message_type=MessageType.INTERRUPTION,
        ...     command="cancel_booking",  # New intent
        ...     slots=[],
        ...     confidence=0.85,
        ...     confirmation_value=None
        ... )

    See Also:
        - MessageType: Enum with all message types and examples
        - SlotValue: Individual slot extraction
        - DATA_STRUCTURES.md: Complete data structure reference
    """

    message_type: MessageType = Field(
        description="Classification of user message. "
        "See MessageType enum for detailed examples of each type."
    )

    command: str | None = Field(
        default=None,
        description="User's intent/flow name when changing intent. "
        "Set for INTERRUPTION (new flow) and CANCELLATION (cancel flow). "
        "None for SLOT_VALUE, CORRECTION, CONFIRMATION, DIGRESSION, etc. "
        "Example: 'cancel_booking', 'check_status', 'book_flight'"
    )

    slots: list[SlotValue] = Field(
        default_factory=list,
        description="Extracted slot values with metadata. "
        "Can contain multiple slots if user provides several values in one message. "
        "Empty for CONFIRMATION, DIGRESSION, CLARIFICATION (usually)."
    )

    confidence: float = Field(
        ge=0.0,
        le=1.0,
        description="Overall NLU confidence (0.0-1.0). "
        "Aggregated from individual slot confidences. "
        "Typical: 0.8-0.95 for clear messages, 0.5-0.7 for ambiguous"
    )

    confirmation_value: bool | None = Field(
        default=None,
        description=(
            "ONLY for message_type=CONFIRMATION. "
            "True = User confirmed (yes/correct/right), "
            "False = User denied (no/wrong/incorrect), "
            "None = Unclear response or not a confirmation message. "
            "MUST be None for all other message types."
        ),
    )
```

**Explicación:**
- Enhanced class docstring with field relationships
- Multiple examples showing different message types
- Field descriptions more detailed
- Cross-references to MessageType enum
- References DATA_STRUCTURES.md
- Documents when fields are used/not used

#### Paso 5: Enhance DialogueContext Model

**Current DialogueContext (lines 84-105):**
```python
class DialogueContext(BaseModel):
    """Current dialogue context for NLU."""

    current_slots: dict[str, Any] = Field(default_factory=dict, description="Filled slots")
    available_actions: list[str] = Field(default_factory=list, description="Available actions")
    available_flows: dict[str, str] = Field(
        default_factory=dict, description="Available flows as {flow_name: description} mapping"
    )
    current_flow: str = Field(default="none", description="Active flow")
    expected_slots: list[str] = Field(default_factory=list, description="Expected slot names")
    current_prompted_slot: str | None = Field(
        default=None,
        description="Slot currently being prompted for - user's response should fill this slot",
    )
    conversation_state: str | None = Field(
        default=None,
        description=(
            "Current conversation state: idle, waiting_for_slot, confirming, "
            "ready_for_action, ready_for_confirmation, completed, etc."
        ),
    )
```

**Enhanced DialogueContext:**
```python
class DialogueContext(BaseModel):
    """Current dialogue state provided to NLU for context-aware analysis.

    This model provides all necessary context for the NLU to correctly interpret
    user messages. The same user message ("Madrid") can mean different things
    depending on the context (providing new value vs correcting).

    Examples:
        Waiting for slot:
        >>> DialogueContext(
        ...     current_flow="book_flight",
        ...     expected_slots=["destination", "departure_date"],
        ...     current_slots={},
        ...     current_prompted_slot="destination",
        ...     conversation_state="waiting_for_slot",
        ...     available_flows={"book_flight": "Book a flight..."},
        ...     available_actions=["search_flights"]
        ... )

        Confirming values:
        >>> DialogueContext(
        ...     current_flow="book_flight",
        ...     expected_slots=["destination", "departure_date"],
        ...     current_slots={"destination": "Madrid", "departure_date": "2025-12-15"},
        ...     current_prompted_slot=None,
        ...     conversation_state="confirming",
        ...     available_flows={...},
        ...     available_actions=["confirm_booking"]
        ... )
    """

    current_slots: dict[str, Any] = Field(
        default_factory=dict,
        description="Already filled slots {slot_name: value}. "
        "Used to detect corrections (new value != existing value). "
        "Example: {'destination': 'Madrid', 'departure_date': '2025-12-15'}"
    )

    available_actions: list[str] = Field(
        default_factory=list,
        description="Available action names in current context. "
        "Example: ['search_flights', 'confirm_booking', 'cancel_booking']"
    )

    available_flows: dict[str, str] = Field(
        default_factory=dict,
        description="Available flows as {flow_name: description}. "
        "Descriptions used for semantic matching of user intent. "
        "Example: {'book_flight': 'Book a flight to a destination', "
        "'cancel_booking': 'Cancel an existing flight booking'}"
    )

    current_flow: str = Field(
        default="none",
        description="Currently active flow name. "
        "'none' if no flow active. "
        "Example: 'book_flight', 'cancel_booking', 'none'"
    )

    expected_slots: list[str] = Field(
        default_factory=list,
        description="Slot names expected in current flow. "
        "NLU MUST only extract slots from this list. "
        "Example: ['destination', 'departure_date', 'return_date']"
    )

    current_prompted_slot: str | None = Field(
        default=None,
        description="Slot currently being asked for (if any). "
        "Helps NLU prioritize which slot user is providing. "
        "None if not explicitly prompting for a slot. "
        "Example: 'destination' when system asked 'Where do you want to fly?'"
    )

    conversation_state: str | None = Field(
        default=None,
        description=(
            "Current conversation phase. CRITICAL for determining message_type. "
            "Values: 'idle', 'waiting_for_slot', 'confirming', "
            "'ready_for_action', 'ready_for_confirmation', 'completed', etc. "
            "Example: 'confirming' → expect CONFIRMATION message_type"
        ),
    )
```

**Explicación:**
- Enhanced class docstring with purpose
- Multiple examples showing different states
- Field descriptions include examples
- Explains how fields are used by NLU
- Documents critical fields (conversation_state)

### Exception: Test-After

**Reason for test-after:**
- [x] Other: Documentation improvements - no code changes

**Justification:**
This task only enhances model docstrings and documentation. No executable code changes, so no new tests required.

### Tests Requeridos

N/A - Documentation task only

### Criterios de Éxito

- [ ] MessageType enum has examples for all values
- [ ] SlotAction enum has examples for all values
- [ ] SlotValue model has enhanced documentation with examples
- [ ] NLUOutput model has enhanced documentation with examples
- [ ] DialogueContext model has enhanced documentation with examples
- [ ] Relationships between models documented
- [ ] All examples use flight_booking scenario
- [ ] All documentation in English
- [ ] Cross-references added where appropriate

### Validación Manual

**Comandos para validar:**

```bash
# View enhanced model documentation
python -c "from soni.du.models import MessageType; help(MessageType)"
python -c "from soni.du.models import SlotAction; help(SlotAction)"
python -c "from soni.du.models import NLUOutput; help(NLUOutput)"

# Check for examples in docstrings
grep -A 3 "Examples:" src/soni/du/models.py | head -20

# Verify no Spanish text
grep -i "usuario\|sistema" src/soni/du/models.py

# Check docstring is well-formed
python -m pydoc soni.du.models
```

**Resultado esperado:**
- help() shows comprehensive documentation with examples
- Examples found in all major types
- No Spanish text
- pydoc renders cleanly

### Referencias

- `src/soni/du/models.py` - File to enhance
- `src/soni/du/DATA_STRUCTURES.md` - Reference documentation (task-334)
- `examples/flight_booking/soni.yaml` - Example scenario
- Pydantic documentation: https://docs.pydantic.dev/

### Notas Adicionales

- Use flight_booking scenario consistently for all examples
- Make examples concrete and realistic (not abstract)
- Explain relationships between types (e.g., confirmation_value only with CONFIRMATION)
- Cross-reference related types and documentation
- Keep examples simple but illustrative
