## Task: 333 - Crear Helper de Validación de Transiciones de Estado

**ID de tarea:** 333
**Hito:** Fase 3 - Quality Improvements
**Dependencias:** Ninguna
**Duración estimada:** 2-3 horas
**Prioridad:** 🟢 BAJA

### Objetivo

Crear un helper function que valide que las transiciones de estado en los tests son válidas según la state machine definida en el diseño.

### Contexto

Según el informe de conformidad (`docs/analysis/INFORME_CONFORMIDAD_DISENO_TESTS.md`), agregar un validador de transiciones mejora la calidad de los tests y asegura conformidad con el diseño.

**Beneficio**: Verificar que transiciones de estado son válidas según state machine design.

**Impacto**: BAJO - Mejora de calidad y validación de diseño.

### Entregables

- [ ] Helper function `assert_valid_state_transition` creado en `tests/unit/conftest.py`
- [ ] Helper valida transiciones según state machine del diseño
- [ ] Helper usado en tests relevantes
- [ ] Tests pasan y siguen patrón AAA

### Implementación Detallada

#### Paso 1: Crear helper function

**Archivo(s) a modificar:** `tests/unit/conftest.py`

**Código específico:**

```python
def assert_valid_state_transition(from_state: str, to_state: str) -> None:
    """
    Verify state transition is valid per state machine design.

    Design Reference: docs/design/04-state-machine.md

    Args:
        from_state: Source conversation state
        to_state: Target conversation state

    Raises:
        AssertionError: If transition is invalid
    """
    valid_transitions = {
        "idle": ["understanding"],
        "understanding": [
            "waiting_for_slot",
            "validating_slot",
            "confirming",
            "executing_action",
            "error",
        ],
        "waiting_for_slot": ["understanding"],
        "validating_slot": [
            "waiting_for_slot",
            "ready_for_confirmation",
            "ready_for_action",
            "error",
        ],
        "confirming": [
            "ready_for_action",
            "understanding",
            "waiting_for_slot",
            "error",
        ],
        "ready_for_action": ["executing_action"],
        "ready_for_confirmation": ["confirming"],
        "executing_action": ["completed", "error"],
        "completed": ["idle"],
        "error": ["idle", "understanding"],
    }

    allowed = valid_transitions.get(from_state, [])
    assert to_state in allowed, (
        f"Invalid state transition: {from_state} → {to_state}. "
        f"Allowed transitions from {from_state}: {allowed}"
    )
```

#### Paso 2: Usar helper en tests

**Archivo(s) a modificar:** `tests/unit/test_handle_confirmation_node.py`

**Ejemplo de uso:**

```python
async def test_handle_confirmation_confirmed(mock_runtime):
    """User confirms - should transition to ready_for_action."""
    # Arrange
    state = {
        "conversation_state": "confirming",
        "nlu_result": {
            "message_type": "confirmation",
            "confirmation_value": True,
        },
    }

    # Act
    result = await handle_confirmation_node(state, mock_runtime)

    # Assert
    from_state = state["conversation_state"]
    to_state = result["conversation_state"]

    # ✅ Validate state transition
    assert_valid_state_transition(from_state, to_state)

    assert to_state == "ready_for_action"
```

#### Paso 3: Agregar a más tests

**Archivos a modificar:**
- `tests/unit/test_dm_nodes_handle_correction.py`
- `tests/unit/test_dm_nodes_handle_modification.py`
- `tests/unit/test_nodes_validate_slot.py`
- Otros tests que cambian `conversation_state`

### TDD Cycle

#### Red Phase: Write Failing Tests

**Test file:** `tests/unit/test_state_transition_validator.py` (opcional, para testear el helper)

**Failing test to write FIRST:**

```python
def test_assert_valid_state_transition_valid():
    """Test that valid transitions pass."""
    # Valid transition
    assert_valid_state_transition("idle", "understanding")
    assert_valid_state_transition("confirming", "ready_for_action")

def test_assert_valid_state_transition_invalid():
    """Test that invalid transitions fail."""
    with pytest.raises(AssertionError):
        assert_valid_state_transition("idle", "executing_action")  # Invalid
```

**Verify test:**
```bash
uv run pytest tests/unit/test_state_transition_validator.py -v
```

**Commit:**
```bash
git add tests/unit/conftest.py tests/unit/test_state_transition_validator.py
git commit -m "test: add state transition validator helper"
```

#### Green Phase: Make Tests Pass

**Verify helper works correctly.**

**Commit:**
```bash
git add tests/
git commit -m "feat: implement state transition validator"
```

---

### Tests Requeridos

**Archivo de tests:** `tests/unit/test_state_transition_validator.py` (opcional)

**Tests específicos a implementar:**

```python
# Test 1: Valid transitions
def test_assert_valid_state_transition_valid():
    """Test that valid transitions pass."""
    # Test multiple valid transitions

# Test 2: Invalid transitions
def test_assert_valid_state_transition_invalid():
    """Test that invalid transitions raise AssertionError."""
    # Test invalid transitions raise error
```

### Criterios de Éxito

- [ ] Helper `assert_valid_state_transition` creado en conftest.py
- [ ] Helper valida todas las transiciones según diseño
- [ ] Helper usado en al menos 5 tests relevantes
- [ ] Tests del helper pasan (si se crean)
- [ ] Todos los tests existentes siguen pasando
- [ ] Linting pasa sin errores
- [ ] Type checking pasa sin errores

### Validación Manual

**Comandos para validar:**

```bash
# Run tests
uv run pytest tests/unit/ -v

# Test helper specifically (if test file created)
uv run pytest tests/unit/test_state_transition_validator.py -v

# Linting
uv run ruff check tests/unit/conftest.py

# Type checking
uv run mypy tests/unit/conftest.py
```

**Resultado esperado:**
- Helper funciona correctamente
- Tests que usan helper pasan
- Sin errores de linting o type checking

### Referencias

- `docs/analysis/INFORME_CONFORMIDAD_DISENO_TESTS.md` - Recommendation #2: Add State Transition Validation Helper
- `docs/design/04-state-machine.md` - State machine design
- `src/soni/core/state.py` - ConversationState enum

### Notas Adicionales

- **State Machine**: Verificar que las transiciones en el helper coinciden exactamente con el diseño.
- **Uso incremental**: Puede agregarse a tests gradualmente, no requiere hacer todo de una vez.
- **Documentación**: El helper debe estar bien documentado con referencias al diseño.
- **Flexibilidad**: Considerar si el helper debe ser estricto o permitir transiciones adicionales no documentadas.
