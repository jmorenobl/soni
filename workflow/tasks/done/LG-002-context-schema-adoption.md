## Task: LG-002 - Complete Runtime[RuntimeContext] Adoption

**ID de tarea:** LG-002
**Hito:** LangGraph Modernization
**Dependencias:** Ninguna
**Duración estimada:** 6-8 horas
**Prioridad:** Media (Code Quality)

### Objetivo

Completar la adopción del patrón oficial de LangGraph v0.6.0+ para inyección de contexto: migrar de `config["configurable"]["runtime_context"]` a `Runtime[RuntimeContext]` en las firmas de nodos y usar el parámetro `context=` en `ainvoke()`/`astream()`.

### Contexto

Soni **ya tiene** `context_schema=RuntimeContext` configurado en:
- `src/soni/dm/builder.py` línea 31
- `src/soni/compiler/subgraph.py` línea 50

Sin embargo, los nodos aún usan el patrón manual:

```python
# Current approach (manual - to be replaced)
async def understand_node(state: DialogueState, config: RunnableConfig):
    context = get_runtime_context(config)  # Manual extraction
    flow_manager = context.flow_manager
```

El patrón oficial de LangGraph v0.6.0+ es:

```python
# Target approach (official)
from langgraph.runtime import Runtime

async def understand_node(state: DialogueState, runtime: Runtime[RuntimeContext]):
    flow_manager = runtime.context.flow_manager  # Type-safe access
```

**Beneficios:**
- Type safety completo en tiempo de compilación
- Acceso limpio via `runtime.context`
- Acceso a `runtime.store` y `runtime.stream_writer` si se necesitan
- Alineación con el ecosistema LangGraph

**Referencia:** `ref/langgraph/libs/langgraph/langgraph/runtime.py` - dataclass `Runtime`

### Entregables

- [ ] RuntimeLoop usa `context=` en `ainvoke()`/`astream()`
- [ ] Todos los nodos del DM usan `Runtime[RuntimeContext]`
- [ ] Todas las node factories del compiler usan `Runtime[RuntimeContext]`
- [ ] Command handlers actualizados
- [ ] Pattern handlers actualizados
- [ ] Helper `get_runtime_context()` eliminado
- [ ] Tests actualizados
- [ ] Type checking pasa sin errores

### Implementación Detallada

#### Paso 1: Actualizar invocación del grafo en RuntimeLoop

**Archivo(s) a modificar:** `src/soni/runtime/loop.py`

**Código actual (líneas 166-190):**

```python
# Create runtime context for dependency injection
context = RuntimeContext(
    config=self.config,
    flow_manager=self.flow_manager,
    action_handler=self.action_handler,
    du=self.du,
    slot_extractor=self.slot_extractor,
)

# Build config with thread and context
run_config: dict[str, Any] = {
    "configurable": {
        "thread_id": user_id,
        "runtime_context": context,  # ← Manual injection
    }
}

result = await graph.ainvoke(input_payload, config=final_config)
```

**Código nuevo:**

```python
from langgraph.runtime import Runtime

# Create runtime context for dependency injection
context = RuntimeContext(
    config=self.config,
    flow_manager=self.flow_manager,
    action_handler=self.action_handler,
    du=self.du,
    slot_extractor=self.slot_extractor,
)

# Build config with thread_id only (context passed separately)
run_config: RunnableConfig = {
    "configurable": {
        "thread_id": user_id,
    }
}

# Pass context as explicit argument (LangGraph v0.6.0+)
result = await graph.ainvoke(
    input_payload,
    config=run_config,
    context=context,  # ← Official API
)
```

**Explicación:**
- El contexto se pasa explícitamente con `context=`
- `configurable` solo mantiene `thread_id` para checkpointing
- LangGraph crea internamente el `Runtime` wrapper

#### Paso 2: Actualizar nodos del Dialogue Manager

**Archivos a modificar:**
- `src/soni/dm/nodes/understand.py`
- `src/soni/dm/nodes/execute.py`
- `src/soni/dm/nodes/resume.py`
- `src/soni/dm/nodes/respond.py`

**Ejemplo: understand.py**

**Código actual:**

```python
from langchain_core.runnables import RunnableConfig
from soni.core.types import get_runtime_context

async def understand_node(
    state: DialogueState,
    config: RunnableConfig,
) -> dict[str, Any]:
    runtime_ctx = get_runtime_context(config)
    du = runtime_ctx.du
    slot_extractor = runtime_ctx.slot_extractor
```

**Código nuevo:**

```python
from langgraph.runtime import Runtime
from soni.core.types import RuntimeContext

async def understand_node(
    state: DialogueState,
    runtime: Runtime[RuntimeContext],
) -> dict[str, Any]:
    du = runtime.context.du
    slot_extractor = runtime.context.slot_extractor
```

**Patrón consistente para todos los nodos:**
```python
from langgraph.runtime import Runtime
from soni.core.types import RuntimeContext

async def node_name(
    state: DialogueState,
    runtime: Runtime[RuntimeContext],
) -> dict[str, Any]:
    ctx = runtime.context  # Shorthand for readability
    flow_manager = ctx.flow_manager
    config = ctx.config
    # ...
```

#### Paso 3: Actualizar Command Registry

**Archivo a modificar:** `src/soni/dm/nodes/command_registry.py`

Los command handlers reciben `RuntimeContext` directamente (no `Runtime`), lo cual está bien porque son llamados desde los nodos que ya extrajeron el contexto.

**Verificar que las firmas de handlers son consistentes:**

```python
class CommandHandler(Protocol):
    async def handle(
        self,
        command: Command,
        state: DialogueState,
        context: RuntimeContext,  # Direct context, not Runtime
        expected_slot: str | None = None,
    ) -> HandlerResult | None:
        ...
```

**En los nodos, pasar `runtime.context`:**
```python
# In understand_node
result = await registry.dispatch(
    cmd,
    state_view,
    runtime.context,  # ← Pass the context directly
    expected_slot,
)
```

#### Paso 4: Actualizar Pattern Handlers

**Archivos a modificar:**
- `src/soni/dm/patterns/base.py`
- `src/soni/dm/patterns/correction.py`
- `src/soni/dm/patterns/cancellation.py`
- `src/soni/dm/patterns/clarification.py`
- `src/soni/dm/patterns/handoff.py`

Los patterns ya reciben `RuntimeContext` directamente - **no requieren cambios** si se mantiene la misma interfaz en el dispatch.

#### Paso 5: Actualizar Node Factories del Compiler

**Archivos a modificar:**
- `src/soni/compiler/nodes/action.py`
- `src/soni/compiler/nodes/branch.py`
- `src/soni/compiler/nodes/collect.py`
- `src/soni/compiler/nodes/confirm.py`
- `src/soni/compiler/nodes/say.py`
- `src/soni/compiler/nodes/set_node.py`

**Ejemplo: action.py**

**Código actual:**

```python
from langchain_core.runnables import RunnableConfig

def create_action_node(step: ActionStepConfig) -> NodeFunction:
    async def action_node(state: DialogueState, config: RunnableConfig) -> dict:
        context = get_runtime_context(config)
        handler = context.action_handler
```

**Código nuevo:**

```python
from langgraph.runtime import Runtime
from soni.core.types import RuntimeContext

def create_action_node(step: ActionStepConfig) -> NodeFunction:
    async def action_node(
        state: DialogueState,
        runtime: Runtime[RuntimeContext],
    ) -> dict:
        handler = runtime.context.action_handler
```

**Misma actualización para todas las factories.**

#### Paso 6: Eliminar helper get_runtime_context

**Archivo a modificar:** `src/soni/core/types.py`

**Código a eliminar (líneas 261-283):**

```python
def get_runtime_context(config: Any) -> RuntimeContext:
    """Extract RuntimeContext from LangGraph RunnableConfig.
    ...
    """
    context: RuntimeContext = config["configurable"]["runtime_context"]
    return context
```

**También eliminar la exportación si está en `__all__`.**

#### Paso 7: Actualizar proceso de streaming (si LG-001 ya implementado)

Si `process_message_streaming()` ya existe, aplicar el mismo patrón:

```python
async for chunk in self._components.graph.astream(
    input_payload,
    config=run_config,
    context=context,  # ← Add context parameter
    stream_mode=stream_mode,
):
    yield chunk
```

### TDD Cycle (MANDATORY)

#### Red Phase: Write Failing Tests

**Test file:** `tests/unit/dm/test_runtime_injection.py`

```python
"""Tests for Runtime[RuntimeContext] injection pattern."""

import pytest
from unittest.mock import MagicMock, AsyncMock
from langgraph.runtime import Runtime

from soni.core.types import RuntimeContext


class TestRuntimeInjection:
    """Tests for LangGraph Runtime pattern."""

    @pytest.fixture
    def mock_runtime(self) -> Runtime[RuntimeContext]:
        """Create mock Runtime with RuntimeContext."""
        mock_context = MagicMock(spec=RuntimeContext)
        mock_context.flow_manager = MagicMock()
        mock_context.du = AsyncMock()
        mock_context.action_handler = AsyncMock()
        mock_context.config = MagicMock()
        mock_context.slot_extractor = None

        return Runtime(
            context=mock_context,
            store=None,
            stream_writer=lambda x: None,
            previous=None,
        )

    @pytest.mark.asyncio
    async def test_understand_node_accepts_runtime(self, mock_runtime):
        """Test that understand_node accepts Runtime[RuntimeContext]."""
        from soni.dm.nodes.understand import understand_node

        state = {
            "user_message": "hello",
            "flow_stack": [],
            "flow_slots": {},
            "waiting_for_slot": None,
            "waiting_for_slot_type": None,
            "messages": [],
            "commands": [],
            "flow_state": "idle",
            "metadata": {},
        }

        # Configure mock DU
        mock_runtime.context.du.acall = AsyncMock(
            return_value=MagicMock(commands=[])
        )

        # Should not raise TypeError
        result = await understand_node(state, mock_runtime)
        assert isinstance(result, dict)

    @pytest.mark.asyncio
    async def test_execute_node_accepts_runtime(self, mock_runtime):
        """Test that execute_node accepts Runtime[RuntimeContext]."""
        from soni.dm.nodes.execute import execute_node

        state = {
            "flow_stack": [],
            "flow_slots": {},
            "commands": [],
        }

        result = await execute_node(state, mock_runtime)
        assert isinstance(result, dict)


class TestActionNodeFactory:
    """Tests for action node factory with Runtime."""

    @pytest.mark.asyncio
    async def test_action_node_uses_runtime(self):
        """Test that action nodes accept Runtime parameter."""
        from soni.compiler.nodes.action import create_action_node
        from soni.compiler.definitions import ActionStepConfig

        step = ActionStepConfig(
            type="action",
            action="test_action",
            result_slot="result",
        )

        node_fn = create_action_node(step)

        mock_context = MagicMock(spec=RuntimeContext)
        mock_context.action_handler = AsyncMock()
        mock_context.action_handler.execute = AsyncMock(return_value={"data": "ok"})
        mock_context.flow_manager = MagicMock()
        mock_context.flow_manager.get_active_context.return_value = {
            "flow_id": "test_123",
            "flow_name": "test",
        }
        mock_context.flow_manager.get_all_slots.return_value = {}

        mock_runtime = Runtime(
            context=mock_context,
            store=None,
            stream_writer=lambda x: None,
            previous=None,
        )

        state = {"flow_stack": [{"flow_id": "test_123"}], "flow_slots": {}}

        # Should execute without TypeError
        result = await node_fn(state, mock_runtime)
        assert isinstance(result, dict)
```

**Verify tests fail:**
```bash
uv run pytest tests/unit/dm/test_runtime_injection.py -v
# Expected: FAILED (nodes still use RunnableConfig)
```

#### Green Phase: Make Tests Pass

Implement the changes from "Implementación Detallada" section.

#### Refactor Phase

- Ensure consistent naming (`runtime` parameter everywhere)
- Add type hints to all node return types
- Verify no remaining references to `get_runtime_context`

### Archivos Afectados (Resumen)

| Archivo | Cambio |
|---------|--------|
| `src/soni/runtime/loop.py` | `context=` en ainvoke/astream |
| `src/soni/dm/nodes/understand.py` | `Runtime[RuntimeContext]` |
| `src/soni/dm/nodes/execute.py` | `Runtime[RuntimeContext]` |
| `src/soni/dm/nodes/resume.py` | `Runtime[RuntimeContext]` |
| `src/soni/dm/nodes/respond.py` | `Runtime[RuntimeContext]` |
| `src/soni/compiler/nodes/action.py` | `Runtime[RuntimeContext]` |
| `src/soni/compiler/nodes/branch.py` | `Runtime[RuntimeContext]` |
| `src/soni/compiler/nodes/collect.py` | `Runtime[RuntimeContext]` |
| `src/soni/compiler/nodes/confirm.py` | `Runtime[RuntimeContext]` |
| `src/soni/compiler/nodes/say.py` | `Runtime[RuntimeContext]` |
| `src/soni/compiler/nodes/set_node.py` | `Runtime[RuntimeContext]` |
| `src/soni/core/types.py` | Eliminar `get_runtime_context` |

### Criterios de Éxito

- [ ] `RuntimeLoop.process_message()` usa `context=` parameter
- [ ] Todos los nodos DM usan `Runtime[RuntimeContext]`
- [ ] Todas las node factories usan `Runtime[RuntimeContext]`
- [ ] No hay referencias a `config["configurable"]["runtime_context"]`
- [ ] `get_runtime_context()` eliminado de types.py
- [ ] Tests unitarios pasan
- [ ] Tests de integración pasan
- [ ] `mypy` pasa sin errores
- [ ] Comportamiento funcional idéntico al anterior

### Validación Manual

```bash
# Type checking
uv run mypy src/soni/dm/nodes/ src/soni/runtime/ src/soni/compiler/nodes/

# Unit tests
uv run pytest tests/unit/dm/ tests/unit/compiler/ -v

# Integration test
uv run pytest tests/integration/ -v

# Full test suite
uv run pytest

# Manual validation
uv run soni chat --config examples/banking/domain
```

### Referencias

- [LangGraph Runtime dataclass](ref/langgraph/libs/langgraph/langgraph/runtime.py)
- [LangGraph ainvoke with context](ref/langgraph/libs/langgraph/langgraph/pregel/main.py#L3111-3131)
- [context_schema usage](ref/langgraph/libs/langgraph/langgraph/runtime.py#L68-76)

### Notas Adicionales

- Este cambio es interno, no afecta API pública
- `RuntimeContext` **no necesita** ser frozen/immutable
- Los command handlers y pattern handlers siguen recibiendo `RuntimeContext` directamente (extraído en el nodo)
- Verificar que checkpointing sigue funcionando (el contexto NO se serializa)
