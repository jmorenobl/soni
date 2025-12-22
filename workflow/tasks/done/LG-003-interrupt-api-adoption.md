## Task: LG-003 - Adopt Modern LangGraph interrupt() API

**ID de tarea:** LG-003
**Hito:** LangGraph Modernization
**Dependencias:** LG-002 (Runtime[RuntimeContext] adoption)
**Duración estimada:** 6-8 horas (phased migration)
**Prioridad:** Media-Alta (Critical for Human-in-the-Loop UX)
**Status:** Ready to implement with approved command-based strategy

### Objetivo

Migrar de `flow_state: "waiting_input"` + routers manuales a la función `interrupt()` de LangGraph v1.0+ usando **enfoque command-based** que preserva integración NLU.

**Estrategia aprobada**: Migración en 3 fases (collect → cleanup → confirm) con command-based approach.

### Contexto

**Estado actual (manual):**
```python
# collect.py
return {
    "last_response": prompt,
    "flow_state": "waiting_input",  # Flag manual
    "waiting_for_slot": slot_name,
}

# router
if is_waiting_input(state):
    return END  # Interrupción manual

# RuntimeLoop (siguiente turno)
result = await graph.ainvoke(payload, config)  # Resume implícito
```

**Estado objetivo (API moderna):**
```python
# collect.py
from langgraph.types import interrupt

value = interrupt({"prompt": prompt, "slot": slot_name})  # Pausa aquí
return {"slot_value": value}  # Solo ejecuta al resumir

# RuntimeLoop
result = await graph.ainvoke(payload, config)
if "__interrupt__" in result:
    return result["__interrupt__"][0].value["prompt"]

# Resume (siguiente turno)
result = await graph.ainvoke(Command(resume=user_input), config)
```

**Beneficios del API moderna:**
- Patrón oficial LangGraph v1.0+ (activo soporte)
- `interrupt()` retorna el valor de resume directamente
- Elimina flags manuales (`flow_state`, `is_waiting_input`)
- Mejor integración con checkpointing
- Soporte para múltiples interrupts paralelos

> **IMPORTANTE:** La función `interrupt()` re-ejecuta el nodo completo al resumir.
> El código antes del `interrupt()` se ejecuta dos veces (una al pausar, otra al resumir).

**Referencia:** [Human-in-the-loop Guide](ref/langgraph/docs/docs/how-tos/human_in_the_loop/add-human-in-the-loop.md)

### Estrategia: Command-Based Approach (APROBADA)

**Problema identificado**: ¿Cómo preservar NLU (detección de digressions, correcciones) con interrupt()?

**Solución elegante**:
Los nodos revisan comandos NLU ANTES de llamar `interrupt()`:

```python
async def collect_node(state, runtime):
    # 1. Check if NLU provided value via SetSlot command
    commands = state.get("commands", [])
    for cmd in commands:
        if cmd.type == "SetSlot" and cmd.slot == slot_name:
            # NLU provided value - use it!
            return {"slot_value": cmd.value}

    # 2. No command - interrupt and wait
    user_input = interrupt({"prompt": "Please provide value"})
    return {"slot_value": user_input}
```

**Flujo completo**:
1. Usuario: "100 euros" → NLU genera `SetSlot(amount="100")`
2. `collect_node` ve comando → usa valor, NO interrumpe
3. Usuario: "check balance" → NLU genera `StartFlow("balance")`
4. `collect_node` NO ve SetSlot → interrumpe de nuevo (sigue esperando)

**Ventajas**:
- ✅ Una sola invocación de grafo por turno
- ✅ NLU siempre procesa input (detecta digressions)
- ✅ Compatible con `interrupt()` nativo de LangGraph
- ✅ Más simple que enfoque de doble invocación

### Migración en Fases (APROBADA)

**Fase 1: Collect Node** (3-4 horas)
- Migrar solo nodo `collect` a `interrupt()`
- Implementar command-based approach
- Tests exhaustivos (básico, digression, correction)
- Mantener `confirm` con patrón anterior

**Fase 2: Partial Cleanup** (30 minutos)
- Eliminar `WAITING_INPUT` de código no usado
- Mantener `is_waiting_input()` para `confirm`

**Fase 3: Confirm Node** (2-3 horas)
- Aplicar aprendizajes de Fase 1
- Migrar `confirm` a `interrupt()`
- Cleanup final completo

### Entregables

**Fase 1:**
- [ ] Nodo `collect` usa command-based + `interrupt()`
- [ ] RuntimeLoop detecta `__interrupt__` y retorna prompt
- [ ] Tests: basic collection, digression, correction

**Fase 2:**
- [ ] `FlowState.WAITING_INPUT` eliminado (parcial)
- [ ] Código no usado limpiado

**Fase 3:**
- [ ] Nodo `confirm` usa command-based + `interrupt()`
- [ ] `is_waiting_input()` eliminado completamente
- [ ] Cleanup final (builder, subgraph, resume)
- [ ] Tests completos pasan
- [ ] Comportamiento funcional idéntico

### Implementación Detallada

#### Fase 1, Paso 1: Actualizar nodo Collect (Command-Based)

**Archivo(s) a modificar:** `src/soni/compiler/nodes/collect.py`

**Código actual:**

```python
from soni.core.constants import FlowState

def create_collect_node(step: CollectStepConfig) -> Callable:
    async def collect_node(state, runtime):
        slot_name = step.slot
        current_value = get_slot_value(state, slot_name)

        if current_value is not None:
            return {"flow_state": "active"}

        prompt = generate_prompt(step, state)
        return {
            "flow_state": "waiting_input",  # ← Manual flag
            "waiting_for_slot": slot_name,
            "waiting_for_slot_type": SlotWaitType.COLLECTION,
            "last_response": prompt,
        }

    return collect_node
```

**Código nuevo (Command-Based Approach):**

```python
from langgraph.types import interrupt
from soni.core.commands import SetSlot

def create_collect_node(step: CollectStepConfig) -> Callable:
    async def collect_node(state, runtime):
        slot_name = step.slot
        ctx = runtime.context

        # Check if slot already has value (idempotent - runs twice!)
        current_value = ctx.flow_manager.get_slot(state, slot_name)
        if current_value is not None:
            return {}  # Already collected

        # ✅ COMMAND-BASED: Check if NLU provided value
        commands = state.get("commands", [])
        for cmd in commands:
            if _is_set_slot_for(cmd, slot_name):
                # NLU provided value - use it, no interrupt!
                delta = ctx.flow_manager.set_slot(state, slot_name, cmd.value)
                return _merge_updates({
                    "waiting_for_slot": None,
                    "waiting_for_slot_type": None,
                }, delta)

        # No command - interrupt and wait
        prompt = generate_prompt(step, state, ctx)

        # This pauses execution (raises GraphInterrupt)
        # On resume, returns the user input
        user_value = interrupt({
            "type": "collect",
            "prompt": prompt,
            "slot": slot_name,
        })

        # ⚠️ Code below only runs on RESUME
        delta = ctx.flow_manager.set_slot(state, slot_name, user_value)
        return _merge_updates({
            "waiting_for_slot": None,
            "waiting_for_slot_type": None,
        }, delta)

    return collect_node

def _is_set_slot_for(cmd, slot_name):
    """Check if command is SetSlot for this slot."""
    if isinstance(cmd, dict):
        return cmd.get("type") == "SetSlot" and cmd.get("slot") == slot_name
    return getattr(cmd, "type", None) == "SetSlot" and getattr(cmd, "slot", None) == slot_name
```

**Explicación:**
- `interrupt()` pausa el nodo y envía el prompt al cliente
- Al resumir con `Command(resume=value)`, `user_value` contiene el input
- El código después de `interrupt()` solo se ejecuta al resumir
- No necesitamos `flow_state: waiting_input`

#### Paso 2: Actualizar nodo Confirm

**Archivo(s) a modificar:** `src/soni/compiler/nodes/confirm.py`

**Código nuevo (patrón similar):**

```python
from langgraph.types import interrupt

def create_confirm_node(step: ConfirmStepConfig) -> Callable:
    async def confirm_node(state, runtime):
        slot_name = step.slot
        ctx = runtime.context

        # Build confirmation message
        current_value = ctx.flow_manager.get_slot(state, slot_name)
        prompt = f"Is {current_value} correct? (yes/no)"

        # Pause for confirmation
        confirmation = interrupt({
            "type": "confirm",
            "prompt": prompt,
            "slot": slot_name,
            "current_value": current_value,
        })

        # Handle confirmation response
        # NLU will have parsed "yes"/"no" into affirm/deny
        if confirmation.get("affirmed", False):
            # Confirmed - set confirmed flag
            delta = ctx.flow_manager.set_slot(
                state, f"{slot_name}_confirmed", True
            )
            return merge_delta({}, delta) if delta else {}
        else:
            # Denied - clear slot for re-collection
            delta = ctx.flow_manager.set_slot(state, slot_name, None)
            return merge_delta({"last_response": "OK, please provide the value again."}, delta)

    return confirm_node
```

#### Paso 3: Actualizar RuntimeLoop para manejar interrupts

**Archivo(s) a modificar:** `src/soni/runtime/loop.py`

**Código nuevo:**

```python
from langgraph.types import Command, Interrupt

class RuntimeLoop:
    async def process_message(
        self,
        user_message: str,
        user_id: str = "default",
    ) -> str:
        """Process a user message, handling interrupts transparently."""
        run_config = self._build_run_config(user_id)

        # Check if we're resuming from an interrupt
        state = await self.get_state(user_id)
        is_resuming = self._has_pending_interrupt(state)

        if is_resuming:
            # Resume with user's input
            result = await self._components.graph.ainvoke(
                Command(resume=self._prepare_resume_value(user_message, state)),
                config=run_config,
                context=self._context,
            )
        else:
            # Normal invocation
            payload = self._hydrator.prepare_input(user_message, state)
            result = await self._components.graph.ainvoke(
                payload,
                config=run_config,
                context=self._context,
            )

        # Check if graph interrupted
        if "__interrupt__" in result:
            # Return the interrupt prompt to user
            interrupt_info = result["__interrupt__"][0]
            return interrupt_info.value.get("prompt", "")

        # Normal completion
        return self._extractor.extract(result, payload, None)

    def _has_pending_interrupt(self, state: dict | None) -> bool:
        """Check if there's a pending interrupt to resume."""
        if not state:
            return False
        # Check via graph state API
        # Note: This might need adjustment based on actual API
        return bool(state.get("__interrupt__"))

    def _prepare_resume_value(self, user_message: str, state: dict) -> Any:
        """Prepare the resume value based on interrupt type."""
        interrupt_info = state.get("__interrupt__", [{}])[0]
        interrupt_type = interrupt_info.get("value", {}).get("type")

        if interrupt_type == "collect":
            # For collection, return raw user input
            return user_message
        elif interrupt_type == "confirm":
            # For confirmation, return structured response
            # (NLU would have parsed this, but for simplicity)
            affirmed = user_message.lower() in ("yes", "si", "sí", "ok", "confirm")
            return {"affirmed": affirmed, "raw": user_message}
        else:
            return user_message

    async def get_interrupt_state(self, user_id: str = "default") -> Interrupt | None:
        """Get current interrupt state if any."""
        run_config = self._build_run_config(user_id)
        graph_state = await self._components.graph.aget_state(run_config)

        if graph_state.interrupts:
            return graph_state.interrupts[0]
        return None
```

**Explicación:**
- Detecta si hay interrupt pendiente via `__interrupt__` en estado
- Usa `Command(resume=value)` para resumir
- Extrae prompt del `Interrupt.value` para devolver al usuario
- Prepara el valor de resume según el tipo de interrupt

#### Paso 4: Eliminar manejo manual de flow_state

**Archivos a modificar:**
- `src/soni/core/constants.py` - Eliminar `WAITING_INPUT` de `FlowState`
- `src/soni/core/state.py` - Eliminar `is_waiting_input()`
- `src/soni/dm/builder.py` - Eliminar checks de `is_waiting_input`
- `src/soni/compiler/subgraph.py` - Eliminar routing basado en `is_waiting_input`
- `src/soni/dm/nodes/resume.py` - Simplificar lógica
- `src/soni/core/types.py` - Mantener `flow_state` pero sin `WAITING_INPUT`

**Código a eliminar en `src/soni/core/state.py`:**

```python
# DELETE this function
def is_waiting_input(state: DialogueState) -> bool:
    return state.get("flow_state") == FlowState.WAITING_INPUT
```

**Código a modificar en `src/soni/core/constants.py`:**

```python
class FlowState(StrEnum):
    IDLE = "idle"
    ACTIVE = "active"
    # WAITING_INPUT = "waiting_input"  # REMOVE - handled by interrupt()
    DONE = "done"
    ERROR = "error"
```

#### Paso 5: Simplificar routers

**Archivo(s) a modificar:** `src/soni/dm/builder.py`

**Código actual:**

```python
def route_resume(state: DialogueState) -> str:
    if is_waiting_input(state):
        return NodeName.END
    if state.get("flow_stack"):
        return NodeName.LOOP
    return NodeName.END
```

**Código nuevo:**

```python
def route_resume(state: DialogueState) -> str:
    # No need to check is_waiting_input - interrupt() handles pausing
    if state.get("flow_stack"):
        return NodeName.LOOP
    return NodeName.END
```

### TDD Cycle (MANDATORY)

#### Red Phase: Write Failing Tests

**Test file:** `tests/unit/compiler/test_interrupt_pattern.py`

```python
"""Tests for LangGraph interrupt() pattern."""

import pytest
from unittest.mock import MagicMock, AsyncMock, patch


class TestCollectNodeInterrupt:
    """Tests for collect node with interrupt()."""

    @pytest.mark.asyncio
    async def test_collect_node_calls_interrupt_when_slot_empty(self):
        """Test that collect node uses interrupt() for empty slots."""
        from soni.compiler.nodes.collect import create_collect_node
        from soni.compiler.definitions import CollectStepConfig
        from langgraph.types import Interrupt
        from langgraph.errors import GraphInterrupt

        step = CollectStepConfig(
            type="collect",
            slot="name",
            prompt="What is your name?",
        )

        node_fn = create_collect_node(step)

        mock_context = MagicMock()
        mock_context.flow_manager.get_slot.return_value = None
        mock_runtime = MagicMock()
        mock_runtime.context = mock_context

        state = {"flow_stack": [{"flow_id": "test"}], "flow_slots": {}}

        # Should raise GraphInterrupt (via interrupt() function)
        with pytest.raises(GraphInterrupt) as exc_info:
            await node_fn(state, mock_runtime)

        # Verify interrupt was called with correct prompt
        assert len(exc_info.value.args[0]) == 1
        interrupt_info = exc_info.value.args[0][0]
        assert interrupt_info.value["type"] == "collect"
        assert "name" in interrupt_info.value["prompt"].lower()

    @pytest.mark.asyncio
    async def test_collect_node_skips_interrupt_when_slot_filled(self):
        """Test that collect node skips interrupt when slot has value."""
        from soni.compiler.nodes.collect import create_collect_node
        from soni.compiler.definitions import CollectStepConfig

        step = CollectStepConfig(
            type="collect",
            slot="name",
            prompt="What is your name?",
        )

        node_fn = create_collect_node(step)

        mock_context = MagicMock()
        mock_context.flow_manager.get_slot.return_value = "John"
        mock_runtime = MagicMock()
        mock_runtime.context = mock_context

        state = {"flow_stack": [{"flow_id": "test"}], "flow_slots": {}}

        # Should NOT raise - slot already filled
        result = await node_fn(state, mock_runtime)
        assert isinstance(result, dict)


class TestRuntimeLoopInterrupt:
    """Tests for RuntimeLoop interrupt handling."""

    @pytest.fixture
    def mock_graph(self):
        graph = MagicMock()
        graph.ainvoke = AsyncMock()
        graph.aget_state = AsyncMock()
        return graph

    @pytest.mark.asyncio
    async def test_returns_prompt_on_interrupt(self, mock_graph):
        """Test that RuntimeLoop returns prompt when graph interrupts."""
        from soni.runtime.loop import RuntimeLoop
        from langgraph.types import Interrupt

        # Setup mock to return interrupt
        mock_graph.ainvoke.return_value = {
            "__interrupt__": [
                Interrupt(
                    value={"type": "collect", "prompt": "What is your name?"},
                    id="test-id",
                )
            ]
        }
        mock_graph.aget_state.return_value = MagicMock(interrupts=[])

        loop = RuntimeLoop.__new__(RuntimeLoop)
        loop._components = MagicMock()
        loop._components.graph = mock_graph
        loop._context = MagicMock()
        loop._hydrator = MagicMock()
        loop._hydrator.prepare_input.return_value = {}
        loop._build_run_config = MagicMock(return_value={})
        loop.get_state = AsyncMock(return_value=None)

        # Act
        response = await loop.process_message("start flow")

        # Assert
        assert response == "What is your name?"

    @pytest.mark.asyncio
    async def test_resumes_with_command(self, mock_graph):
        """Test that RuntimeLoop resumes with Command when continuing."""
        from soni.runtime.loop import RuntimeLoop
        from langgraph.types import Command

        # First call - simulate interrupt state
        mock_graph.aget_state.return_value = MagicMock(
            interrupts=[MagicMock(value={"type": "collect"})]
        )
        mock_graph.ainvoke.return_value = {"last_response": "Thank you!"}

        loop = RuntimeLoop.__new__(RuntimeLoop)
        loop._components = MagicMock()
        loop._components.graph = mock_graph
        loop._context = MagicMock()
        loop._extractor = MagicMock()
        loop._extractor.extract.return_value = "Thank you!"
        loop._build_run_config = MagicMock(return_value={})
        loop.get_state = AsyncMock(return_value={"__interrupt__": [{}]})

        # Act - provide resume value
        response = await loop.process_message("John")

        # Assert - should have called with Command
        call_args = mock_graph.ainvoke.call_args
        assert isinstance(call_args[0][0], Command)
```

**Verify tests fail:**
```bash
uv run pytest tests/unit/compiler/test_interrupt_pattern.py -v
# Expected: FAILED (interrupt pattern not implemented yet)
```

#### Green Phase: Make Tests Pass

Implement the code from "Implementación Detallada" section.

### Archivos Afectados (Resumen)

| Archivo | Cambio |
|---------|--------|
| `src/soni/compiler/nodes/collect.py` | Usar `interrupt()` |
| `src/soni/compiler/nodes/confirm.py` | Usar `interrupt()` |
| `src/soni/compiler/nodes/confirm_handlers.py` | Adaptar al nuevo patrón |
| `src/soni/runtime/loop.py` | Detectar `__interrupt__`, resume con `Command` |
| `src/soni/core/constants.py` | Eliminar `WAITING_INPUT` |
| `src/soni/core/state.py` | Eliminar `is_waiting_input()` |
| `src/soni/dm/builder.py` | Simplificar router |
| `src/soni/compiler/subgraph.py` | Eliminar routing de interrupt |
| `src/soni/dm/nodes/resume.py` | Simplificar |

### Criterios de Éxito

- [ ] Nodos `collect` usan `interrupt()` para pausar
- [ ] Nodos `confirm` usan `interrupt()` para pausar
- [ ] RuntimeLoop detecta `__interrupt__` y devuelve prompt
- [ ] RuntimeLoop resume con `Command(resume=value)`
- [ ] `FlowState.WAITING_INPUT` eliminado
- [ ] `is_waiting_input()` eliminado
- [ ] Todos los tests pasan (unit + integration)
- [ ] `mypy` pasa sin errores
- [ ] Conversación funciona igual que antes

### Validación Manual

```bash
# Unit tests
uv run pytest tests/unit/compiler/test_interrupt_pattern.py -v

# Integration tests
uv run pytest tests/integration/ -v

# Full test suite
uv run pytest

# Manual validation
uv run soni chat --config examples/banking/domain
# Try: "Quiero hacer una transferencia"
# Should prompt for amount and wait
# Provide: "100 euros"
# Should prompt for recipient and wait
# ...complete flow
```

### Referencias

- [LangGraph interrupt() function](ref/langgraph/libs/langgraph/langgraph/types.py#L401-524)
- [Human-in-the-loop Guide](ref/langgraph/docs/docs/how-tos/human_in_the_loop/add-human-in-the-loop.md)
- [Command primitive](ref/langgraph/libs/langgraph/langgraph/types.py#L340-400)

### Notas Adicionales

- **Re-ejecución del nodo:** Al resumir, todo el nodo se ejecuta de nuevo. El código antes de `interrupt()` debe ser idempotente.
- **Checkpointer requerido:** `interrupt()` requiere un checkpointer configurado.
- **NLU en resume:** Considerar si el NLU debe procesar el input de resume o si va directo al slot.
- **Subgraphs:** El patrón funciona en subgraphs; los interrupts se propagan al grafo padre.
- **Múltiples interrupts:** Si hay múltiples `interrupt()` en paralelo, usar `Command.resume` con mapping de IDs.
- **Migración gradual:** Considerar migrar un flow a la vez para minimizar riesgo.
