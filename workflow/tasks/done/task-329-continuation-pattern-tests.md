## Task: 329 - Tests para Patrón CONTINUATION

**ID de tarea:** 329
**Hito:** Fase 2 - Enhanced Coverage
**Dependencias:** Ninguna
**Duración estimada:** 2 horas
**Prioridad:** 🟡 BAJA

### Objetivo

Crear tests unitarios para el patrón conversacional CONTINUATION, que actualmente tiene cobertura débil (40%). Este patrón maneja la continuación general del flujo cuando no hay un patrón específico detectado.

### Contexto

Según el informe de conformidad (`docs/analysis/INFORME_CONFORMIDAD_DISENO_TESTS.md`), el patrón CONTINUATION tiene cobertura débil.

**Estado actual**:
- Solo existe test básico de routing en `test_routing.py`
- **NO hay tests exhaustivos del comportamiento de continuation**

**Impacto**: MEDIO - Patrón menos crítico pero debe estar cubierto para completitud.

### Entregables

- [ ] Tests para continuation pattern implementados
- [ ] Test verifica avance de flujo cuando hay active flow
- [ ] Test verifica detección de intent cuando no hay active flow
- [ ] Tests pasan y siguen patrón AAA

### Implementación Detallada

#### Paso 1: Identificar dónde se maneja continuation

**Archivo(s) a investigar:**
- `src/soni/dm/routing.py` - Routing de continuation
- `src/soni/dm/nodes/collect_next_slot.py` - Posible nodo de continuation
- `src/soni/dm/nodes/understand.py` - Puede manejar continuation

#### Paso 2: Crear tests de continuation

**Archivo(s) a crear/modificar:** `tests/unit/test_dm_nodes_handle_continuation.py` o agregar a archivo existente

**Código específico:**

```python
async def test_handle_continuation_advances_flow(
    create_state_with_flow, mock_runtime
):
    """
    Continuation advances to next unfilled slot or action.

    When user provides continuation message and there's an active flow,
    system should advance to next step.
    """
    # Arrange
    state = create_state_with_flow("book_flight")
    state["conversation_state"] = "waiting_for_slot"
    state["waiting_for_slot"] = "origin"
    state["nlu_result"] = {
        "message_type": MessageType.CONTINUATION.value,
        "command": "continue",
    }

    # Mock step_manager to advance to next slot
    mock_runtime.context["step_manager"].get_next_unfilled_slot.return_value = "destination"
    mock_runtime.context["step_manager"].advance_to_next_step.return_value = {
        "waiting_for_slot": "destination",
        "conversation_state": "waiting_for_slot",
    }

    # Act
    # (Depende de dónde se maneje continuation)
    result = await handle_continuation_node(state, mock_runtime)  # O el nodo apropiado

    # Assert
    assert result["waiting_for_slot"] == "destination"
    assert result["conversation_state"] == "waiting_for_slot"
```

#### Paso 3: Crear test de continuation sin active flow

**Archivo(s) a modificar:** `tests/unit/test_dm_nodes_handle_continuation.py`

**Código específico:**

```python
async def test_handle_continuation_with_no_active_flow(
    create_empty_state, mock_runtime
):
    """
    Continuation when no active flow triggers intent detection.

    When user provides continuation but no active flow exists,
    system should treat it as new intent.
    """
    # Arrange
    state = create_empty_state()
    state["conversation_state"] = "idle"
    state["nlu_result"] = {
        "message_type": MessageType.CONTINUATION.value,
        "command": "continue",
        "intent": "book_flight",  # NLU detects intent
    }

    # Act
    # (Depende de implementación)
    result = await handle_continuation_node(state, mock_runtime)

    # Assert
    # Should trigger new flow or intent detection
    # (Depende de implementación específica)
```

### TDD Cycle

#### Red Phase: Write Failing Tests

**Test file:** `tests/unit/test_dm_nodes_handle_continuation.py` (o archivo apropiado)

**Failing tests to write FIRST:**

```python
# Test 1: Continuation with active flow
async def test_handle_continuation_advances_flow(...):
    """Test that continuation advances flow."""
    # Arrange
    # Act
    # Assert
    pass  # Will fail until implemented

# Test 2: Continuation without active flow
async def test_handle_continuation_with_no_active_flow(...):
    """Test that continuation triggers intent detection when no flow."""
    # Arrange
    # Act
    # Assert
    pass  # Will fail until implemented
```

**Verify tests:**
```bash
uv run pytest tests/unit/test_dm_nodes_handle_continuation.py -v
# Expected: May need to create file first
```

**Commit:**
```bash
git add tests/unit/test_dm_nodes_handle_continuation.py
git commit -m "test: add tests for continuation pattern"
```

---

### Tests Requeridos

**Archivo de tests:** `tests/unit/test_dm_nodes_handle_continuation.py` (o archivo apropiado)

**Tests específicos a implementar:**

```python
# Test 1: Advance flow
async def test_handle_continuation_advances_flow():
    """Continuation advances to next unfilled slot or action."""
    # Arrange
    # Act
    # Assert
    # - Flow advances
    # - Correct state transition

# Test 2: No active flow
async def test_handle_continuation_with_no_active_flow():
    """Continuation when no active flow triggers intent detection."""
    # Arrange
    # Act
    # Assert
    # - Intent detected or new flow started
```

### Criterios de Éxito

- [ ] Tests para continuation pattern implementados
- [ ] Tests cubren escenarios con y sin active flow
- [ ] Tests pasan
- [ ] Linting pasa sin errores
- [ ] Type checking pasa sin errores

### Validación Manual

**Comandos para validar:**

```bash
# Run tests
uv run pytest tests/unit/test_dm_nodes_handle_continuation.py -v

# Linting
uv run ruff check tests/unit/test_dm_nodes_handle_continuation.py

# Type checking
uv run mypy tests/unit/test_dm_nodes_handle_continuation.py
```

**Resultado esperado:**
- Tests pasan
- Sin errores de linting o type checking

### Referencias

- `docs/analysis/INFORME_CONFORMIDAD_DISENO_TESTS.md` - Continuation Pattern coverage
- `src/soni/dm/routing.py` - Routing logic
- `tests/unit/test_routing.py` - Tests existentes de routing

### Notas Adicionales

- **Investigación necesaria**: Primero investigar dónde se maneja continuation en el código.
- **Routing**: Continuation puede manejarse en routing o en un nodo dedicado.
- **Completitud**: Esta tarea es para completitud, no crítica.
