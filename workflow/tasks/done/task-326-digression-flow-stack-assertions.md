## Task: 326 - Agregar Assertions de flow_stack a Tests de Digression

**ID de tarea:** 326
**Hito:** Fase 1 - Critical Fixes
**Dependencias:** Ninguna
**Duración estimada:** 30 minutos
**Prioridad:** 🔴 MEDIA-ALTA

### Objetivo

Agregar assertions críticas a los tests existentes de digression para verificar que el principio de diseño "digression NO modifica flow_stack" se cumple correctamente.

### Contexto

Según el informe de conformidad (`docs/analysis/INFORME_CONFORMIDAD_DISENO_TESTS.md`), los tests de digression verifican que se preserva `waiting_for_slot` y `conversation_state`, pero **NO verifican explícitamente que `flow_stack` permanece intacto**.

**Principio de diseño crítico** (`docs/design/10-dsl-specification/06-patterns.md:201`):
> "DigressionHandler coordinates question/help handling. **Does NOT modify flow stack**."

**Impacto**: MEDIA-ALTA - Principio de diseño crítico no verificado en tests.

**Estado actual**:
- Tests existen en `tests/unit/test_dm_nodes_handle_digression.py`
- Falta assertion explícita de que `flow_stack` no cambia

### Entregables

- [ ] Assertions agregadas a todos los tests de digression
- [ ] Verificación explícita de que `flow_stack` no se modifica
- [ ] Tests existentes siguen pasando
- [ ] Documentación del principio de diseño en comentarios

### Implementación Detallada

#### Paso 1: Identificar tests que necesitan assertions

**Archivo(s) a modificar:** `tests/unit/test_dm_nodes_handle_digression.py`

**Tests a modificar:**
- `test_handle_digression_preserves_waiting_for_slot`
- `test_handle_digression_preserves_conversation_state`
- Cualquier otro test que llame a `handle_digression_node`

#### Paso 2: Agregar assertion a cada test

**Archivo(s) a modificar:** `tests/unit/test_dm_nodes_handle_digression.py`

**Código específico:**

```python
async def test_handle_digression_preserves_waiting_for_slot(
    create_state_with_flow, mock_runtime
):
    """Digression preserves waiting_for_slot and flow_stack."""
    # Arrange
    state = create_state_with_flow("book_flight")
    state["waiting_for_slot"] = "destination"
    state["flow_stack"] = [{"flow_id": "flow_1", "flow_name": "book_flight"}]

    # ✅ AGREGAR: Guardar stack original
    original_stack = state["flow_stack"].copy()

    # Act
    result = await handle_digression_node(state, mock_runtime)

    # Assert
    # ✅ Preserva waiting_for_slot
    assert result["waiting_for_slot"] == "destination"

    # ✅ AGREGAR: Verifica que flow_stack NO cambió
    assert result.get("flow_stack", state["flow_stack"]) == original_stack, \
        "Digression must NOT modify flow stack (design principle)"
```

#### Paso 3: Agregar test dedicado si no existe

**Archivo(s) a modificar:** `tests/unit/test_dm_nodes_handle_digression.py`

**Código específico:**

```python
async def test_handle_digression_flow_stack_unchanged(
    create_state_with_flow, mock_runtime
):
    """
    Digression does NOT modify flow stack (design principle).

    Design Reference: docs/design/10-dsl-specification/06-patterns.md:201
    Principle: "DigressionHandler coordinates question/help handling. Does NOT modify flow stack"
    """
    # Arrange
    state = create_state_with_flow("book_flight")
    state["waiting_for_slot"] = "destination"
    original_stack = state["flow_stack"].copy()

    state["nlu_result"] = {
        "message_type": MessageType.QUESTION.value,
    }

    # Act
    result = await handle_digression_node(state, mock_runtime)

    # Assert
    # ✅ CRÍTICO: flow_stack NO debe modificarse
    assert result.get("flow_stack", state["flow_stack"]) == original_stack, \
        "Digression must NOT modify flow stack (design principle)"

    # ✅ Verificar que es la misma referencia o copia equivalente
    assert len(result.get("flow_stack", state["flow_stack"])) == len(original_stack)
    if original_stack:
        assert result.get("flow_stack", state["flow_stack"])[0]["flow_id"] == original_stack[0]["flow_id"]
```

### TDD Cycle

**Nota**: Esta tarea NO requiere TDD completo ya que estamos agregando assertions a tests existentes. Sin embargo, debemos verificar que los tests siguen pasando.

#### Verificación: Tests Existentes Siguen Pasando

**Verificar que los tests existentes pasan después de agregar assertions:**

```bash
uv run pytest tests/unit/test_dm_nodes_handle_digression.py -v
# Expected: PASSED ✅ (todos los tests deben seguir pasando)
```

**Si algún test falla:**
- Investigar por qué `flow_stack` está cambiando
- Puede indicar un bug en la implementación
- Documentar el issue y crear tarea separada si es necesario

**Commit:**
```bash
git add tests/unit/test_dm_nodes_handle_digression.py
git commit -m "test: add flow_stack preservation assertions to digression tests"
```

---

### Tests Requeridos

**Archivo de tests:** `tests/unit/test_dm_nodes_handle_digression.py`

**Modificaciones específicas:**

1. **Agregar a cada test existente:**
   ```python
   # Al inicio del test (después de Arrange):
   original_stack = state["flow_stack"].copy()

   # Al final del test (en Assert):
   assert result.get("flow_stack", state["flow_stack"]) == original_stack, \
       "Digression must NOT modify flow stack (design principle)"
   ```

2. **Crear test dedicado (si no existe):**
   ```python
   async def test_handle_digression_flow_stack_unchanged(...):
       """Explicit test that digression doesn't modify flow stack."""
   ```

### Criterios de Éxito

- [ ] Assertions agregadas a todos los tests de digression
- [ ] Test dedicado `test_handle_digression_flow_stack_unchanged` existe
- [ ] Todos los tests existentes siguen pasando
- [ ] Comentarios con referencia al diseño agregados
- [ ] Linting pasa sin errores
- [ ] Type checking pasa sin errores

### Validación Manual

**Comandos para validar:**

```bash
# Run tests
uv run pytest tests/unit/test_dm_nodes_handle_digression.py -v

# Verificar que todos pasan
uv run pytest tests/unit/test_dm_nodes_handle_digression.py --tb=short

# Linting
uv run ruff check tests/unit/test_dm_nodes_handle_digression.py

# Type checking
uv run mypy tests/unit/test_dm_nodes_handle_digression.py
```

**Resultado esperado:**
- Todos los tests pasan (incluyendo nuevas assertions)
- Sin errores de linting o type checking
- Si algún test falla, investigar si es bug en implementación

### Referencias

- `docs/analysis/INFORME_CONFORMIDAD_DISENO_TESTS.md` - Issue #3: Digression Doesn't Verify flow_stack Unchanged
- `docs/design/10-dsl-specification/06-patterns.md:201` - Principio de diseño
- `tests/unit/test_dm_nodes_handle_digression.py` - Tests existentes
- `src/soni/dm/nodes/handle_digression.py` - Implementación del nodo

### Notas Adicionales

- **Importante**: Si las assertions fallan, puede indicar un bug en `handle_digression_node` que debe corregirse.
- **Principio crítico**: Digression es similar a clarification - ambos NO deben modificar `flow_stack`.
- **Comparación**: Usar `.copy()` para evitar problemas de referencia mutua.
- **Si falla**: Documentar el bug y crear tarea separada para corregir la implementación.
