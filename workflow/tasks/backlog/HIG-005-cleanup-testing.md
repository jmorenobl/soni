# Task: HIG-005 - Cleanup & Final Testing

**ID de tarea:** HIG-005
**Hito:** Human Input Gate Refactoring (ADR-002)
**Dependencias:** HIG-001, HIG-002, HIG-003, HIG-004
**Duración estimada:** 1 día

## Objetivo

Limpieza final: eliminar código obsoleto (`execute_flow.py`, campos de estado obsoletos), actualizar/eliminar tests obsoletos, y realizar tests de integración completos con NLU mockeado.

## Contexto

Esta es la tarea final del refactoring. Todo el código nuevo está implementado y funcionando. Ahora limpiamos el código legacy y verificamos que todo funciona end-to-end.

**Referencia:** [ADR-002](../analysis/ADR-002-Human-Input-Gate-Architecture.md) - Phase 5

## Entregables

- [ ] Eliminar `dm/nodes/execute_flow.py`
- [ ] Eliminar `_need_input` de DialogueState y cualquier uso
- [ ] Eliminar `_pending_prompt` de DialogueState y cualquier uso
- [ ] Actualizar/eliminar tests obsoletos
- [ ] Tests de integración end-to-end con NLU mockeado
- [ ] Documentación actualizada

---

## Limpieza de Código (NO TDD para eliminación)

### Archivos a ELIMINAR

| Archivo | Razón |
|---------|-------|
| `src/soni/dm/nodes/execute_flow.py` | Reemplazado por `orchestrator.py` |
| Tests que usan `execute_flow_node` | Obsoletos |

### Campos de Estado a ELIMINAR

**Archivo:** `src/soni/core/state.py`

```python
# ELIMINAR estos campos de DialogueState:
_need_input: NotRequired[bool]      # Obsoleto - usar requires_input()
_pending_prompt: NotRequired[dict]  # Obsoleto - usar _pending_task
```

### Imports a ELIMINAR

Buscar y eliminar cualquier import de:
```python
from soni.dm.nodes.execute_flow import execute_flow_node  # ELIMINAR
```

---

## Tests Obsoletos a Eliminar/Actualizar

### Tests a ELIMINAR

```bash
# Buscar tests que usan execute_flow_node
grep -r "execute_flow" tests/

# Archivos típicos a eliminar:
# tests/unit/dm/nodes/test_execute_flow.py
# tests/integration/test_execute_flow_*.py
```

### Tests a ACTUALIZAR

| Test File | Actualización Necesaria |
|-----------|------------------------|
| `tests/integration/test_full_conversation.py` | Usar nuevo grafo y mocked NLU |
| Tests que verifican `_need_input` | Eliminar o cambiar a `_pending_task` |

---

## TDD: Integration Tests

**Test file:** `tests/integration/test_human_input_gate_e2e.py`

```python
"""End-to-end integration tests for Human Input Gate architecture.

Uses mocked NLU to ensure deterministic testing of DM logic.
"""
import pytest
from unittest.mock import MagicMock, AsyncMock

from soni.dm.builder import build_orchestrator
from soni.runtime.context import RuntimeContext
from soni.core.message_sink import BufferedMessageSink
from soni.core.pending_task import is_collect, is_confirm, is_inform


class MockNLUProvider:
    """Deterministic mock NLU for testing DM logic."""

    def __init__(self):
        self.responses: list[dict] = []
        self._response_index = 0

    def set_responses(self, responses: list[list[dict]]):
        """Set sequence of command responses."""
        self.responses = responses
        self._response_index = 0

    async def acall(self, message: str, context: dict) -> MagicMock:
        """Return next predetermined response."""
        if self._response_index < len(self.responses):
            commands = self.responses[self._response_index]
            self._response_index += 1
        else:
            commands = []

        result = MagicMock()
        result.commands = commands
        return result


class MockSubgraphRegistry:
    """Mock subgraph registry returning predetermined results."""

    def __init__(self):
        self.flow_results: dict[str, list[dict]] = {}

    def set_flow_result(self, flow_name: str, outputs: list[dict]):
        """Set outputs for a specific flow."""
        self.flow_results[flow_name] = outputs

    def get(self, flow_name: str) -> MagicMock:
        """Return mock subgraph that yields predetermined outputs."""
        outputs = self.flow_results.get(flow_name, [{}])

        async def mock_astream(state, stream_mode=None):
            for output in outputs:
                yield {"node": output}

        mock_graph = MagicMock()
        mock_graph.astream = mock_astream
        return mock_graph


class MockFlowManager:
    """Mock flow manager for predictable flow stack behavior."""

    def __init__(self):
        self.flow_stack = []
        self.flow_slots = {}

    def push_flow(self, state, flow_name):
        from soni.flow.delta import FlowDelta
        flow_id = f"{flow_name}_test"
        new_ctx = {"flow_name": flow_name, "flow_id": flow_id}
        self.flow_stack.append(new_ctx)
        return FlowDelta(flow_stack=self.flow_stack.copy())

    def pop_flow(self, state):
        from soni.flow.delta import FlowDelta
        if self.flow_stack:
            self.flow_stack.pop()
        return FlowDelta(flow_stack=self.flow_stack.copy())

    def get_active_context(self, state):
        return self.flow_stack[-1] if self.flow_stack else None

    def set_slot(self, state, slot_name, slot_value):
        from soni.flow.delta import FlowDelta
        self.flow_slots[slot_name] = slot_value
        return FlowDelta(flow_slots=self.flow_slots.copy())


@pytest.fixture
def mock_context():
    """Create fully mocked RuntimeContext."""
    return RuntimeContext(
        flow_manager=MockFlowManager(),
        subgraph_registry=MockSubgraphRegistry(),
        message_sink=BufferedMessageSink(),
        nlu_provider=MockNLUProvider(),
    )


class TestHumanInputGateE2E:
    """End-to-end tests for the Human Input Gate architecture."""

    @pytest.mark.asyncio
    async def test_start_flow_triggers_collect(self, mock_context):
        """Test: User starts flow → NLU returns StartFlow → Orchestrator invokes subgraph → CollectTask returned."""
        # Arrange
        graph = build_orchestrator()

        # Mock NLU to return StartFlow command
        mock_context.nlu_provider.set_responses([
            [{"type": "start_flow", "flow_name": "check_balance"}]
        ])

        # Mock subgraph to return CollectTask
        from soni.core.pending_task import collect
        mock_context.subgraph_registry.set_flow_result("check_balance", [
            {"_pending_task": collect(prompt="Which account?", slot="account")}
        ])

        # Act
        result = await graph.ainvoke(
            {"user_message": "Check my balance"},
            context=mock_context,
        )

        # Assert
        assert "_pending_task" in result
        assert is_collect(result["_pending_task"])
        assert result["_pending_task"]["slot"] == "account"

    @pytest.mark.asyncio
    async def test_inform_without_wait_sends_immediately(self, mock_context):
        """Test: InformTask without wait_for_ack sends message and continues."""
        # Arrange
        graph = build_orchestrator()
        sink = mock_context.message_sink

        mock_context.nlu_provider.set_responses([
            [{"type": "start_flow", "flow_name": "check_balance"}]
        ])

        from soni.core.pending_task import inform
        mock_context.subgraph_registry.set_flow_result("check_balance", [
            {"_pending_task": inform(prompt="Your balance is $1,234", wait_for_ack=False)}
        ])
        mock_context.flow_manager.push_flow({}, "check_balance")

        # Act
        result = await graph.ainvoke(
            {"user_message": "Check balance"},
            context=mock_context,
        )

        # Assert
        assert sink.messages == ["Your balance is $1,234"]
        # Flow should complete (no pending task requiring input)

    @pytest.mark.asyncio
    async def test_cancel_flow_pops_stack(self, mock_context):
        """Test: CancelFlow command pops flow from stack."""
        # Arrange
        graph = build_orchestrator()
        mock_context.flow_manager.push_flow({}, "transfer_funds")

        mock_context.nlu_provider.set_responses([
            [{"type": "cancel_flow"}]
        ])

        # Act
        result = await graph.ainvoke(
            {"user_message": "Cancel"},
            context=mock_context,
        )

        # Assert
        assert mock_context.flow_manager.flow_stack == []

    @pytest.mark.asyncio
    async def test_no_obsolete_fields_in_state(self, mock_context):
        """Test: Result does not contain obsolete fields."""
        # Arrange
        graph = build_orchestrator()
        mock_context.nlu_provider.set_responses([[]])

        # Act
        result = await graph.ainvoke(
            {"user_message": "Hello"},
            context=mock_context,
        )

        # Assert
        assert "_need_input" not in result
        assert "_pending_prompt" not in result


class TestMockedNLUDeterminism:
    """Tests verifying mocked NLU provides deterministic results."""

    @pytest.mark.asyncio
    async def test_mock_nlu_returns_predetermined_commands(self):
        """Test that MockNLUProvider returns commands in order."""
        # Arrange
        nlu = MockNLUProvider()
        nlu.set_responses([
            [{"type": "start_flow", "flow_name": "flow1"}],
            [{"type": "set_slot", "slot_name": "x", "slot_value": "1"}],
            [],
        ])

        # Act
        r1 = await nlu.acall("msg1", {})
        r2 = await nlu.acall("msg2", {})
        r3 = await nlu.acall("msg3", {})

        # Assert
        assert r1.commands == [{"type": "start_flow", "flow_name": "flow1"}]
        assert r2.commands == [{"type": "set_slot", "slot_name": "x", "slot_value": "1"}]
        assert r3.commands == []

    @pytest.mark.asyncio
    async def test_mock_nlu_repeatable(self):
        """Test that MockNLUProvider can be reset for repeatable tests."""
        # Arrange
        nlu = MockNLUProvider()
        commands = [[{"type": "start_flow", "flow_name": "test"}]]

        # Act - first run
        nlu.set_responses(commands)
        r1 = await nlu.acall("msg", {})

        # Act - reset and run again
        nlu.set_responses(commands)
        r2 = await nlu.acall("msg", {})

        # Assert - both should return same result
        assert r1.commands == r2.commands
```

**Commit:**
```bash
git add tests/
git commit -m "test(HIG-005): add e2e integration tests with mocked NLU"
```

---

## Pasos de Limpieza

### Paso 1: Eliminar execute_flow.py

```bash
rm src/soni/dm/nodes/execute_flow.py
git add -u
git commit -m "chore(HIG-005): delete obsolete execute_flow.py"
```

### Paso 2: Limpiar imports

```bash
# Buscar y eliminar imports obsoletos
grep -r "execute_flow" src/
# Editar archivos que lo importen
```

### Paso 3: Eliminar campos de estado obsoletos

**Archivo:** `src/soni/core/state.py`

```python
# ELIMINAR:
_need_input: NotRequired[bool]
_pending_prompt: NotRequired[dict]
```

### Paso 4: Eliminar tests obsoletos

```bash
# Eliminar tests de execute_flow
rm tests/unit/dm/nodes/test_execute_flow.py  # si existe
rm tests/integration/test_execute_flow*.py   # si existen

git add -u
git commit -m "chore(HIG-005): remove obsolete tests"
```

### Paso 5: Verificar sin código obsoleto

```bash
# Verificar que no hay referencias a código eliminado
grep -r "_need_input" src/
grep -r "_pending_prompt" src/
grep -r "execute_flow" src/

# Todos deben retornar vacío
```

---

## Criterios de Éxito

- [ ] `execute_flow.py` eliminado
- [ ] `_need_input` eliminado de todo el código
- [ ] `_pending_prompt` eliminado de todo el código
- [ ] No hay imports huérfanos
- [ ] Tests obsoletos eliminados
- [ ] Nuevos tests de integración pasan
- [ ] `uv run pytest` completo pasa
- [ ] `uv run mypy src/` sin errores
- [ ] `uv run ruff check src/` sin errores

## Validación Final

```bash
# 1. Verificar código limpio
grep -r "execute_flow" src/     # Expected: empty
grep -r "_need_input" src/      # Expected: empty
grep -r "_pending_prompt" src/  # Expected: empty

# 2. Ejecutar suite completa de tests
uv run pytest -v

# 3. Verificar tipos
uv run mypy src/soni/

# 4. Verificar linting
uv run ruff check src/

# 5. Verificar que el servidor arranca
uv run soni server --config examples/banking/domain &
sleep 5
curl http://localhost:8000/health
kill %1
```

## Referencias

- [ADR-002](../analysis/ADR-002-Human-Input-Gate-Architecture.md) - Phase 5: Cleanup & Testing
- Todas las tareas previas: HIG-001, HIG-002, HIG-003, HIG-004
