## Task: 002 - Create Dedicated Correction/Modification Handlers

**ID de tarea:** 002
**Hito:** 10
**Dependencias:** Puede hacerse en paralelo con 001, pero se recomienda después
**Duración estimada:** 6-8 horas

### Objetivo

Crear nodos dedicados `handle_correction_node` y `handle_modification_node` según el diseño, y actualizar el routing para que las correcciones y modificaciones se enruten a estos nodos en lugar de `validate_slot`.

### Contexto

**Problema actual:**
- Correcciones y modificaciones se enrutan a `validate_slot` (igual que `slot_value`)
- No hay nodos dedicados `handle_correction` y `handle_modification`
- El diseño especifica que deben existir estos nodos separados

**Comportamiento esperado (según diseño):**
- Correcciones enrutadas a `handle_correction_node`
- Modificaciones enrutadas a `handle_modification_node`
- Estos nodos manejan lógica específica de correcciones/modificaciones

**Referencias:**
- Diseño: `docs/design/05-message-flow.md` (líneas 282-285)
- Inconsistencias: `docs/analysis/DESIGN_IMPLEMENTATION_INCONSISTENCIES.md` - Inconsistencia #1
- Backlog: `docs/analysis/BACKLOG_DESIGN_COMPLIANCE.md` (Fix #2)

### Entregables

- [ ] Nodo `handle_correction.py` creado e implementado
- [ ] Nodo `handle_modification.py` creado e implementado
- [ ] Routing actualizado para enrutar a estos nodos
- [ ] Graph builder actualizado para incluir estos nodos
- [ ] Node factory registry actualizado
- [ ] Tests de routing pasan

### Implementación Detallada

#### Paso 1: Crear handle_correction_node

**Archivo(s) a crear:** `src/soni/dm/nodes/handle_correction.py`

**Código específico:**

```python
"""Handle correction node for slot corrections."""

import logging
from typing import Any

from soni.core.types import DialogueState

logger = logging.getLogger(__name__)


async def handle_correction_node(
    state: DialogueState,
    runtime: Any,  # Runtime[RuntimeContext] - using Any to avoid import issues
) -> dict:
    """
    Handle slot correction.

    When user corrects a previously provided slot value:
    1. Extract slot and new value from NLU result
    2. Update slot in state
    3. Set state variables (_correction_slot, _correction_value)
    4. Return to the step where user was (not advance)

    Args:
        state: Current dialogue state
        runtime: Runtime context with dependencies

    Returns:
        Partial state updates
    """
    nlu_result = state.get("nlu_result", {})

    if not nlu_result:
        logger.warning("No NLU result in state for handle_correction_node")
        return {"conversation_state": "error"}

    slots = nlu_result.get("slots", [])
    if not slots:
        logger.warning("No slots in NLU result for correction")
        return {"conversation_state": "error"}

    # Get first slot (corrections typically have one slot)
    slot = slots[0]

    # Extract slot name and value
    if hasattr(slot, "name"):
        slot_name = slot.name
        raw_value = slot.value
    elif isinstance(slot, dict):
        slot_name = slot.get("name")
        raw_value = slot.get("value")
    else:
        logger.error(f"Unknown slot format: {type(slot)}")
        return {"conversation_state": "error"}

    # Normalize value
    normalizer = runtime.context["normalizer"]
    try:
        normalized_value = await normalizer.normalize_slot(slot_name, raw_value)
    except Exception as e:
        logger.error(f"Normalization failed for correction: {e}")
        return {"conversation_state": "error"}

    # Update slot in state
    flow_manager = runtime.context["flow_manager"]
    active_ctx = flow_manager.get_active_context(state)

    if not active_ctx:
        return {"conversation_state": "error"}

    flow_id = active_ctx["flow_id"]
    flow_slots = state.get("flow_slots", {}).copy()
    if flow_id not in flow_slots:
        flow_slots[flow_id] = {}

    # Get previous value for state variable
    previous_value = flow_slots[flow_id].get(slot_name)

    # Update slot
    flow_slots[flow_id][slot_name] = normalized_value

    # Get previous step to return to
    previous_step = active_ctx.get("current_step")
    previous_state = state.get("conversation_state")

    # Set state variables
    metadata = state.get("metadata", {}).copy()
    metadata["_correction_slot"] = slot_name
    metadata["_correction_value"] = normalized_value

    # Determine conversation_state based on previous step
    step_manager = runtime.context["step_manager"]
    if previous_step:
        # Get step config to determine state
        temp_state = {**state, "current_step": previous_step}
        step_config = step_manager.get_current_step_config(temp_state, runtime.context)

        if step_config:
            step_type_to_state = {
                "action": "ready_for_action",
                "collect": "waiting_for_slot",
                "confirm": "ready_for_confirmation",
                "say": "generating_response",
            }
            new_state = step_type_to_state.get(step_config.type, previous_state)
        else:
            new_state = previous_state
    else:
        new_state = previous_state

    return {
        "flow_slots": flow_slots,
        "conversation_state": new_state,
        "current_step": previous_step,
        "flow_stack": state["flow_stack"],
        "metadata": metadata,
    }
```

#### Paso 2: Crear handle_modification_node

**Archivo(s) a crear:** `src/soni/dm/nodes/handle_modification.py`

**Código específico:**

```python
"""Handle modification node for slot modifications."""

import logging
from typing import Any

from soni.core.types import DialogueState

logger = logging.getLogger(__name__)


async def handle_modification_node(
    state: DialogueState,
    runtime: Any,  # Runtime[RuntimeContext] - using Any to avoid import issues
) -> dict:
    """
    Handle slot modification.

    Similar to correction but for intentional modifications.
    Sets _modification_slot and _modification_value instead.

    Args:
        state: Current dialogue state
        runtime: Runtime context with dependencies

    Returns:
        Partial state updates
    """
    # Similar structure to handle_correction_node
    # But sets _modification_slot and _modification_value
    # Implementation follows same pattern as correction
    ...
```

#### Paso 3: Actualizar routing

**Archivo(s) a modificar:** `src/soni/dm/routing.py`

**Código específico:**

```python
def route_after_understand(state: DialogueStateType) -> str:
    # ... código existente ...

    match message_type:
        case "slot_value":
            # ... código existente ...
        case "correction":
            # Route to dedicated correction handler
            return "handle_correction"
        case "modification":
            # Route to dedicated modification handler
            return "handle_modification"
        # ... resto del código ...
```

#### Paso 4: Actualizar graph builder

**Archivo(s) a modificar:** `src/soni/dm/builder.py`

**Explicación:**
- Agregar edges para `handle_correction` y `handle_modification`
- Conectar desde `understand` a estos nodos
- Conectar desde estos nodos a los siguientes pasos apropiados

#### Paso 5: Registrar en node factory

**Archivo(s) a modificar:** `src/soni/dm/node_factory_registry.py`

**Explicación:**
- Registrar factories para `handle_correction` y `handle_modification`
- Seguir el patrón de otros nodos existentes

### Tests Requeridos

**Archivo de tests:** `tests/integration/test_design_compliance_corrections.py`

**Tests específicos a crear:**

```python
@pytest.mark.integration
@pytest.mark.asyncio
async def test_correction_routes_to_handle_correction_node(runtime, skip_without_api_key):
    """Test that corrections route to handle_correction_node."""
    # Arrange: Create state with correction message_type
    # Act: Process message
    # Assert: Verify routing goes to handle_correction

@pytest.mark.integration
@pytest.mark.asyncio
async def test_modification_routes_to_handle_modification_node(runtime, skip_without_api_key):
    """Test that modifications route to handle_modification_node."""
    # Similar to above but for modification
```

### Criterios de Éxito

- [ ] Nodos `handle_correction` y `handle_modification` existen
- [ ] Routing enruta correcciones a `handle_correction`
- [ ] Routing enruta modificaciones a `handle_modification`
- [ ] Graph builder incluye estos nodos
- [ ] Tests de routing pasan
- [ ] No hay regresiones en tests existentes
- [ ] Linting pasa sin errores
- [ ] Type checking pasa sin errores

### Validación Manual

**Comandos para validar:**

```bash
# Verificar que los nodos existen
ls src/soni/dm/nodes/handle_correction.py
ls src/soni/dm/nodes/handle_modification.py

# Ejecutar tests de routing (si se crean)
uv run pytest tests/integration/test_design_compliance_corrections.py -v

# Verificar que el graph se construye correctamente
uv run pytest tests/integration/test_e2e.py::test_e2e_slot_correction -v
```

**Resultado esperado:**
- Los nodos existen y funcionan
- El routing lleva a los nodos correctos
- El sistema procesa correcciones/modificaciones correctamente

### Referencias

- Diseño: `docs/design/05-message-flow.md` (líneas 282-285)
- Análisis: `docs/analysis/DESIGN_IMPLEMENTATION_INCONSISTENCIES.md` (Inconsistencia #1)
- Backlog: `docs/analysis/BACKLOG_DESIGN_COMPLIANCE.md` (Fix #2)
- Código de referencia: `src/soni/dm/nodes/handle_confirmation.py` (patrón similar)
- Código de referencia: `src/soni/dm/nodes/validate_slot.py` (lógica similar)

### Notas Adicionales

- Esta tarea puede hacerse en paralelo con 001, pero se recomienda después para reutilizar la lógica de "volver al step"
- Los nodos deben seguir el mismo patrón que otros nodos existentes (async, TypedDict state, etc.)
- Considerar si `handle_correction` y `handle_modification` pueden compartir código común
- La lógica de "volver al step" puede extraerse a una función helper compartida
