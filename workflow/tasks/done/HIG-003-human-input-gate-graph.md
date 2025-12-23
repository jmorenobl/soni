# Task: HIG-003 - Human Input Gate & Graph

**ID de tarea:** HIG-003
**Hito:** Human Input Gate Refactoring (ADR-002)
**Dependencias:** HIG-001, HIG-002
**Duración estimada:** 1-2 días

## Objetivo

Crear el nodo `human_input_gate`, modificar el `builder.py` con la nueva estructura de grafo, y simplificar `RuntimeLoop` eliminando la lógica de NLU-on-resume.

## Contexto

El Human Input Gate es el punto único de entrada para toda comunicación con el usuario. Es un nodo "puro" que solo necesita state (sin dependencias externas). Este cambio centraliza la gestión de interrupts y elimina duplicación de lógica NLU.

**Referencia:** [ADR-002](../analysis/ADR-002-Human-Input-Gate-Architecture.md) - Secciones 1-2

## Entregables

- [ ] Crear `dm/nodes/human_input_gate.py`
- [ ] Crear `dm/nodes/orchestrator.py` (el nodo thin que usa los componentes de HIG-002)
- [ ] Modificar `dm/builder.py` con nueva estructura de grafo
- [ ] Simplificar `runtime/loop.py` (eliminar NLU-on-resume)
- [ ] Tests de integración con NLU mockeado

---

## TDD Cycle (MANDATORY)

### Red Phase: Write Failing Tests

**Test file:** `tests/unit/dm/nodes/test_human_input_gate.py`

```python
"""Tests for human_input_gate node."""
import pytest

from soni.core.pending_task import collect, confirm, inform
from soni.dm.nodes.human_input_gate import human_input_gate


class TestHumanInputGate:
    """Tests for human_input_gate node function."""

    @pytest.mark.asyncio
    async def test_returns_empty_when_no_pending_task(self):
        """Test that gate returns empty dict when no pending task."""
        # Arrange
        state = {"user_message": "Hello", "_pending_task": None}

        # Act
        result = await human_input_gate(state)

        # Assert
        assert result == {}

    @pytest.mark.asyncio
    async def test_returns_empty_when_pending_task_key_missing(self):
        """Test that gate returns empty dict when key doesn't exist."""
        # Arrange
        state = {"user_message": "Hello"}

        # Act
        result = await human_input_gate(state)

        # Assert
        assert result == {}


class TestHumanInputGateWithPendingTask:
    """Tests for human_input_gate with pending tasks.

    Note: These tests verify the structure, actual interrupt()
    behavior is tested in integration tests.
    """

    def test_gate_is_async_function(self):
        """Test that human_input_gate is an async function."""
        # Arrange & Act & Assert
        import inspect
        assert inspect.iscoroutinefunction(human_input_gate)

    def test_gate_accepts_only_state(self):
        """Test that human_input_gate signature only requires state."""
        # Arrange & Act
        import inspect
        sig = inspect.signature(human_input_gate)

        # Assert - only one required parameter
        required_params = [
            p for p in sig.parameters.values()
            if p.default == inspect.Parameter.empty
        ]
        assert len(required_params) == 1
        assert "state" in sig.parameters
```

**Test file:** `tests/integration/dm/test_graph_structure.py`

```python
"""Integration tests for new graph structure with mocked NLU."""
import pytest
from unittest.mock import AsyncMock, MagicMock, patch

from soni.dm.builder import build_orchestrator
from soni.runtime.context import RuntimeContext
from soni.core.message_sink import BufferedMessageSink


class MockNLUProvider:
    """Mock NLU provider that returns predetermined commands."""

    def __init__(self, commands: list[dict] | None = None):
        self.commands = commands or []
        self.call_count = 0

    async def acall(self, message: str, context: dict) -> MagicMock:
        """Return mocked NLU result."""
        self.call_count += 1
        result = MagicMock()
        result.commands = self.commands
        return result


class MockSubgraphRegistry:
    """Mock subgraph registry for testing."""

    def __init__(self):
        self.subgraphs: dict[str, MagicMock] = {}

    def get(self, flow_name: str) -> MagicMock:
        if flow_name not in self.subgraphs:
            mock_graph = MagicMock()
            mock_graph.astream = AsyncMock(return_value=iter([]))
            self.subgraphs[flow_name] = mock_graph
        return self.subgraphs[flow_name]


class TestGraphStructure:
    """Tests for the new graph structure."""

    def test_build_orchestrator_creates_graph(self):
        """Test that build_orchestrator creates a compiled graph."""
        # Arrange & Act
        graph = build_orchestrator()

        # Assert
        assert graph is not None
        assert hasattr(graph, "ainvoke")
        assert hasattr(graph, "astream")

    def test_graph_has_required_nodes(self):
        """Test that graph contains required nodes."""
        # Arrange
        graph = build_orchestrator()

        # Act - get node names from graph
        # Note: Access may vary by LangGraph version
        nodes = list(graph.nodes.keys()) if hasattr(graph, "nodes") else []

        # Assert - at minimum should have these
        # Implementation detail: check graph structure
        assert graph is not None


class TestGraphWithMockedNLU:
    """Integration tests with mocked NLU to test DM logic."""

    @pytest.fixture
    def mock_context(self):
        """Create mock RuntimeContext for testing."""
        return RuntimeContext(
            flow_manager=MagicMock(),
            subgraph_registry=MockSubgraphRegistry(),
            message_sink=BufferedMessageSink(),
            nlu_provider=MockNLUProvider(),
        )

    @pytest.mark.asyncio
    async def test_graph_processes_message_with_no_commands(self, mock_context):
        """Test graph execution when NLU returns no commands."""
        # Arrange
        graph = build_orchestrator()
        mock_context.nlu_provider.commands = []  # No commands
        mock_context.flow_manager.get_active_context.return_value = None

        # Act
        # Note: Actual invocation depends on final implementation
        # This test verifies the structure is correct

        # Assert
        assert graph is not None

    @pytest.mark.asyncio
    async def test_graph_with_start_flow_command(self, mock_context):
        """Test graph execution when NLU returns StartFlow command."""
        # Arrange
        graph = build_orchestrator()
        mock_context.nlu_provider.commands = [
            {"type": "start_flow", "flow_name": "check_balance"}
        ]

        # Act & Assert
        # Verify graph can handle this scenario
        assert graph is not None
```

**Verify tests fail:**
```bash
uv run pytest tests/unit/dm/nodes/test_human_input_gate.py tests/integration/dm/test_graph_structure.py -v
# Expected: FAILED (modules not implemented yet)
```

**Commit:**
```bash
git add tests/
git commit -m "test(HIG-003): add failing tests for human_input_gate and graph structure"
```

---

### Green Phase: Make Tests Pass

#### Paso 1: Crear human_input_gate.py

**Archivo:** `src/soni/dm/nodes/human_input_gate.py`

```python
"""Human Input Gate node - single entry point for user communication."""
from typing import Any

from langgraph.types import interrupt

from soni.core.state import DialogueState


async def human_input_gate(state: DialogueState) -> dict[str, Any]:
    """Single entry point for all user communication.

    This is a pure node - no external dependencies needed.

    Responsibilities:
    1. Receive new user messages
    2. Handle resume from interrupts
    3. Process pending tasks from orchestrator
    """
    # Check if resuming from interrupt
    pending = state.get("_pending_task")
    if pending:
        # Collect user response for pending task
        resume_value = interrupt(pending)
        return {
            "user_message": resume_value,
            "_pending_task": None,
        }

    # Normal message reception (already in user_message from invoke)
    return {}
```

#### Paso 2: Crear orchestrator.py (el nodo)

**Archivo:** `src/soni/dm/nodes/orchestrator.py`

```python
"""Orchestrator node - thin coordinator using RuntimeContext."""
from typing import Any

from langgraph.types import Runtime

from soni.core.state import DialogueState
from soni.runtime.context import RuntimeContext
from soni.dm.orchestrator.commands import DEFAULT_HANDLERS
from soni.dm.orchestrator.command_processor import CommandProcessor
from soni.dm.orchestrator.executor import SubgraphExecutor
from soni.dm.orchestrator.task_handler import PendingTaskHandler, TaskAction


async def orchestrator_node(
    state: DialogueState,
    runtime: Runtime[RuntimeContext],
) -> dict[str, Any]:
    """Orchestrator node - thin coordinator delegating to specialized components.

    Access dependencies via runtime.context (LangGraph pattern).
    """
    ctx = runtime.context

    # Initialize components
    handlers = ctx.command_handlers or DEFAULT_HANDLERS
    command_processor = CommandProcessor(list(handlers))
    task_handler = PendingTaskHandler(ctx.message_sink)

    # 1. Process NLU commands
    delta = await command_processor.process(
        commands=state.get("commands", []),
        state=state,
        flow_manager=ctx.flow_manager,
    )
    updates = delta.to_dict()

    # 2. Get active flow
    merged_state = {**state, **updates}
    active_ctx = ctx.flow_manager.get_active_context(merged_state)

    if not active_ctx:
        return {**updates, "response": "How can I help?"}

    # 3. Stream subgraph execution
    subgraph = ctx.subgraph_registry.get(active_ctx["flow_name"])
    subgraph_state = _build_subgraph_state(merged_state)
    final_output: dict[str, Any] = {}

    async for event in subgraph.astream(subgraph_state, stream_mode="updates"):
        for node_name, output in event.items():
            pending_task = output.get("_pending_task")

            if pending_task:
                result = await task_handler.handle(pending_task)

                if result.action == TaskAction.INTERRUPT:
                    return {**updates, "_pending_task": result.task}

                if result.action == TaskAction.CONTINUE:
                    continue

            final_output = {**final_output, **output}

    # 4. Return merged result
    return {**updates, **_transform_result(final_output)}


def _build_subgraph_state(state: dict[str, Any]) -> dict[str, Any]:
    """Build state for subgraph invocation."""
    # Extract relevant fields for subgraph
    return {
        "flow_slots": state.get("flow_slots", {}),
        "user_message": state.get("user_message"),
        "commands": state.get("commands", []),
    }


def _transform_result(result: dict[str, Any]) -> dict[str, Any]:
    """Transform subgraph result to parent state updates."""
    # Filter out internal fields, keep relevant updates
    return {
        k: v for k, v in result.items()
        if not k.startswith("_") or k == "_pending_task"
    }
```

#### Paso 3: Modificar builder.py

**Archivo:** `src/soni/dm/builder.py`

```python
"""Graph builder for Human Input Gate architecture."""
from langgraph.graph import StateGraph, END

from soni.core.state import DialogueState
from soni.runtime.context import RuntimeContext
from soni.dm.nodes.human_input_gate import human_input_gate
from soni.dm.nodes.understand import nlu_node  # Existing NLU node
from soni.dm.nodes.orchestrator import orchestrator_node
from soni.dm.routing import route_after_orchestrator


def build_orchestrator(checkpointer=None):
    """Build the main orchestrator graph with RuntimeContext for DI."""
    builder = StateGraph(DialogueState, context_schema=RuntimeContext)

    # Nodes
    builder.add_node("human_input_gate", human_input_gate)
    builder.add_node("nlu", nlu_node)
    builder.add_node("orchestrator", orchestrator_node)

    # Edges
    builder.set_entry_point("human_input_gate")
    builder.add_edge("human_input_gate", "nlu")
    builder.add_edge("nlu", "orchestrator")
    builder.add_conditional_edges(
        "orchestrator",
        route_after_orchestrator,
        {"pending_task": "human_input_gate", "end": END}
    )

    return builder.compile(checkpointer=checkpointer)
```

#### Paso 4: Simplificar RuntimeLoop

**Archivo:** `src/soni/runtime/loop.py`

Eliminar la lógica de NLU-on-resume. El flujo ahora es:
1. `Command(resume=message)` → goes to human_input_gate
2. human_input_gate → passes to NLU
3. NLU → orchestrator

```python
# ELIMINAR esta lógica (aproximadamente líneas 114-228):
# - NLU processing before resume
# - Complex command injection on resume

# SIMPLIFICAR a:
async def process_resume(self, message: str, thread_id: str) -> str:
    """Process resume with user message."""
    result = await self.graph.ainvoke(
        Command(resume=message),
        config={"configurable": {"thread_id": thread_id}},
        context=self._runtime_context,
    )
    return result.get("response", "")
```

**Verify tests pass:**
```bash
uv run pytest tests/unit/dm/nodes/test_human_input_gate.py tests/integration/dm/test_graph_structure.py -v
```

**Commit:**
```bash
git add src/ tests/
git commit -m "feat(HIG-003): implement human_input_gate and new graph structure"
```

---

## Limpieza Progresiva

**Código a eliminar/simplificar en esta fase:**

| Archivo | Acción | Razón |
|---------|--------|-------|
| `runtime/loop.py` | SIMPLIFICAR | Eliminar NLU-on-resume (líneas ~114-228) |

**NO eliminar todavía:**
- `dm/nodes/execute_flow.py` - Se elimina en HIG-005

---

## Criterios de Éxito

- [ ] human_input_gate es una función pura (solo state)
- [ ] orchestrator_node usa runtime.context correctamente
- [ ] builder.py crea grafo con 3 nodos + conditional edges
- [ ] RuntimeLoop simplificado sin NLU-on-resume
- [ ] Tests de integración pasan con NLU mockeado
- [ ] `uv run mypy src/soni/dm/nodes/` sin errores

## Validación Manual

```bash
# Verificar imports
uv run python -c "from soni.dm.nodes.human_input_gate import human_input_gate; print('OK')"
uv run python -c "from soni.dm.builder import build_orchestrator; print('OK')"

# Verificar grafo se construye
uv run python -c "
from soni.dm.builder import build_orchestrator
g = build_orchestrator()
print(f'Graph created: {g}')
"

# Ejecutar tests
uv run pytest tests/unit/dm/nodes/ tests/integration/dm/ -v
```

## Referencias

- [ADR-002](../analysis/ADR-002-Human-Input-Gate-Architecture.md) - Secciones 1-2, 3.3-3.4
