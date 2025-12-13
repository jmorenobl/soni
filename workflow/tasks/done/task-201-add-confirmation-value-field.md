## Task: 201 - Add confirmation_value Field to NLUOutput Model

**ID de tarea:** 201
**Hito:** Confirmation Flow Fix
**Dependencias:** Ninguna
**Duración estimada:** 1-2 horas

### Objetivo

Add the missing `confirmation_value` field to the `NLUOutput` Pydantic model to support yes/no confirmation extraction from user messages.

### Contexto

The `handle_confirmation_node` expects a `confirmation_value` field in the NLU result to determine if the user confirmed (True), denied (False), or gave an unclear response (None). However, this field does not exist in the `NLUOutput` model (src/soni/du/models.py:53-63), causing `confirmation_value` to always be `None` and triggering an infinite loop.

This is a critical missing piece that makes confirmation steps (`type: confirm` in YAML) completely unusable.

**References:**
- Analysis: `docs/analysis/ANALISIS_ERROR_CONFIRMACION.md`
- Current model: `src/soni/du/models.py:53-63`
- Node expecting field: `src/soni/dm/nodes/handle_confirmation.py:49`

### Entregables

- [ ] Add `confirmation_value: bool | None` field to `NLUOutput` model
- [ ] Update model docstring to explain the field
- [ ] Add field description with Field() annotation
- [ ] Update any model serialization tests
- [ ] Verify model validation works correctly

### Implementación Detallada

#### Paso 1: Add confirmation_value field to NLUOutput

**Archivo(s) a modificar:** `src/soni/du/models.py`

**Código específico:**

```python
class NLUOutput(BaseModel):
    """Structured NLU output."""

    message_type: MessageType = Field(description="Type of user message")
    command: str | None = Field(
        default=None,
        description="User's intent or command when changing intent, canceling, or confirming. None for slot value messages.",
    )
    slots: list[SlotValue] = Field(default_factory=list, description="Extracted slot values")
    confidence: float = Field(ge=0.0, le=1.0, description="Overall confidence")

    # ✅ ADD THIS FIELD
    confirmation_value: bool | None = Field(
        default=None,
        description=(
            "For CONFIRMATION message_type: True if user confirmed (yes/correct/confirm), "
            "False if user denied (no/wrong/incorrect), None if unclear or not a confirmation message."
        ),
    )
```

**Explicación:**
- Add field after `confidence` to maintain logical grouping
- Use `bool | None` type hint (Python 3.10+ union syntax)
- Default to `None` so existing code doesn't break
- Provide detailed description explaining all three states
- Field is only populated when `message_type = MessageType.CONFIRMATION`

#### Paso 2: Update model docstring

**Archivo(s) a modificar:** `src/soni/du/models.py`

**Código específico:**

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
```

**Explicación:**
- Update docstring to document all fields including new one
- Add note explaining when confirmation_value is relevant
- Maintain consistency with existing documentation style

#### Paso 3: Verify backward compatibility

**Archivo(s) a revisar:** `src/soni/du/modules.py`, `src/soni/du/nlu_provider.py`

**Acción:**
- Check all places where `NLUOutput` is instantiated
- Verify that existing code still works with the new optional field
- Pydantic will automatically set `confirmation_value=None` if not provided

**Consideraciones importantes:**
- The field has `default=None`, so existing code won't break
- Any code creating `NLUOutput` can omit this field initially
- Task 202 will implement the actual extraction logic

### Tests Requeridos

**Archivo de tests:** `tests/unit/test_du_models.py`

**Tests específicos a implementar:**

```python
# Test 1: Model instantiation with confirmation_value
def test_nlu_output_with_confirmation_value():
    """Test that NLUOutput accepts confirmation_value field"""
    # Arrange
    nlu_output = NLUOutput(
        message_type=MessageType.CONFIRMATION,
        command=None,
        slots=[],
        confidence=0.9,
        confirmation_value=True
    )

    # Assert
    assert nlu_output.confirmation_value is True
    assert nlu_output.message_type == MessageType.CONFIRMATION


# Test 2: Model instantiation without confirmation_value (backward compatibility)
def test_nlu_output_without_confirmation_value():
    """Test that NLUOutput works without confirmation_value (defaults to None)"""
    # Arrange
    nlu_output = NLUOutput(
        message_type=MessageType.SLOT_VALUE,
        command=None,
        slots=[],
        confidence=0.9
    )

    # Assert
    assert nlu_output.confirmation_value is None


# Test 3: Confirmation value with different states
def test_nlu_output_confirmation_states():
    """Test all three states of confirmation_value"""
    # Test confirmed (True)
    confirmed = NLUOutput(
        message_type=MessageType.CONFIRMATION,
        command=None,
        slots=[],
        confidence=0.95,
        confirmation_value=True
    )
    assert confirmed.confirmation_value is True

    # Test denied (False)
    denied = NLUOutput(
        message_type=MessageType.CONFIRMATION,
        command=None,
        slots=[],
        confidence=0.90,
        confirmation_value=False
    )
    assert denied.confirmation_value is False

    # Test unclear (None)
    unclear = NLUOutput(
        message_type=MessageType.CONFIRMATION,
        command=None,
        slots=[],
        confidence=0.60,
        confirmation_value=None
    )
    assert unclear.confirmation_value is None


# Test 4: Model serialization includes confirmation_value
def test_nlu_output_serialization():
    """Test that confirmation_value is included in model_dump()"""
    # Arrange
    nlu_output = NLUOutput(
        message_type=MessageType.CONFIRMATION,
        command=None,
        slots=[],
        confidence=0.9,
        confirmation_value=True
    )

    # Act
    serialized = nlu_output.model_dump()

    # Assert
    assert "confirmation_value" in serialized
    assert serialized["confirmation_value"] is True
```

### Criterios de Éxito

- [ ] `confirmation_value` field added to `NLUOutput` model
- [ ] Field has correct type hint: `bool | None`
- [ ] Field has default value of `None`
- [ ] Field has descriptive documentation
- [ ] Model docstring updated to include new field
- [ ] All new tests pass
- [ ] Existing tests still pass (backward compatibility)
- [ ] Type checking passes: `uv run mypy src/soni/du/models.py`
- [ ] Linting passes: `uv run ruff check src/soni/du/models.py`

### Validación Manual

**Comandos para validar:**

```bash
# Run type checking
uv run mypy src/soni/du/models.py

# Run linting
uv run ruff check src/soni/du/models.py

# Run model tests
uv run pytest tests/unit/test_du_models.py -v

# Run all tests to ensure no regressions
uv run pytest tests/ -v
```

**Resultado esperado:**
- Type checking passes with no errors
- Linting passes with no errors
- All model tests pass
- No regressions in existing tests

### Referencias

- Analysis document: `docs/analysis/ANALISIS_ERROR_CONFIRMACION.md`
- NLUOutput model: `src/soni/du/models.py:53-63`
- handle_confirmation_node: `src/soni/dm/nodes/handle_confirmation.py:49-75`
- Pydantic documentation: https://docs.pydantic.dev/latest/

### Notas Adicionales

**Why this field is needed:**
- The confirmation handler (handle_confirmation_node) checks `nlu_result.get("confirmation_value")`
- Without this field, it always returns None, causing the handler to re-prompt indefinitely
- This creates an infinite loop: understand → handle_confirmation → understand → ...

**Design consideration:**
- The field is optional (`default=None`) to maintain backward compatibility
- Only relevant when `message_type = MessageType.CONFIRMATION`
- Should be `None` for all other message types

**Next steps after this task:**
- Task 202 will implement the actual extraction logic in the NLU module
- Task 203 will fix the confirmation message display issue
- Task 204 will add defensive checks to prevent infinite loops
