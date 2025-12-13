## Task: 328 - Tests para Multi-Slot Skip Logic

**ID de tarea:** 328
**Hito:** Fase 2 - Enhanced Coverage
**Dependencias:** Ninguna
**Duración estimada:** 1-2 horas
**Prioridad:** ⚠️ MEDIA

### Objetivo

Agregar tests que verifiquen que cuando un usuario proporciona múltiples slots en un solo mensaje, los pasos de collect subsecuentes para esos slots son saltados automáticamente.

### Contexto

Según el informe de conformidad (`docs/analysis/INFORME_CONFORMIDAD_DISENO_TESTS.md`), el comportamiento de skip de múltiples slots no está verificado.

**Diseño especifica** (`docs/design/10-dsl-specification/06-patterns.md:87`):
> "Subsequent collect steps for those slots are **SKIPPED** (already filled)"

**Impacto**: MEDIA - Comportamiento esperado del usuario (proveer múltiples valores en un mensaje) que debe estar cubierto.

**Estado actual**:
- Tests de `validate_slot` existen en `tests/unit/test_nodes_validate_slot.py`
- **NO hay tests que verifiquen skip de múltiples slots**

### Entregables

- [ ] Test `test_validate_slot_skips_completed_collect_steps` implementado
- [ ] Test verifica que múltiples slots se guardan correctamente
- [ ] Test verifica que pasos de collect para slots ya completados se saltan
- [ ] Test verifica transición correcta a confirmation o siguiente slot
- [ ] Test pasa y sigue patrón AAA

### Implementación Detallada

#### Paso 1: Crear test de skip logic

**Archivo(s) a modificar:** `tests/unit/test_nodes_validate_slot.py`

**Código específico:**

```python
async def test_validate_slot_skips_completed_collect_steps(
    create_state_with_flow, mock_runtime
):
    """
    When multiple slots provided, collect steps for those slots are skipped.

    Design Reference: docs/design/10-dsl-specification/06-patterns.md:87
    Pattern: "Subsequent collect steps for those slots are SKIPPED (already filled)"
    """
    # Arrange - User provides multiple slots at once
    state = create_state_with_flow("book_flight")
    state["nlu_result"] = {
        "message_type": MessageType.SLOT_VALUE.value,
        "slots": [
            {"name": "origin", "value": "Madrid"},
            {"name": "destination", "value": "Barcelona"},
            {"name": "date", "value": "2024-12-25"}
        ]
    }

    # Mock step_manager to simulate flow with multiple collect steps
    mock_step_config = {
        "type": "collect",
        "slot": "origin",
    }

    # Mock get_next_unfilled_slot to return None after all slots filled
    def mock_get_next_unfilled_slot(state, context):
        # After validating all slots, no more unfilled slots
        return None

    mock_runtime.context["step_manager"].get_current_step_config.return_value = mock_step_config
    mock_runtime.context["step_manager"].get_next_unfilled_slot.side_effect = mock_get_next_unfilled_slot

    # Mock normalizer
    mock_runtime.context["normalizer"].normalize_slot.return_value = lambda slot, value: value

    # Act
    result = await validate_slot_node(state, mock_runtime)

    # Assert
    # ✅ All slots filled
    assert result["flow_slots"]["flow_1"]["origin"] == "Madrid"
    assert result["flow_slots"]["flow_1"]["destination"] == "Barcelona"
    assert result["flow_slots"]["flow_1"]["date"] == "2024-12-25"

    # ✅ Should advance to confirmation, not next collect
    # (because all slots are filled)
    assert result["conversation_state"] == "ready_for_confirmation" or \
           result["conversation_state"] == "waiting_for_slot"  # Depends on flow config
```

#### Paso 2: Crear test de skip parcial

**Archivo(s) a modificar:** `tests/unit/test_nodes_validate_slot.py`

**Código específico:**

```python
async def test_validate_slot_skips_to_next_unfilled_slot(
    create_state_with_flow, mock_runtime
):
    """
    When some slots provided, skip to next unfilled slot.

    User provides origin and destination, but not date.
    System should skip collect steps for origin and destination,
    and go directly to collect date.
    """
    # Arrange
    state = create_state_with_flow("book_flight")
    state["nlu_result"] = {
        "message_type": MessageType.SLOT_VALUE.value,
        "slots": [
            {"name": "origin", "value": "Madrid"},
            {"name": "destination", "value": "Barcelona"},
        ]
    }

    # Mock: next unfilled slot is "date"
    mock_runtime.context["step_manager"].get_next_unfilled_slot.return_value = "date"
    mock_runtime.context["step_manager"].get_current_step_config.return_value = {
        "type": "collect",
        "slot": "origin",
    }

    # Act
    result = await validate_slot_node(state, mock_runtime)

    # Assert
    # ✅ Provided slots filled
    assert result["flow_slots"]["flow_1"]["origin"] == "Madrid"
    assert result["flow_slots"]["flow_1"]["destination"] == "Barcelona"

    # ✅ Should advance to next unfilled slot (date)
    assert result["waiting_for_slot"] == "date"
    assert result["conversation_state"] == "waiting_for_slot"
```

### TDD Cycle

#### Red Phase: Write Failing Tests

**Test file:** `tests/unit/test_nodes_validate_slot.py`

**Failing tests to write FIRST:**

```python
# Test 1: All slots provided - skip to confirmation
async def test_validate_slot_skips_completed_collect_steps(...):
    """Test that completed collect steps are skipped."""
    # Arrange
    # Act
    # Assert
    pass  # Will fail until implemented

# Test 2: Some slots provided - skip to next unfilled
async def test_validate_slot_skips_to_next_unfilled_slot(...):
    """Test that system skips to next unfilled slot."""
    # Arrange
    # Act
    # Assert
    pass  # Will fail until implemented
```

**Verify tests fail or pass:**
```bash
uv run pytest tests/unit/test_nodes_validate_slot.py::test_validate_slot_skips_completed_collect_steps -v
uv run pytest tests/unit/test_nodes_validate_slot.py::test_validate_slot_skips_to_next_unfilled_slot -v
# Expected: May PASS if already implemented, or FAIL if gap exists
```

**Commit:**
```bash
git add tests/unit/test_nodes_validate_slot.py
git commit -m "test: add tests for multi-slot skip logic"
```

#### Green Phase: Make Tests Pass

**If tests fail, implement missing functionality in `validate_slot_node`.**

**Verify tests pass:**
```bash
uv run pytest tests/unit/test_nodes_validate_slot.py -v
# Expected: PASSED ✅
```

**Commit:**
```bash
git add src/soni/dm/nodes/validate_slot.py tests/
git commit -m "feat: implement multi-slot skip logic"
```

---

### Tests Requeridos

**Archivo de tests:** `tests/unit/test_nodes_validate_slot.py`

**Tests específicos a implementar:**

```python
# Test 1: All slots provided
async def test_validate_slot_skips_completed_collect_steps():
    """
    When multiple slots provided, collect steps for those slots are skipped.
    """
    # Arrange - Multiple slots in NLU result
    # Act - Validate slot
    # Assert
    # - All slots saved
    # - Advance to confirmation (not next collect)

# Test 2: Partial slots provided
async def test_validate_slot_skips_to_next_unfilled_slot():
    """
    When some slots provided, skip to next unfilled slot.
    """
    # Arrange - Some slots in NLU result
    # Act - Validate slot
    # Assert
    # - Provided slots saved
    # - Advance to next unfilled slot
```

### Criterios de Éxito

- [ ] Test `test_validate_slot_skips_completed_collect_steps` implementado
- [ ] Test `test_validate_slot_skips_to_next_unfilled_slot` implementado
- [ ] Tests verifican que múltiples slots se guardan
- [ ] Tests verifican skip correcto de pasos
- [ ] Tests verifican transición correcta de estado
- [ ] Todos los tests pasan
- [ ] Linting pasa sin errores
- [ ] Type checking pasa sin errores

### Validación Manual

**Comandos para validar:**

```bash
# Run specific tests
uv run pytest tests/unit/test_nodes_validate_slot.py::test_validate_slot_skips_completed_collect_steps -v
uv run pytest tests/unit/test_nodes_validate_slot.py::test_validate_slot_skips_to_next_unfilled_slot -v

# Run all validate_slot tests
uv run pytest tests/unit/test_nodes_validate_slot.py -v

# Linting
uv run ruff check tests/unit/test_nodes_validate_slot.py

# Type checking
uv run mypy tests/unit/test_nodes_validate_slot.py
```

**Resultado esperado:**
- Tests pasan
- Si tests fallan, puede indicar gap en implementación
- Sin errores de linting o type checking

### Referencias

- `docs/analysis/INFORME_CONFORMIDAD_DISENO_TESTS.md` - Issue #5: Multi-Slot Skip Logic Not Verified
- `docs/design/10-dsl-specification/06-patterns.md:87` - Especificación del patrón
- `tests/unit/test_nodes_validate_slot.py` - Tests existentes
- `src/soni/dm/nodes/validate_slot.py` - Implementación del nodo

### Notas Adicionales

- **Importante**: Este comportamiento es esperado por usuarios que proporcionan múltiples valores en un mensaje.
- **Step Manager**: Verificar cómo `step_manager` determina el siguiente slot no completado.
- **Routing**: Verificar que el routing después de `validate_slot` maneja correctamente el caso de todos los slots completados.
- **Edge cases**: Considerar casos donde algunos slots son opcionales.
