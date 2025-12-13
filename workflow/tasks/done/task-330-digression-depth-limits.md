## Task: 330 - Tests para Límites de Digression Depth

**ID de tarea:** 330
**Hito:** Fase 2 - Enhanced Coverage
**Dependencias:** Ninguna
**Duración estimada:** 1-2 horas
**Prioridad:** 🟡 BAJA

### Objetivo

Agregar tests que verifiquen el comportamiento del sistema cuando se alcanza el límite de profundidad de digresiones consecutivas.

### Contexto

Según el informe de conformidad (`docs/analysis/INFORME_CONFORMIDAD_DISENO_TESTS.md`), no hay tests para límites de digression depth.

**Impacto**: BAJO - Edge case que debe estar cubierto para robustez.

**Estado actual**:
- Tests de digression existen en `tests/unit/test_dm_nodes_handle_digression.py`
- **NO hay tests que verifiquen límites de profundidad**

### Entregables

- [ ] Test `test_handle_digression_depth_limit` implementado
- [ ] Test verifica comportamiento cuando se alcanza límite
- [ ] Test verifica múltiples digresiones consecutivas
- [ ] Test pasa y sigue patrón AAA

### Implementación Detallada

#### Paso 1: Investigar límite de digression depth

**Archivo(s) a investigar:**
- `src/soni/dm/nodes/handle_digression.py` - Implementación del nodo
- `src/soni/core/config.py` - Configuración de límites
- `src/soni/core/state.py` - Estado y metadata de digression

#### Paso 2: Crear test de límite de profundidad

**Archivo(s) a modificar:** `tests/unit/test_dm_nodes_handle_digression.py`

**Código específico:**

```python
async def test_handle_digression_depth_limit(
    create_state_with_flow, mock_runtime
):
    """
    Digression depth limit prevents infinite digression loops.

    When maximum digression depth is reached, system should handle gracefully.
    """
    # Arrange
    state = create_state_with_flow("book_flight")
    state["waiting_for_slot"] = "destination"

    # Set metadata to indicate we're at max depth
    MAX_DIGRESSION_DEPTH = 3  # Or from config
    state["metadata"] = {
        "_digression_depth": MAX_DIGRESSION_DEPTH,
    }

    state["nlu_result"] = {
        "message_type": MessageType.QUESTION.value,
    }

    # Act
    result = await handle_digression_node(state, mock_runtime)

    # Assert
    # ✅ Should handle gracefully (may return error, or re-prompt, or limit)
    # (Depende de implementación específica)
    assert "digression" in result.get("last_response", "").lower() or \
           result.get("conversation_state") == "error" or \
           result.get("conversation_state") == "waiting_for_slot"

    # ✅ Flow stack still preserved
    assert len(result.get("flow_stack", state["flow_stack"])) == len(state["flow_stack"])
```

#### Paso 3: Crear test de múltiples digresiones consecutivas

**Archivo(s) a modificar:** `tests/unit/test_dm_nodes_handle_digression.py`

**Código específico:**

```python
async def test_handle_digression_multiple_consecutive(
    create_state_with_flow, mock_runtime
):
    """
    Multiple consecutive digressions increment depth counter.
    """
    # Arrange
    state = create_state_with_flow("book_flight")
    state["waiting_for_slot"] = "destination"
    state["metadata"] = {}

    # First digression
    state["nlu_result"] = {
        "message_type": MessageType.QUESTION.value,
    }

    result1 = await handle_digression_node(state, mock_runtime)

    # Second digression (simulate)
    state["metadata"] = result1.get("metadata", {})
    result2 = await handle_digression_node(state, mock_runtime)

    # Assert
    # ✅ Depth counter incremented
    assert result2.get("metadata", {}).get("_digression_depth", 0) >= 1
```

### TDD Cycle

#### Red Phase: Write Failing Tests

**Test file:** `tests/unit/test_dm_nodes_handle_digression.py`

**Failing tests to write FIRST:**

```python
# Test 1: Depth limit
async def test_handle_digression_depth_limit(...):
    """Test that digression depth limit is enforced."""
    # Arrange
    # Act
    # Assert
    pass  # Will fail until implemented

# Test 2: Multiple consecutive
async def test_handle_digression_multiple_consecutive(...):
    """Test that multiple digressions increment counter."""
    # Arrange
    # Act
    # Assert
    pass  # Will fail until implemented
```

**Verify tests:**
```bash
uv run pytest tests/unit/test_dm_nodes_handle_digression.py::test_handle_digression_depth_limit -v
```

**Commit:**
```bash
git add tests/unit/test_dm_nodes_handle_digression.py
git commit -m "test: add tests for digression depth limits"
```

---

### Tests Requeridos

**Archivo de tests:** `tests/unit/test_dm_nodes_handle_digression.py`

**Tests específicos a implementar:**

```python
# Test 1: Depth limit
async def test_handle_digression_depth_limit():
    """Digression depth limit prevents infinite loops."""
    # Arrange - Set depth to max
    # Act
    # Assert
    # - Graceful handling
    # - Flow stack preserved

# Test 2: Multiple consecutive
async def test_handle_digression_multiple_consecutive():
    """Multiple consecutive digressions increment counter."""
    # Arrange
    # Act - Multiple digressions
    # Assert
    # - Counter incremented
    # - Flow stack preserved
```

### Criterios de Éxito

- [ ] Test `test_handle_digression_depth_limit` implementado
- [ ] Test `test_handle_digression_multiple_consecutive` implementado
- [ ] Tests verifican límites de profundidad
- [ ] Tests verifican preservación de flow_stack
- [ ] Tests pasan
- [ ] Linting pasa sin errores
- [ ] Type checking pasa sin errores

### Validación Manual

**Comandos para validar:**

```bash
# Run tests
uv run pytest tests/unit/test_dm_nodes_handle_digression.py::test_handle_digression_depth_limit -v
uv run pytest tests/unit/test_dm_nodes_handle_digression.py::test_handle_digression_multiple_consecutive -v

# Linting
uv run ruff check tests/unit/test_dm_nodes_handle_digression.py

# Type checking
uv run mypy tests/unit/test_dm_nodes_handle_digression.py
```

**Resultado esperado:**
- Tests pasan
- Sin errores de linting o type checking

### Referencias

- `docs/analysis/INFORME_CONFORMIDAD_DISENO_TESTS.md` - Digression depth limits
- `src/soni/dm/nodes/handle_digression.py` - Implementación del nodo
- `src/soni/core/config.py` - Configuración

### Notas Adicionales

- **Investigación necesaria**: Primero investigar si existe límite de digression depth en la implementación.
- **Configuración**: Verificar si el límite es configurable o hardcoded.
- **Completitud**: Esta tarea es para completitud y robustez.
