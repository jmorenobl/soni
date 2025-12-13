## Task: 202 - Implement Confirmation Value Extraction in NLU Module

**ID de tarea:** 202
**Hito:** Confirmation Flow Fix
**Dependencias:** Task 201 (Add confirmation_value field)
**Duración estimada:** 4-6 horas

### Objetivo

Implement the logic in the NLU module (DSPy-based SoniDU or NLU provider) to extract `confirmation_value` (True/False/None) from user messages when the message type is CONFIRMATION.

### Contexto

After adding the `confirmation_value` field to the NLUOutput model (Task 201), we need to implement the actual extraction logic. The NLU module must:

1. Detect when the user is responding to a confirmation request (message_type = CONFIRMATION)
2. Analyze the user's response to determine if they confirmed (yes), denied (no), or gave an unclear response
3. Set the `confirmation_value` field accordingly

Currently, the NLU detects `message_type = CONFIRMATION` but doesn't extract the yes/no value, causing the infinite loop.

**References:**
- Analysis: `docs/analysis/ANALISIS_ERROR_CONFIRMACION.md`
- NLU module: `src/soni/du/modules.py`
- DialogueContext: `src/soni/du/models.py:65-79`

### Entregables

- [ ] Update DSPy signature to include confirmation_value output
- [ ] Add confirmation extraction logic to SoniDU forward method
- [ ] Update DialogueContext to include confirmation state hint
- [ ] Handle common yes/no variations (yes, no, confirm, correct, wrong, etc.)
- [ ] Set confidence appropriately for confirmation extraction
- [ ] Add comprehensive unit tests for confirmation extraction

### Implementación Detallada

#### Paso 1: Update DSPy Signature

**Archivo(s) a modificar:** `src/soni/du/modules.py`

**Código específico:**

```python
class UnderstandSignature(dspy.Signature):
    """Understand user message in dialogue context.

    When message_type is CONFIRMATION:
    - Extract confirmation_value: True if user confirms (yes/correct/confirm/that's right)
    - Extract confirmation_value: False if user denies (no/wrong/incorrect/not right)
    - Extract confirmation_value: None if unclear or ambiguous
    """

    user_message: str = dspy.InputField(
        description="The user's message to understand"
    )

    context: str = dspy.InputField(
        description=(
            "Current dialogue context including:\n"
            "- Active flow and current prompted slot\n"
            "- Available flows and their descriptions\n"
            "- Previously collected slots\n"
            "- Conversation state (idle, waiting_for_slot, confirming, etc.)"
        )
    )

    message_type: MessageType = dspy.OutputField(
        description=(
            "Type of user message:\n"
            "- slot_value: Direct answer to current prompt\n"
            "- confirmation: Yes/no response to confirmation request\n"
            "- correction: Fixing a previous value\n"
            "- modification: Requesting to change a slot\n"
            "- interruption: New intent/flow\n"
            "- digression: Question without flow change\n"
            "- clarification: Asking for explanation\n"
            "- cancellation: Wants to stop\n"
            "- continuation: General continuation"
        )
    )

    command: str = dspy.OutputField(
        description="User's intent or command (flow name for intent changes, None otherwise)"
    )

    slots: list[SlotValue] = dspy.OutputField(
        description="Extracted slot values with metadata"
    )

    confidence: float = dspy.OutputField(
        description="Overall confidence (0.0 to 1.0)"
    )

    # ✅ ADD THIS FIELD
    confirmation_value: bool | None = dspy.OutputField(
        description=(
            "For CONFIRMATION message_type ONLY:\n"
            "- True: User confirms (yes/correct/confirm/that's right/sounds good/perfect/etc.)\n"
            "- False: User denies (no/wrong/incorrect/not right/not correct/change it/etc.)\n"
            "- None: Unclear, ambiguous, or not a confirmation message\n"
            "For all other message types, this should be None."
        )
    )
```

**Explicación:**
- Add `confirmation_value` as output field in the DSPy signature
- Provide detailed description with examples of yes/no phrases
- Explicitly state it should be None for non-confirmation messages
- This guides the LLM to extract the correct value

#### Paso 2: Update DialogueContext for Confirmation State

**Archivo(s) a modificar:** `src/soni/du/models.py`

**Código específico:**

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

    # ✅ ADD THIS FIELD
    conversation_state: str | None = Field(
        default=None,
        description=(
            "Current conversation state: idle, waiting_for_slot, confirming, "
            "ready_for_action, ready_for_confirmation, completed, etc."
        ),
    )
```

**Explicación:**
- Add `conversation_state` to DialogueContext so NLU knows when we're in confirming state
- This helps the NLU detect that a confirmation response is expected
- When `conversation_state = "confirming"`, NLU should prioritize detecting message_type=CONFIRMATION

#### Paso 3: Update understand_node to pass conversation_state

**Archivo(s) a modificar:** `src/soni/dm/nodes/understand.py`

**Localizar línea donde se crea DialogueContext:**

```python
# Current code (approximate location)
context = DialogueContext(
    current_slots=slots,
    available_actions=available_actions,
    available_flows=available_flows,
    current_flow=current_flow,
    expected_slots=expected_slots,
    current_prompted_slot=current_prompted_slot,
)

# ✅ ADD conversation_state
context = DialogueContext(
    current_slots=slots,
    available_actions=available_actions,
    available_flows=available_flows,
    current_flow=current_flow,
    expected_slots=expected_slots,
    current_prompted_slot=current_prompted_slot,
    conversation_state=state.get("conversation_state"),  # ✅ Add this
)
```

**Explicación:**
- Pass the conversation_state from dialogue state to DialogueContext
- This allows NLU to know when we're expecting a confirmation response
- Helps NLU prioritize CONFIRMATION detection when conversation_state="confirming"

#### Paso 4: Implement confirmation extraction in SoniDU

**Archivo(s) a modificar:** `src/soni/du/modules.py`

**Código específico:**

```python
class SoniDU(dspy.Module):
    """Dialogue Understanding module using DSPy."""

    def __init__(self, use_cot: bool = False):
        super().__init__()
        self.use_cot = use_cot

        if use_cot:
            self.understand = dspy.ChainOfThought(UnderstandSignature)
        else:
            self.understand = dspy.Predict(UnderstandSignature)

    def forward(
        self,
        user_message: str,
        context: DialogueContext,
    ) -> NLUOutput:
        """Process user message with dialogue context.

        Args:
            user_message: User's input message
            context: Current dialogue context

        Returns:
            Structured NLU output with message type, slots, and confirmation value
        """
        # Build context string
        context_str = self._build_context_string(context)

        # Call DSPy module
        result = self.understand(user_message=user_message, context=context_str)

        # Extract fields
        message_type = result.message_type
        command = result.command if hasattr(result, "command") else None
        slots = result.slots if hasattr(result, "slots") else []
        confidence = float(result.confidence) if hasattr(result, "confidence") else 0.8

        # ✅ ADD confirmation_value extraction
        confirmation_value = None
        if hasattr(result, "confirmation_value"):
            # DSPy may return string "True"/"False"/"None" or actual bool
            cv = result.confirmation_value
            if isinstance(cv, bool):
                confirmation_value = cv
            elif isinstance(cv, str):
                if cv.lower() in ("true", "yes", "confirmed"):
                    confirmation_value = True
                elif cv.lower() in ("false", "no", "denied"):
                    confirmation_value = False
                else:
                    confirmation_value = None
            # If cv is None, confirmation_value stays None

        # ✅ ADD validation: confirmation_value should only be set for CONFIRMATION messages
        if message_type != MessageType.CONFIRMATION:
            confirmation_value = None

        # Build NLUOutput
        return NLUOutput(
            message_type=message_type,
            command=command,
            slots=slots,
            confidence=confidence,
            confirmation_value=confirmation_value,  # ✅ Include this
        )
```

**Explicación:**
- Extract `confirmation_value` from DSPy result
- Handle type conversion (DSPy may return string or bool)
- Validate that `confirmation_value` is only set when message_type=CONFIRMATION
- Set to None for all other message types

#### Paso 5: Add post-processing for confirmation confidence

**Archivo(s) a modificar:** `src/soni/du/modules.py`

**Código adicional en forward method:**

```python
# ✅ ADD confidence adjustment for confirmation
# If message_type is CONFIRMATION but confirmation_value is None (unclear),
# lower the confidence to reflect uncertainty
if message_type == MessageType.CONFIRMATION and confirmation_value is None:
    # Unclear confirmation - lower confidence
    confidence = min(confidence, 0.6)
    logger.warning(
        f"Confirmation detected but value unclear (message: '{user_message}'). "
        f"Setting confidence to {confidence}"
    )
```

**Explicación:**
- When NLU detects CONFIRMATION but can't determine yes/no, lower confidence
- This signals to downstream nodes that the confirmation is ambiguous
- The handle_confirmation_node will ask again if confidence is low or value is None

### Tests Requeridos

**Archivo de tests:** `tests/unit/test_soni_du_confirmation.py`

**Tests específicos a implementar:**

```python
import pytest
from soni.du.models import DialogueContext, MessageType, NLUOutput
from soni.du.modules import SoniDU


@pytest.fixture
def du_module():
    """Create SoniDU module for testing."""
    return SoniDU(use_cot=False)


@pytest.fixture
def confirming_context():
    """Create context for confirmation state."""
    return DialogueContext(
        current_slots={
            "origin": "Madrid",
            "destination": "Barcelona",
            "departure_date": "2025-12-10"
        },
        current_flow="book_flight",
        conversation_state="confirming",
        available_flows={"book_flight": "Book a flight"},
        expected_slots=["origin", "destination", "departure_date"],
    )


# Test 1: Extract confirmation_value=True for "yes"
@pytest.mark.asyncio
async def test_confirmation_yes(du_module, confirming_context):
    """Test that 'yes' is extracted as confirmation_value=True"""
    # Arrange
    user_message = "Yes, please confirm"

    # Act
    result = du_module(user_message=user_message, context=confirming_context)

    # Assert
    assert isinstance(result, NLUOutput)
    assert result.message_type == MessageType.CONFIRMATION
    assert result.confirmation_value is True
    assert result.confidence > 0.8


# Test 2: Extract confirmation_value=True for variations
@pytest.mark.parametrize("message", [
    "yes",
    "Yes",
    "YES",
    "confirm",
    "correct",
    "that's right",
    "sounds good",
    "perfect",
    "absolutely",
    "sure",
    "ok",
    "okay",
])
@pytest.mark.asyncio
async def test_confirmation_yes_variations(du_module, confirming_context, message):
    """Test various ways of saying 'yes'"""
    result = du_module(user_message=message, context=confirming_context)
    assert result.message_type == MessageType.CONFIRMATION
    assert result.confirmation_value is True


# Test 3: Extract confirmation_value=False for "no"
@pytest.mark.asyncio
async def test_confirmation_no(du_module, confirming_context):
    """Test that 'no' is extracted as confirmation_value=False"""
    result = du_module(user_message="No, that's not correct", context=confirming_context)
    assert result.message_type == MessageType.CONFIRMATION
    assert result.confirmation_value is False


# Test 4: Extract confirmation_value=False for variations
@pytest.mark.parametrize("message", [
    "no",
    "No",
    "NO",
    "not correct",
    "wrong",
    "incorrect",
    "that's wrong",
    "change it",
    "not right",
])
@pytest.mark.asyncio
async def test_confirmation_no_variations(du_module, confirming_context, message):
    """Test various ways of saying 'no'"""
    result = du_module(user_message=message, context=confirming_context)
    assert result.message_type == MessageType.CONFIRMATION
    assert result.confirmation_value is False


# Test 5: Extract confirmation_value=None for unclear
@pytest.mark.parametrize("message", [
    "maybe",
    "I'm not sure",
    "hmm",
    "let me think",
    "can you repeat that?",
])
@pytest.mark.asyncio
async def test_confirmation_unclear(du_module, confirming_context, message):
    """Test that unclear responses have confirmation_value=None"""
    result = du_module(user_message=message, context=confirming_context)
    # May be detected as CONFIRMATION or CLARIFICATION
    if result.message_type == MessageType.CONFIRMATION:
        assert result.confirmation_value is None
        assert result.confidence <= 0.6  # Low confidence for unclear


# Test 6: confirmation_value is None for non-confirmation messages
@pytest.mark.asyncio
async def test_confirmation_value_none_for_other_types(du_module):
    """Test that confirmation_value is None when message_type is not CONFIRMATION"""
    # Arrange
    context = DialogueContext(
        current_flow="book_flight",
        conversation_state="waiting_for_slot",
        current_prompted_slot="origin",
        expected_slots=["origin", "destination", "departure_date"],
    )

    # Act - slot value message
    result = du_module(user_message="Madrid", context=context)

    # Assert
    assert result.message_type == MessageType.SLOT_VALUE
    assert result.confirmation_value is None  # Should be None for slot_value


# Test 7: Detect confirmation in confirming state
@pytest.mark.asyncio
async def test_confirmation_prioritized_in_confirming_state(du_module, confirming_context):
    """Test that CONFIRMATION is detected when conversation_state='confirming'"""
    # When in confirming state, even simple "yes" should be CONFIRMATION not SLOT_VALUE
    result = du_module(user_message="yes", context=confirming_context)
    assert result.message_type == MessageType.CONFIRMATION
    assert result.confirmation_value is True
```

### Criterios de Éxito

- [ ] DSPy signature includes `confirmation_value` output field
- [ ] DialogueContext includes `conversation_state` field
- [ ] understand_node passes `conversation_state` to DialogueContext
- [ ] SoniDU extracts `confirmation_value` correctly:
  - True for yes/confirm/correct variations
  - False for no/wrong/incorrect variations
  - None for unclear responses
- [ ] confirmation_value is None for non-CONFIRMATION message types
- [ ] All unit tests pass (15+ test cases)
- [ ] Integration test: debug_scenarios.py scenario 1 completes without infinite loop
- [ ] Type checking passes: `uv run mypy src/soni/du/`
- [ ] Linting passes: `uv run ruff check src/soni/du/`

### Validación Manual

**Comandos para validar:**

```bash
# Run unit tests
uv run pytest tests/unit/test_soni_du_confirmation.py -v

# Run integration test (scenario 1)
uv run python scripts/debug_scenarios.py 1

# Run all tests
uv run pytest tests/ -v

# Type checking
uv run mypy src/soni/du/

# Linting
uv run ruff check src/soni/du/
```

**Resultado esperado:**
- All unit tests pass
- Scenario 1 completes successfully with booking confirmation
- No infinite loop when user says "yes" to confirmation
- Type checking and linting pass

### Referencias

- Analysis: `docs/analysis/ANALISIS_ERROR_CONFIRMACION.md`
- NLU module: `src/soni/du/modules.py`
- NLU models: `src/soni/du/models.py`
- understand_node: `src/soni/dm/nodes/understand.py`
- DSPy documentation: https://dspy-docs.vercel.app/

### Notas Adicionales

**Implementation approach:**
- Use DSPy's structured output to extract confirmation_value
- The LLM will learn to classify yes/no responses based on the field description
- DSPy optimization will improve this over time with examples

**Common yes/no variations to handle:**
- **Yes**: yes, confirm, correct, that's right, sounds good, perfect, absolutely, sure, ok, okay
- **No**: no, not correct, wrong, incorrect, that's wrong, change it, not right, nope

**Edge cases:**
- **Unclear**: maybe, I'm not sure, hmm, can you repeat?
- **Correction during confirmation**: "Actually, change the destination to London"
  - Should detect as MODIFICATION, not CONFIRMATION
  - confirmation_value should be None

**Confidence adjustment:**
- Clear yes/no: confidence > 0.8
- Unclear response: confidence <= 0.6
- This allows handle_confirmation_node to re-prompt when uncertain

**Context importance:**
- `conversation_state="confirming"` helps NLU prioritize CONFIRMATION detection
- Without this context, "yes" might be misclassified as SLOT_VALUE
- Always pass conversation_state to DialogueContext
