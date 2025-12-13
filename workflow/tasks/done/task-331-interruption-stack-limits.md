## Task: 331 - Tests para Límites de Stack en Interruption

**ID de tarea:** 331
**Hito:** Fase 2 - Enhanced Coverage
**Dependencias:** Ninguna
**Duración estimada:** 1 hora
**Prioridad:** 🟡 BAJA

### Objetivo

Agregar tests que verifiquen el comportamiento del sistema cuando se alcanza el límite de profundidad del stack de flows durante una interrupción (intent change).

### Contexto

Según el informe de conformidad (`docs/analysis/INFORME_CONFORMIDAD_DISENO_TESTS.md`), falta verificar límite de stack depth en interruptions.

**Impacto**: BAJO - Edge case que debe estar cubierto para robustez.

**Estado actual**:
- Tests de intent_change existen en `tests/unit/test_nodes_handle_intent_change.py`
- **NO hay tests que verifiquen límite de stack depth**

### Entregables

- [ ] Test `test_handle_intent_change_stack_limit` implementado
- [ ] Test verifica comportamiento cuando se alcanza límite
- [ ] Test verifica estrategia de manejo (cancel_oldest, reject_new, etc.)
- [ ] Test pasa y sigue patrón AAA

### Implementación Detallada

#### Paso 1: Investigar límite de stack depth

**Archivo(s) a investigar:**
- `src/soni/dm/nodes/handle_intent_change.py` - Implementación del nodo
- `src/soni/flow/manager.py` - FlowManager y `_enforce_stack_limit`
- `src/soni/core/config.py` - Configuración de límites

#### Paso 2: Crear test de límite de stack

**Archivo(s) a modificar:** `tests/unit/test_nodes_handle_intent_change.py`

**Código específico:**

```python
async def test_handle_intent_change_stack_limit(
    create_state_with_flow, mock_runtime
):
    """
    Intent change respects flow stack limit.

    When maximum stack depth is reached, system should handle according to strategy.
    """
    # Arrange - Create state with stack at max depth
    MAX_STACK_DEPTH = 5  # Or from config
    state = create_state_with_flow("book_flight")

    # Fill stack to max depth
    state["flow_stack"] = [
        {"flow_id": f"flow_{i}", "flow_name": f"flow_{i}", "flow_state": "paused"}
        for i in range(MAX_STACK_DEPTH)
    ]
    state["flow_stack"][-1]["flow_state"] = "active"  # Current flow

    # Try to push new flow
    state["nlu_result"] = {
        "message_type": MessageType.INTENT_CHANGE.value,
        "intent": "check_weather",
        "command": "new_flow",
    }

    # Mock flow_manager to enforce limit
    mock_runtime.context["flow_manager"].push_flow.side_effect = Exception("Stack limit reached")
    # Or mock to return None/error

    # Act
    result = await handle_intent_change_node(state, mock_runtime)

    # Assert
    # ✅ Should handle gracefully according to strategy
    # (May reject new flow, cancel oldest, or return error)
    # (Depende de implementación específica)
    assert result.get("conversation_state") in ["error", "waiting_for_slot", "idle"] or \
           len(result.get("flow_stack", [])) <= MAX_STACK_DEPTH
```

#### Paso 3: Crear test de estrategia de manejo

**Archivo(s) a modificar:** `tests/unit/test_nodes_handle_intent_change.py`

**Código específico:**

```python
async def test_handle_intent_change_stack_limit_strategy_cancel_oldest(
    create_state_with_flow, mock_runtime
):
    """
    Stack limit strategy: cancel_oldest removes oldest flow.
    """
    # Arrange
    MAX_STACK_DEPTH = 3
    state = create_state_with_flow("book_flight")
    state["flow_stack"] = [
        {"flow_id": "flow_1", "flow_name": "oldest", "flow_state": "paused"},
        {"flow_id": "flow_2", "flow_name": "middle", "flow_state": "paused"},
        {"flow_id": "flow_3", "flow_name": "current", "flow_state": "active"},
    ]

    state["nlu_result"] = {
        "message_type": MessageType.INTENT_CHANGE.value,
        "intent": "check_weather",
    }

    # Mock strategy: cancel_oldest
    def mock_push_flow(state, flow_name, ...):
        if len(state["flow_stack"]) >= MAX_STACK_DEPTH:
            # Cancel oldest
            state["flow_stack"].pop(0)
        # Push new flow
        state["flow_stack"].append({"flow_id": "flow_4", "flow_name": "check_weather"})

    mock_runtime.context["flow_manager"].push_flow.side_effect = mock_push_flow

    # Act
    result = await handle_intent_change_node(state, mock_runtime)

    # Assert
    # ✅ Oldest flow removed
    assert len(result["flow_stack"]) == MAX_STACK_DEPTH
    assert result["flow_stack"][0]["flow_name"] != "oldest"  # Oldest removed
    assert result["flow_stack"][-1]["flow_name"] == "check_weather"  # New flow added
```

### TDD Cycle

#### Red Phase: Write Failing Tests

**Test file:** `tests/unit/test_nodes_handle_intent_change.py`

**Failing tests to write FIRST:**

```python
# Test 1: Stack limit
async def test_handle_intent_change_stack_limit(...):
    """Test that stack limit is enforced."""
    # Arrange
    # Act
    # Assert
    pass  # Will fail until implemented

# Test 2: Strategy
async def test_handle_intent_change_stack_limit_strategy_cancel_oldest(...):
    """Test cancel_oldest strategy."""
    # Arrange
    # Act
    # Assert
    pass  # Will fail until implemented
```

**Verify tests:**
```bash
uv run pytest tests/unit/test_nodes_handle_intent_change.py::test_handle_intent_change_stack_limit -v
```

**Commit:**
```bash
git add tests/unit/test_nodes_handle_intent_change.py
git commit -m "test: add tests for interruption stack limits"
```

---

### Tests Requeridos

**Archivo de tests:** `tests/unit/test_nodes_handle_intent_change.py`

**Tests específicos a implementar:**

```python
# Test 1: Stack limit
async def test_handle_intent_change_stack_limit():
    """Intent change respects flow stack limit."""
    # Arrange - Stack at max depth
    # Act
    # Assert
    # - Graceful handling
    # - Stack depth respected

# Test 2: Strategy
async def test_handle_intent_change_stack_limit_strategy_cancel_oldest():
    """Stack limit strategy: cancel_oldest removes oldest flow."""
    # Arrange
    # Act
    # Assert
    # - Oldest flow removed
    # - New flow added
```

### Criterios de Éxito

- [ ] Test `test_handle_intent_change_stack_limit` implementado
- [ ] Test de estrategia implementado
- [ ] Tests verifican límites de stack
- [ ] Tests pasan
- [ ] Linting pasa sin errores
- [ ] Type checking pasa sin errores

### Validación Manual

**Comandos para validar:**

```bash
# Run tests
uv run pytest tests/unit/test_nodes_handle_intent_change.py::test_handle_intent_change_stack_limit -v

# Linting
uv run ruff check tests/unit/test_nodes_handle_intent_change.py

# Type checking
uv run mypy tests/unit/test_nodes_handle_intent_change.py
```

**Resultado esperado:**
- Tests pasan
- Sin errores de linting o type checking

### Referencias

- `docs/analysis/INFORME_CONFORMIDAD_DISENO_TESTS.md` - Interruption stack limits
- `src/soni/dm/nodes/handle_intent_change.py` - Implementación del nodo
- `src/soni/flow/manager.py` - FlowManager y stack limits
- `docs/design/07-flow-management.md` - Gestión de flows

### Notas Adicionales

- **Investigación necesaria**: Primero investigar cómo se maneja el límite de stack en FlowManager.
- **Estrategias**: Verificar qué estrategias están implementadas (cancel_oldest, reject_new, warn_user, etc.).
- **Completitud**: Esta tarea es para completitud y robustez.
