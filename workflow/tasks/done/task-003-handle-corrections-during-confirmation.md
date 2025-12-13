## Task: 003 - Handle Corrections During Confirmation Automatically

**ID de tarea:** 003
**Hito:** 10
**Dependencias:** 001 (Return to Current Step)
**Duración estimada:** 6-8 horas

### Objetivo

Modificar `handle_confirmation_node` para que detecte automáticamente correcciones y modificaciones durante la confirmación, actualice los slots, y re-muestre la confirmación con los valores actualizados, sin requerir configuración DSL.

### Contexto

**Problema actual:**
- `handle_confirmation_node` solo maneja respuestas sí/no
- No detecta correcciones/modificaciones durante confirmación
- Usuarios no pueden corregir durante confirmación como está diseñado

**Comportamiento esperado (según diseño):**
- `handle_confirmation_node` detecta correcciones/modificaciones en NLU result
- Actualiza slot automáticamente
- Re-muestra confirmación con valores actualizados
- Espera nueva confirmación
- Esto debe ser automático (sin configuración DSL)

**Referencias:**
- Diseño: `docs/design/10-dsl-specification/06-patterns.md` (líneas 162-173, 195-197)
- Inconsistencias: `docs/analysis/DESIGN_IMPLEMENTATION_INCONSISTENCIES.md` - Inconsistencia #3
- Backlog: `docs/analysis/BACKLOG_DESIGN_COMPLIANCE.md` (Fix #3)

### Entregables

- [ ] `handle_confirmation_node` detecta correcciones en NLU result
- [ ] `handle_confirmation_node` detecta modificaciones en NLU result
- [ ] Slots se actualizan automáticamente cuando se detecta corrección/modificación
- [ ] Confirmación se re-muestra con valores actualizados
- [ ] Sistema vuelve a estado "confirming" después de corrección
- [ ] No se requiere configuración DSL
- [ ] Todos los tests relacionados pasan

### Implementación Detallada

#### Paso 1: Detectar correcciones/modificaciones en handle_confirmation

**Archivo(s) a modificar:** `src/soni/dm/nodes/handle_confirmation.py`

**Código específico:**

```python
async def handle_confirmation_node(
    state: DialogueState,
    runtime: Any,
) -> dict:
    """
    Handle confirmation response, including automatic correction detection.
    """
    nlu_result = state.get("nlu_result", {})

    if not nlu_result:
        return {"conversation_state": "error"}

    message_type = nlu_result.get("message_type", "")

    # Check if user is correcting/modifying during confirmation
    if message_type in ("correction", "modification"):
        return await _handle_correction_during_confirmation(
            state, runtime, nlu_result, message_type
        )

    # Continue with normal yes/no confirmation handling
    # ... código existente ...
```

#### Paso 2: Implementar lógica de corrección durante confirmación

**Archivo(s) a modificar:** `src/soni/dm/nodes/handle_confirmation.py`

**Código específico:**

```python
async def _handle_correction_during_confirmation(
    state: DialogueState,
    runtime: Any,
    nlu_result: dict,
    message_type: str,
) -> dict:
    """
    Handle correction/modification during confirmation step.

    This happens automatically - no DSL configuration needed.
    """
    slots = nlu_result.get("slots", [])
    if not slots:
        logger.warning("Correction/modification detected but no slots in NLU result")
        return {"conversation_state": "confirming"}

    # Get slot to correct/modify
    slot = slots[0]
    if hasattr(slot, "name"):
        slot_name = slot.name
        raw_value = slot.value
    elif isinstance(slot, dict):
        slot_name = slot.get("name")
        raw_value = slot.get("value")
    else:
        return {"conversation_state": "confirming"}

    # Normalize value
    normalizer = runtime.context["normalizer"]
    try:
        normalized_value = await normalizer.normalize_slot(slot_name, raw_value)
    except Exception as e:
        logger.error(f"Normalization failed during confirmation: {e}")
        return {"conversation_state": "confirming"}

    # Update slot in state
    flow_manager = runtime.context["flow_manager"]
    active_ctx = flow_manager.get_active_context(state)

    if not active_ctx:
        return {"conversation_state": "error"}

    flow_id = active_ctx["flow_id"]
    flow_slots = state.get("flow_slots", {}).copy()
    if flow_id not in flow_slots:
        flow_slots[flow_id] = {}

    flow_slots[flow_id][slot_name] = normalized_value

    # Set state variables
    metadata = state.get("metadata", {}).copy()
    if message_type == "correction":
        metadata["_correction_slot"] = slot_name
        metadata["_correction_value"] = normalized_value
    elif message_type == "modification":
        metadata["_modification_slot"] = slot_name
        metadata["_modification_value"] = normalized_value

    # Re-generate confirmation message with updated values
    step_manager = runtime.context["step_manager"]
    current_step_config = step_manager.get_current_step_config(state, runtime.context)

    confirmation_message = _generate_confirmation_message(
        flow_slots[flow_id], current_step_config, runtime.context
    )

    return {
        "flow_slots": flow_slots,
        "conversation_state": "confirming",  # Return to confirming state
        "last_response": confirmation_message,
        "metadata": metadata,
    }
```

#### Paso 3: Generar mensaje de confirmación actualizado

**Archivo(s) a modificar:** `src/soni/dm/nodes/handle_confirmation.py`

**Código específico:**

```python
def _generate_confirmation_message(
    slots: dict[str, Any],
    step_config: StepConfig | None,
    context: RuntimeContext,
) -> str:
    """
    Generate confirmation message with current slot values.

    Uses step_config.message template if available, otherwise generates default.
    """
    if step_config and step_config.message:
        # Use template from step config
        message = step_config.message
        # Interpolate slot values
        for slot_name, value in slots.items():
            message = message.replace(f"{{{slot_name}}}", str(value))
        return message

    # Default confirmation message
    message = "Let me confirm:\n"
    config = context["config"]
    for slot_name, value in slots.items():
        slot_config = config.slots.get(slot_name, {})
        display_name = slot_config.get("display_name", slot_name)
        message += f"- {display_name}: {value}\n"
    message += "\nIs this correct?"

    return message
```

### Tests Requeridos

**Archivo de tests:** `tests/integration/test_design_compliance_corrections.py`

**Tests específicos que deben pasar:**

```python
# Estos tests ya existen y deben pasar:
- test_correction_automatic_during_confirmation
- test_correction_during_confirmation_returns_to_confirmation
- test_modification_during_confirmation_returns_to_confirmation
```

### Criterios de Éxito

- [ ] `test_correction_automatic_during_confirmation` pasa
- [ ] `test_correction_during_confirmation_returns_to_confirmation` pasa
- [ ] `test_modification_during_confirmation_returns_to_confirmation` pasa
- [ ] Correcciones durante confirmación se detectan automáticamente
- [ ] Slots se actualizan automáticamente
- [ ] Confirmación se re-muestra con valores actualizados
- [ ] No se requiere configuración DSL
- [ ] No hay regresiones en tests existentes
- [ ] Linting pasa sin errores
- [ ] Type checking pasa sin errores

### Validación Manual

**Comandos para validar:**

```bash
# Ejecutar tests de corrección durante confirmación
uv run pytest tests/integration/test_design_compliance_corrections.py::test_correction_automatic_during_confirmation -v

# Ejecutar todos los tests de cumplimiento
uv run pytest tests/integration/test_design_compliance_corrections.py -v
```

**Resultado esperado:**
- Los tests pasan
- El sistema detecta correcciones durante confirmación
- La confirmación se re-muestra automáticamente con valores actualizados

### Referencias

- Diseño: `docs/design/10-dsl-specification/06-patterns.md` (líneas 162-173, 195-197)
- Análisis: `docs/analysis/DESIGN_IMPLEMENTATION_INCONSISTENCIES.md` (Inconsistencia #3)
- Backlog: `docs/analysis/BACKLOG_DESIGN_COMPLIANCE.md` (Fix #3)
- Código actual: `src/soni/dm/nodes/handle_confirmation.py`
- Tests: `tests/integration/test_design_compliance_corrections.py`

### Notas Adicionales

- Esta tarea depende de la tarea 001 (Return to Current Step) para funcionar correctamente
- La detección debe ser automática - no requiere configuración DSL
- Considerar usar templates de respuesta `correction_acknowledged` si están disponibles
- El mensaje de confirmación debe mostrar todos los slots, no solo el corregido
