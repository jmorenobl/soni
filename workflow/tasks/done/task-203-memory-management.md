## Task: 2.3 - Memory Management

**ID de tarea:** 203
**Hito:** Phase 2 - State Management & Validation
**Dependencias:** Ninguna
**Duración estimada:** 2-3 horas

### Objetivo

Complete memory management by enhancing the existing `prune_state` method in FlowManager to prevent unbounded state growth.

### Contexto

State persists across sessions and must be pruned to prevent unbounded memory growth. The existing `prune_state` method only prunes completed flows. This task enhances it to also prune orphan flow_slots and trace entries.

**Reference:** [docs/implementation/02-phase-2-state.md](../../docs/implementation/02-phase-2-state.md) - Task 2.3

### Entregables

- [ ] `prune_state()` method enhanced in `src/soni/flow/manager.py`
- [ ] Orphan flow_slots pruning implemented
- [ ] Trace entries pruning implemented
- [ ] Completed flows pruning maintained
- [ ] Tests passing in `tests/unit/test_flow_manager.py`
- [ ] Mypy passes without errors

### Implementación Detallada

#### Paso 1: Enhance prune_state Method

**Archivo(s) a crear/modificar:** `src/soni/flow/manager.py`

**Código específico:**

```python
def prune_state(
    self,
    state: DialogueState,
    max_completed_flows: int = 10,
    max_trace: int = 50,
) -> None:
    """
    Prune state to prevent unbounded memory growth.

    Removes:
    - Orphaned flow_slots (flows no longer in stack)
    - Excess completed flows beyond limit
    - Old trace entries beyond limit

    Args:
        state: Dialogue state to prune
        max_completed_flows: Maximum number of completed flows to keep
        max_trace: Maximum number of trace entries to keep
    """
    # 1. Prune orphan flow slots
    active_ids = {ctx["flow_id"] for ctx in state["flow_stack"]}
    orphan_ids = [fid for fid in state["flow_slots"] if fid not in active_ids]

    for fid in orphan_ids:
        del state["flow_slots"][fid]

    # 2. Prune completed flows (keep last N)
    if "completed_flows" not in state["metadata"]:
        state["metadata"]["completed_flows"] = []

    completed = state["metadata"]["completed_flows"]
    if len(completed) > max_completed_flows:
        state["metadata"]["completed_flows"] = completed[-max_completed_flows:]

    # 3. Prune trace (keep last N turns)
    if len(state["trace"]) > max_trace:
        state["trace"] = state["trace"][-max_trace:]
```

**Explicación:**
- Enhance existing `prune_state` method
- Add orphan flow_slots pruning (flows no longer in stack)
- Add trace entries pruning (keep last N)
- Keep existing completed flows pruning
- Add parameters for limits (with defaults)

#### Paso 2: Add Unit Tests

**Archivo(s) a crear/modificar:** `tests/unit/test_flow_manager.py`

**Código específico:**

```python
def test_prune_state_removes_orphan_slots(empty_state):
    """Test prune_state removes orphaned flow_slots."""
    # Arrange
    manager = FlowManager()

    # Create and complete a flow (should leave orphan slot)
    flow_id = manager.push_flow(empty_state, "test_flow")
    manager.pop_flow(empty_state)

    # Manually add orphan slot
    empty_state["flow_slots"]["orphan_123"] = {"data": "test"}

    # Act
    manager.prune_state(empty_state)

    # Assert
    assert "orphan_123" not in empty_state["flow_slots"]

def test_prune_state_limits_completed_flows(empty_state):
    """Test prune_state limits completed flows."""
    # Arrange
    manager = FlowManager()

    # Create many completed flows
    for i in range(15):
        manager.push_flow(empty_state, f"flow_{i}")
        manager.pop_flow(empty_state)

    # Act
    manager.prune_state(empty_state, max_completed_flows=10)

    # Assert
    assert len(empty_state["metadata"]["completed_flows"]) == 10

def test_prune_state_limits_trace(empty_state):
    """Test prune_state limits trace entries."""
    # Arrange
    manager = FlowManager()

    # Add many trace entries
    for i in range(60):
        empty_state["trace"].append({"event": f"event_{i}", "turn": i})

    # Act
    manager.prune_state(empty_state, max_trace=50)

    # Assert
    assert len(empty_state["trace"]) == 50
    assert empty_state["trace"][0]["event"] == "event_10"  # First kept entry
```

**Explicación:**
- Add tests to existing `test_flow_manager.py`
- Test orphan slots are removed
- Test completed flows are limited
- Test trace entries are limited
- Follow AAA pattern with clear comments

### Tests Requeridos

**Archivo de tests:** `tests/unit/test_flow_manager.py` (add to existing)

**Tests específicos a implementar:**

```python
def test_prune_state_removes_orphan_slots(empty_state):
    """Test prune_state removes orphaned flow_slots."""
    # Arrange
    manager = FlowManager()

    # Create and complete a flow (should leave orphan slot)
    flow_id = manager.push_flow(empty_state, "test_flow")
    manager.pop_flow(empty_state)

    # Manually add orphan slot
    empty_state["flow_slots"]["orphan_123"] = {"data": "test"}

    # Act
    manager.prune_state(empty_state)

    # Assert
    assert "orphan_123" not in empty_state["flow_slots"]

def test_prune_state_limits_completed_flows(empty_state):
    """Test prune_state limits completed flows."""
    # Arrange
    manager = FlowManager()

    # Create many completed flows
    for i in range(15):
        manager.push_flow(empty_state, f"flow_{i}")
        manager.pop_flow(empty_state)

    # Act
    manager.prune_state(empty_state, max_completed_flows=10)

    # Assert
    assert len(empty_state["metadata"]["completed_flows"]) == 10

def test_prune_state_limits_trace(empty_state):
    """Test prune_state limits trace entries."""
    # Arrange
    manager = FlowManager()

    # Add many trace entries
    for i in range(60):
        empty_state["trace"].append({"event": f"event_{i}", "turn": i})

    # Act
    manager.prune_state(empty_state, max_trace=50)

    # Assert
    assert len(empty_state["trace"]) == 50
    assert empty_state["trace"][0]["event"] == "event_10"  # First kept entry

def test_prune_state_keeps_active_slots(empty_state):
    """Test prune_state keeps slots for active flows."""
    # Arrange
    manager = FlowManager()
    flow_id = manager.push_flow(empty_state, "active_flow")
    manager.set_slot(empty_state, "test_slot", "value")

    # Add orphan slot
    empty_state["flow_slots"]["orphan_123"] = {"data": "test"}

    # Act
    manager.prune_state(empty_state)

    # Assert
    assert flow_id in empty_state["flow_slots"]
    assert empty_state["flow_slots"][flow_id]["test_slot"] == "value"
    assert "orphan_123" not in empty_state["flow_slots"]
```

### Criterios de Éxito

- [ ] Pruning logic implemented
- [ ] Orphan slots removed
- [ ] Completed flows limited
- [ ] Trace limited
- [ ] Tests passing (`uv run pytest tests/unit/test_flow_manager.py -v`)
- [ ] Mypy passes (`uv run mypy src/soni/flow/manager.py`)
- [ ] Ruff passes (`uv run ruff check src/soni/flow/manager.py`)

### Validación Manual

**Comandos para validar:**

```bash
# Type checking
uv run mypy src/soni/flow/manager.py

# Tests
uv run pytest tests/unit/test_flow_manager.py -v

# Linting
uv run ruff check src/soni/flow/manager.py
uv run ruff format src/soni/flow/manager.py
```

**Resultado esperado:**
- Mypy shows no errors
- All tests pass
- Ruff shows no linting errors
- Memory management working correctly

### Referencias

- [docs/implementation/02-phase-2-state.md](../../docs/implementation/02-phase-2-state.md) - Task 2.3

### Notas Adicionales

- Method enhances existing `prune_state` (does not replace)
- Default limits are conservative (can be adjusted)
- Orphan slots are identified by comparing flow_stack with flow_slots keys
- Trace pruning keeps most recent entries
