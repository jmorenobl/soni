## Task: 001 - Fix Direct State Mutation in understand_node

**ID de tarea:** 001
**Hito:** 1 - Critical Fixes
**Dependencias:** Ninguna
**Duración estimada:** 4 horas
**Prioridad:** CRÍTICA

### Objetivo

Eliminar la mutación directa de estado en `understand_node` que viola el patrón inmutable utilizado en todo el sistema Soni. Actualmente el código modifica `state["flow_stack"]` y `state["flow_slots"]` directamente durante el procesamiento de comandos, lo cual puede causar bugs sutiles y viola el contrato de LangGraph.

### Contexto

El sistema Soni utiliza un patrón de FlowDelta inmutable donde las operaciones de estado retornan deltas que se fusionan al final. Sin embargo, en `dm/nodes/understand.py:293-297`, el código muta el estado directamente durante el loop de procesamiento de comandos:

```python
# ACTUAL (INCORRECTO)
if "flow_stack" in result.updates:
    state["flow_stack"] = result.updates["flow_stack"]  # Mutación directa!
if "flow_slots" in result.updates:
    state["flow_slots"] = result.updates["flow_slots"]  # Mutación directa!
```

**Por qué es problemático:**
1. Viola el contrato de LangGraph donde el estado debe ser inmutable
2. Los handlers subsecuentes ven estado parcialmente modificado
3. Dificulta el debugging y testing
4. Inconsistente con el resto del sistema (FlowManager retorna FlowDelta)

### Entregables

- [ ] Refactorizar `understand_node` para acumular updates sin mutar estado
- [ ] Crear view inmutable del estado para handlers que necesiten leer estado actualizado
- [ ] Actualizar tests unitarios para verificar inmutabilidad
- [ ] Documentar el patrón correcto en el código

### Implementación Detallada

#### Paso 1: Crear StateView inmutable

**Archivo(s) a crear/modificar:** `src/soni/dm/nodes/understand.py`

**Código específico:**

```python
from typing import Any
from soni.core.types import DialogueState

def create_state_view(base_state: DialogueState, accumulated_updates: dict[str, Any]) -> DialogueState:
    """Create an immutable view of state with accumulated updates applied.

    This allows subsequent command handlers to see the effect of previous
    commands without mutating the original state.
    """
    # Create shallow copy with updates overlaid
    view: DialogueState = {
        **base_state,
        **{k: v for k, v in accumulated_updates.items() if k in base_state},
    }
    return view
```

**Explicación:**
- Crea una vista del estado que combina el estado base con los updates acumulados
- No muta el estado original
- Permite que handlers vean el efecto de comandos previos

#### Paso 2: Refactorizar el loop de procesamiento de comandos

**Archivo(s) a modificar:** `src/soni/dm/nodes/understand.py`

**Buscar el bloque actual (líneas ~275-310):**

```python
# ANTES - Código actual con mutación
for cmd in commands:
    result = await registry.dispatch(cmd, state, runtime_ctx, expected_slot)

    # Acumular updates
    for key, value in result.updates.items():
        updates[key] = value

    # PROBLEMA: Mutación directa del estado
    if "flow_stack" in result.updates:
        state["flow_stack"] = result.updates["flow_stack"]
    if "flow_slots" in result.updates:
        state["flow_slots"] = result.updates["flow_slots"]
```

**Reemplazar con:**

```python
# DESPUÉS - Sin mutación, usando accumulated_updates
accumulated_updates: dict[str, Any] = {}

for cmd in commands:
    # Create view with accumulated updates for this handler
    state_view = create_state_view(state, accumulated_updates)

    result = await registry.dispatch(cmd, state_view, runtime_ctx, expected_slot)

    # Accumulate updates without mutating original state
    for key, value in result.updates.items():
        accumulated_updates[key] = value

    # Track response messages
    if result.response_messages:
        response_messages.extend(result.response_messages)

    if result.should_reset_flow_state:
        should_reset_flow_state = True

# Merge all accumulated updates into final return dict
updates.update(accumulated_updates)
```

**Explicación:**
- `accumulated_updates` acumula todos los cambios sin mutar el estado
- `state_view` proporciona una vista con updates aplicados para handlers que lo necesiten
- Al final, todo se retorna en `updates` que LangGraph procesará correctamente

#### Paso 3: Actualizar signature de dispatch si es necesario

**Archivo(s) a verificar:** `src/soni/dm/nodes/command_registry.py`

Verificar que los handlers funcionen correctamente con el state_view. Los handlers ya deberían funcionar porque reciben el estado como parámetro y retornan updates.

### TDD Cycle (MANDATORY for new features)

#### Red Phase: Write Failing Tests

**Test file:** `tests/unit/dm/test_understand_node_immutability.py`

**Failing tests to write FIRST:**

```python
import pytest
from unittest.mock import AsyncMock, MagicMock
from soni.core.types import DialogueState
from soni.core.state import create_empty_dialogue_state


class TestUnderstandNodeImmutability:
    """Tests to verify understand_node does not mutate input state."""

    @pytest.fixture
    def base_state(self) -> DialogueState:
        """Create a base state for testing."""
        state = create_empty_dialogue_state()
        state["flow_stack"] = [{"flow_id": "original", "flow_name": "test"}]
        state["flow_slots"] = {"original": {"slot1": "value1"}}
        return state

    @pytest.mark.asyncio
    async def test_understand_node_does_not_mutate_flow_stack(
        self, base_state: DialogueState
    ):
        """Test that understand_node does not mutate the input flow_stack."""
        # Arrange
        original_stack = list(base_state["flow_stack"])  # Copy for comparison

        # Act - Process message that would normally modify stack
        # (Mock setup would go here)

        # Assert - Original state should be unchanged
        assert base_state["flow_stack"] == original_stack, \
            "understand_node mutated flow_stack directly!"

    @pytest.mark.asyncio
    async def test_understand_node_does_not_mutate_flow_slots(
        self, base_state: DialogueState
    ):
        """Test that understand_node does not mutate the input flow_slots."""
        # Arrange
        original_slots = dict(base_state["flow_slots"])  # Copy for comparison

        # Act - Process message that would normally modify slots
        # (Mock setup would go here)

        # Assert - Original state should be unchanged
        assert base_state["flow_slots"] == original_slots, \
            "understand_node mutated flow_slots directly!"

    @pytest.mark.asyncio
    async def test_subsequent_handlers_see_accumulated_updates(
        self, base_state: DialogueState
    ):
        """Test that handlers in sequence can see previous updates via state_view."""
        # Arrange
        # First handler adds a slot, second handler should see it

        # Act
        # Process two commands in sequence

        # Assert
        # Second handler received state_view with first handler's updates
        pass  # Will fail until implemented


class TestCreateStateView:
    """Tests for the create_state_view helper function."""

    def test_state_view_includes_base_state(self):
        """Test that state_view contains all base state fields."""
        base = create_empty_dialogue_state()
        base["user_message"] = "hello"

        view = create_state_view(base, {})

        assert view["user_message"] == "hello"

    def test_state_view_overlays_updates(self):
        """Test that accumulated updates are applied to view."""
        base = create_empty_dialogue_state()
        base["flow_stack"] = [{"flow_id": "old"}]

        updates = {"flow_stack": [{"flow_id": "new"}]}
        view = create_state_view(base, updates)

        assert view["flow_stack"] == [{"flow_id": "new"}]
        assert base["flow_stack"] == [{"flow_id": "old"}]  # Original unchanged

    def test_state_view_does_not_modify_base(self):
        """Test that creating a view does not modify base state."""
        base = create_empty_dialogue_state()
        original_id = id(base["flow_stack"])

        view = create_state_view(base, {"flow_stack": []})

        assert id(base["flow_stack"]) == original_id
```

**Verify tests fail:**
```bash
uv run pytest tests/unit/dm/test_understand_node_immutability.py -v
# Expected: FAILED (feature not implemented yet)
```

**Commit:**
```bash
git add tests/
git commit -m "test: add failing tests for understand_node immutability"
```

#### Green Phase: Make Tests Pass

**Implement minimal code to pass tests.**

See "Implementación Detallada" section for implementation steps.

**Verify tests pass:**
```bash
uv run pytest tests/unit/dm/test_understand_node_immutability.py -v
# Expected: PASSED
```

**Commit:**
```bash
git add src/ tests/
git commit -m "fix: eliminate direct state mutation in understand_node

- Add create_state_view() helper for immutable state views
- Refactor command processing loop to accumulate updates
- Handlers now receive state_view with accumulated changes
- Original state is never mutated

Fixes critical SOLID violation in understand_node"
```

#### Refactor Phase: Improve Design

- Add comprehensive docstrings explaining the immutability pattern
- Consider extracting command processing loop to separate function
- Ensure type hints are complete
- Tests must still pass!

**Commit:**
```bash
git add src/
git commit -m "refactor: improve understand_node immutability implementation"
```

### Criterios de Éxito

- [ ] `understand_node` no muta el estado de entrada en ningún punto
- [ ] Handlers subsecuentes pueden ver updates de handlers previos via state_view
- [ ] Todos los tests existentes siguen pasando
- [ ] Nuevos tests de inmutabilidad pasan
- [ ] Linting pasa sin errores (`uv run ruff check src/soni/dm/nodes/understand.py`)
- [ ] Type checking pasa sin errores (`uv run mypy src/soni/dm/nodes/understand.py`)

### Validación Manual

**Comandos para validar:**

```bash
# Ejecutar tests específicos
uv run pytest tests/unit/dm/test_understand_node_immutability.py -v

# Ejecutar tests de integración que usan understand_node
uv run pytest tests/integration/ -k "understand" -v

# Verificar que no hay mutaciones con un test de chat
uv run soni chat --config examples/banking/soni.yaml
# Probar: "I want to transfer money" seguido de "to savings account"
```

**Resultado esperado:**
- Todos los tests pasan
- El flujo de conversación funciona igual que antes
- No hay errores de tipo o linting

### Referencias

- `src/soni/dm/nodes/understand.py` - Código a modificar
- `src/soni/flow/manager.py` - Ejemplo del patrón FlowDelta correcto
- `CLAUDE.md` - Principios de diseño del sistema
- LangGraph StateGraph documentation

### Notas Adicionales

**Edge Cases a considerar:**
- Comandos que fallan a mitad del procesamiento
- Múltiples comandos que modifican el mismo slot
- Comandos que dependen del estado modificado por comandos anteriores

**Impacto:**
Esta corrección es fundamental porque el patrón inmutable es usado en todo el sistema. Una vez corregido, facilitará el debugging y prevendrá una clase completa de bugs relacionados con estado compartido.
