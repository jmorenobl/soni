## Task: 327 - Test de Regeneración de Mensaje en Correction Durante Confirmation

**ID de tarea:** 327
**Hito:** Fase 1 - Critical Fixes
**Dependencias:** Ninguna
**Duración estimada:** 1 hora
**Prioridad:** ⚠️ MEDIA

### Objetivo

Agregar test que verifique que cuando un usuario corrige un slot durante una confirmación, el sistema regenera el mensaje de confirmación con el valor actualizado.

### Contexto

Según el informe de conformidad (`docs/analysis/INFORME_CONFORMIDAD_DISENO_TESTS.md`), existe un gap en la verificación de regeneración de mensajes durante confirmation.

**Diseño especifica** (`docs/design/10-dsl-specification/06-patterns.md:168-171`):
> "User says 'No wait, I meant December 20th not 15th' →
> 1. Detect correction of departure_date
> 2. Update departure_date = "2024-12-20"
> 3. **Re-display confirmation with updated value**"

**Impacto**: MEDIA - Edge case importante del patrón confirmation que debe estar cubierto.

**Estado actual**:
- Tests de confirmation existen en `tests/unit/test_handle_confirmation_node.py`
- Existe test de correction durante confirmation, pero **NO verifica regeneración de mensaje**

### Entregables

- [ ] Test `test_handle_confirmation_correction_regenerates_message` implementado
- [ ] Test verifica que slot se actualiza
- [ ] Test verifica que nuevo mensaje contiene valor actualizado
- [ ] Test verifica que valor antiguo NO aparece en mensaje
- [ ] Test verifica que estado sigue siendo "confirming"
- [ ] Test pasa y sigue patrón AAA

### Implementación Detallada

#### Paso 1: Crear test de regeneración de mensaje

**Archivo(s) a modificar:** `tests/unit/test_handle_confirmation_node.py`

**Código específico:**

```python
async def test_handle_confirmation_correction_regenerates_message(
    create_state_with_slots, mock_runtime
):
    """
    Correction during confirmation regenerates confirmation with new value.

    Design Reference: docs/design/10-dsl-specification/06-patterns.md:168-171
    Pattern: "Re-display confirmation with updated value"
    """
    # Arrange - State ready for confirmation
    state = create_state_with_slots(
        "book_flight",
        slots={
            "origin": "Madrid",
            "destination": "Barcelona",
            "date": "2024-12-15"
        },
        current_step="confirm_booking",
        conversation_state="confirming"
    )

    # User corrects date during confirmation
    state["nlu_result"] = {
        "message_type": MessageType.CORRECTION.value,
        "slots": [{"name": "date", "value": "2024-12-20"}],
    }

    # Mock response generator to return new confirmation message
    mock_runtime.context["response_generator"].generate_confirmation.return_value = (
        "Please confirm your flight booking:\n"
        "Origin: Madrid\n"
        "Destination: Barcelona\n"
        "Date: 2024-12-20\n"
        "Is this correct?"
    )

    # Mock step_manager to handle correction
    mock_runtime.context["step_manager"].get_current_step_config.return_value = {
        "type": "confirm",
        "slot": None,  # Confirmation step
    }

    # Act
    result = await handle_confirmation_node(state, mock_runtime)

    # Assert
    # ✅ Slot updated
    assert result["flow_slots"]["flow_1"]["date"] == "2024-12-20"

    # ✅ New confirmation message generated with updated value
    assert "2024-12-20" in result["last_response"]

    # ✅ OLD value NOT in message
    assert "2024-12-15" not in result["last_response"]

    # ✅ Still in confirming state
    assert result["conversation_state"] == "confirming" or result["conversation_state"] == "ready_for_confirmation"
```

#### Paso 2: Verificar integración con handle_correction

**Nota**: Si `handle_confirmation_node` delega a `handle_correction_node` para manejar corrections, el test debe verificar que:

1. El correction se detecta correctamente
2. El slot se actualiza
3. El mensaje de confirmación se regenera

**Archivo(s) a modificar:** `tests/unit/test_handle_confirmation_node.py`

**Código específico (si aplica):**

```python
async def test_handle_confirmation_detects_and_handles_correction(
    create_state_with_slots, mock_runtime
):
    """
    Confirmation node detects correction and delegates appropriately.

    This test verifies that when a correction is detected during confirmation,
    the system updates the slot and regenerates the confirmation message.
    """
    # Similar structure to above, but may need to mock handle_correction_node
    # if confirmation delegates to it
```

### TDD Cycle

**Nota**: Esta tarea agrega un test a un archivo existente. No requiere TDD completo, pero debemos verificar que el test pasa o identifica un gap en la implementación.

#### Red Phase: Write Failing Test

**Test file:** `tests/unit/test_handle_confirmation_node.py`

**Failing test to write FIRST:**

```python
async def test_handle_confirmation_correction_regenerates_message(...):
    """Test that correction during confirmation regenerates message."""
    # Arrange
    # Act
    # Assert
    # Will fail if implementation doesn't regenerate message
```

**Verify test fails or passes:**
```bash
uv run pytest tests/unit/test_handle_confirmation_node.py::test_handle_confirmation_correction_regenerates_message -v
# Expected: May PASS if already implemented, or FAIL if gap exists
```

**Commit:**
```bash
git add tests/unit/test_handle_confirmation_node.py
git commit -m "test: add test for confirmation message regeneration on correction"
```

#### Green Phase: Make Test Pass

**If test fails, implement missing functionality in `handle_confirmation_node`.**

**Verify test passes:**
```bash
uv run pytest tests/unit/test_handle_confirmation_node.py::test_handle_confirmation_correction_regenerates_message -v
# Expected: PASSED ✅
```

**Commit:**
```bash
git add src/soni/dm/nodes/handle_confirmation.py tests/
git commit -m "feat: implement confirmation message regeneration on correction"
```

---

### Tests Requeridos

**Archivo de tests:** `tests/unit/test_handle_confirmation_node.py`

**Test específico a implementar:**

```python
async def test_handle_confirmation_correction_regenerates_message():
    """
    Correction during confirmation regenerates confirmation with new value.

    Design Reference: docs/design/10-dsl-specification/06-patterns.md:168-171
    """
    # Arrange
    # - State ready for confirmation with slots
    # - NLU result indicates correction
    # - Mock response generator

    # Act
    # - Call handle_confirmation_node

    # Assert
    # - Slot updated with new value
    # - New confirmation message contains new value
    # - Old value NOT in message
    # - State still in confirming
```

### Criterios de Éxito

- [ ] Test `test_handle_confirmation_correction_regenerates_message` implementado
- [ ] Test verifica actualización de slot
- [ ] Test verifica regeneración de mensaje con valor nuevo
- [ ] Test verifica que valor antiguo NO aparece
- [ ] Test verifica estado "confirming"
- [ ] Test pasa
- [ ] Linting pasa sin errores
- [ ] Type checking pasa sin errores

### Validación Manual

**Comandos para validar:**

```bash
# Run specific test
uv run pytest tests/unit/test_handle_confirmation_node.py::test_handle_confirmation_correction_regenerates_message -v

# Run all confirmation tests
uv run pytest tests/unit/test_handle_confirmation_node.py -v

# Linting
uv run ruff check tests/unit/test_handle_confirmation_node.py

# Type checking
uv run mypy tests/unit/test_handle_confirmation_node.py
```

**Resultado esperado:**
- Test pasa
- Si test falla, puede indicar gap en implementación que debe corregirse
- Sin errores de linting o type checking

### Referencias

- `docs/analysis/INFORME_CONFORMIDAD_DISENO_TESTS.md` - Issue #4: Correction During Confirmation - Message Regeneration Not Verified
- `docs/design/10-dsl-specification/06-patterns.md:168-171` - Especificación del patrón
- `tests/unit/test_handle_confirmation_node.py` - Tests existentes
- `src/soni/dm/nodes/handle_confirmation.py` - Implementación del nodo

### Notas Adicionales

- **Importante**: Si el test falla, puede indicar que la implementación no regenera el mensaje correctamente.
- **Edge case crítico**: Este es un comportamiento esperado del usuario que debe funcionar correctamente.
- **Integración**: Verificar si `handle_confirmation_node` delega a `handle_correction_node` o maneja corrections internamente.
- **Response Generator**: Asegurar que el mock de `response_generator` retorna el mensaje esperado.
