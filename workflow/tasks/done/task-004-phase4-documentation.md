## Task: 004 - Phase 4: Documentation Updates

**ID de tarea:** MULTI-SLOTS-004
**Hito:** 1 - Multiple Slots Processing (Solution 3)
**Dependencias:** MULTI-SLOTS-003 (Phase 3 debe estar completa)
**Duración estimada:** 1-2 horas

### Objetivo

Actualizar toda la documentación relacionada con el procesamiento de múltiples slots, incluyendo documentación de arquitectura, docstrings, y guías de desarrollo.

### Contexto

Después de implementar y validar la solución (Phases 1-3), necesitamos documentar:
1. Los nuevos componentes y funciones
2. El patrón de avance iterativo de pasos
3. Cómo manejar múltiples slots en nuevos desarrollos
4. Ejemplos de uso

**Referencias:**
- `docs/design/03-components.md` - Documentación de componentes
- `docs/design/07-flow-management.md` - Documentación de gestión de flujos
- `src/soni/flow/step_manager.py` - Nuevo método a documentar
- `src/soni/dm/nodes/validate_slot.py` - Nuevas funciones helper a documentar

### Entregables

- [ ] Actualización de `docs/design/03-components.md` con nuevos componentes
- [ ] Documentación de `advance_through_completed_steps` en diseño
- [ ] Docstrings completos en todas las funciones nuevas
- [ ] Documentación del patrón de avance iterativo
- [ ] Sección en guía de desarrollo sobre múltiples slots
- [ ] Ejemplos de uso en documentación

### Implementación Detallada

#### Paso 1: Actualizar Documentación de Arquitectura

**Archivo(s) a crear/modificar:** `docs/design/03-components.md`

**Contenido específico:**

Agregar sección sobre `FlowStepManager.advance_through_completed_steps`:

```markdown
### FlowStepManager.advance_through_completed_steps

**Propósito**: Avanzar iterativamente a través de todos los pasos completos hasta encontrar uno incompleto.

**Cuándo usar**:
- Después de guardar múltiples slots en un solo mensaje
- Cuando se necesita avanzar automáticamente a través de pasos completos
- En `validate_slot_node` después de procesar slots
- En `handle_intent_change_node` después de activar flujo con slots

**Ejemplo de uso**:
```python
# After saving multiple slots
updates = step_manager.advance_through_completed_steps(state, context)
state.update(updates)
```

**Comportamiento**:
1. Verifica si el paso actual está completo
2. Si está completo, avanza al siguiente paso
3. Repite hasta encontrar un paso incompleto o el flujo termina
4. Retorna actualizaciones de estado con `current_step`, `conversation_state`, etc.

**Límite de seguridad**: Máximo 20 iteraciones para prevenir loops infinitos
```

Agregar sección sobre funciones helper en `validate_slot_node`:

```markdown
### Helper Functions in validate_slot_node

#### _process_all_slots

Procesa y normaliza todos los slots de un resultado NLU. Maneja diferentes formatos (dict, SlotValue model, string).

#### _detect_correction_or_modification

Detecta si un mensaje es una corrección o modificación basándose en `message_type` y acciones de slots.

#### _handle_correction_flow

Maneja el flujo de corrección/modificación, restaurando el paso correcto y actualizando el estado.
```

#### Paso 2: Actualizar Documentación de Flow Management

**Archivo(s) a crear/modificar:** `docs/design/07-flow-management.md`

**Contenido específico:**

Agregar sección sobre "Procesamiento de Múltiples Slots":

```markdown
## Procesamiento de Múltiples Slots

### Patrón de Avance Iterativo

Cuando el usuario proporciona múltiples slots en un solo mensaje, el sistema debe:

1. **Procesar todos los slots**: Usar `_process_all_slots` para normalizar y guardar todos los slots
2. **Avanzar iterativamente**: Usar `advance_through_completed_steps` para avanzar a través de todos los pasos completos
3. **Detener en paso incompleto**: El sistema se detiene en el primer paso que requiere más información

### Ejemplo de Flujo

```
Usuario: "I want to fly from New York to Los Angeles"

1. NLU extrae: [origin="New York", destination="Los Angeles"]
2. _process_all_slots guarda ambos slots
3. advance_through_completed_steps:
   - Verifica collect_origin → completo → avanza a collect_destination
   - Verifica collect_destination → completo → avanza a collect_date
   - Verifica collect_date → incompleto → DETIENE
4. Estado final: current_step="collect_date", waiting_for_slot="departure_date"
```

### Integración con Nodos

**validate_slot_node**:
- Usa `_process_all_slots` para procesar todos los slots
- Usa `advance_through_completed_steps` para avanzar pasos
- Maneja correcciones con `_handle_correction_flow`

**handle_intent_change_node**:
- Guarda slots extraídos del NLU
- Usa `advance_through_completed_steps` para avanzar pasos después de activar flujo
```

#### Paso 3: Agregar Docstrings Completos

**Archivo(s) a crear/modificar:** `src/soni/flow/step_manager.py`

**Docstring para `advance_through_completed_steps`:**

Ya está incluido en Phase 1, pero verificar que sea completo con:
- Descripción clara del propósito
- Args documentados
- Returns documentados
- Ejemplo de uso
- Notas sobre mutación de estado
- Notas sobre límite de seguridad

**Archivo(s) a crear/modificar:** `src/soni/dm/nodes/validate_slot.py`

**Docstrings para funciones helper:**

```python
async def _process_all_slots(
    slots: list,
    state: DialogueState,
    active_ctx: FlowContext,
    normalizer: INormalizer,
) -> dict[str, dict[str, Any]]:
    """Process and normalize all slots from NLU result.

    This function handles multiple slot formats (dict, SlotValue model, string)
    and normalizes all slot values before saving them to state.

    Args:
        slots: List of slots from NLU result. Can contain:
            - dict: {"name": "origin", "value": "New York"}
            - SlotValue: SlotValue(name="origin", value="New York")
            - str: Raw string value (uses waiting_for_slot as name)
        state: Current dialogue state
        active_ctx: Active flow context containing flow_id
        normalizer: Slot normalizer for value normalization

    Returns:
        Dictionary of flow_slots structure:
        {
            flow_id: {
                slot_name: normalized_value,
                ...
            }
        }

    Example:
        >>> slots = [
        ...     {"name": "origin", "value": "New York"},
        ...     {"name": "destination", "value": "Los Angeles"}
        ... ]
        >>> flow_slots = await _process_all_slots(slots, state, active_ctx, normalizer)
        >>> assert flow_slots[flow_id]["origin"] == "New York"
        >>> assert flow_slots[flow_id]["destination"] == "Los Angeles"
    """
```

#### Paso 4: Actualizar Guía de Desarrollo

**Archivo(s) a crear/modificar:** `docs/implementation/` o crear nuevo archivo

**Contenido específico:**

Crear `docs/implementation/handling-multiple-slots.md`:

```markdown
# Handling Multiple Slots in One Message

## Overview

When users provide multiple slots in a single message (e.g., "I want to fly from New York to Los Angeles"), the system needs to:
1. Extract all slots from NLU
2. Process and normalize all slots
3. Advance iteratively through completed steps
4. Stop at the first incomplete step

## Implementation Pattern

### In validate_slot_node

```python
# Process all slots
flow_slots = await _process_all_slots(slots, state, active_ctx, normalizer)
state["flow_slots"] = flow_slots

# Advance through completed steps
updates = step_manager.advance_through_completed_steps(state, runtime.context)
updates["flow_slots"] = flow_slots

return updates
```

### In handle_intent_change_node

```python
# Save slots from NLU
extracted_slots = _extract_slots_from_nlu(slots_from_nlu)
if extracted_slots:
    current_slots = get_all_slots(state)
    current_slots.update(extracted_slots)
    set_all_slots(state, current_slots)

# Advance through completed steps
updates = step_manager.advance_through_completed_steps(state, runtime.context)
updates["flow_stack"] = state["flow_stack"]
updates["flow_slots"] = state["flow_slots"]

return updates
```

## When to Use advance_through_completed_steps

Use this method when:
- Multiple slots are provided in one message
- You need to advance through multiple completed steps automatically
- After saving slots that might complete multiple steps

Do NOT use when:
- Processing a single slot (use normal step advancement)
- Handling corrections (use _handle_correction_flow)
- Flow is already at the correct step

## Testing

Always test:
1. Multiple slots in one message
2. All slots at once
3. Mix of new slots and corrections
4. Regression: Sequential flow still works
```

### Tests Requeridos

**No se requieren tests nuevos** - esta fase es solo documentación.

**Validación:**
- Revisar que todos los docstrings estén completos
- Verificar que los ejemplos en documentación sean correctos
- Asegurar que la documentación sea clara y útil

### Criterios de Éxito

- [ ] `docs/design/03-components.md` actualizado con nuevos componentes
- [ ] `docs/design/07-flow-management.md` actualizado con patrón de múltiples slots
- [ ] Todos los docstrings completos y con ejemplos
- [ ] Guía de desarrollo creada o actualizada
- [ ] Ejemplos de uso incluidos en documentación
- [ ] Documentación es clara y fácil de seguir

### Validación Manual

**Comandos para validar:**

```bash
# Verificar que los docstrings se generan correctamente
uv run python -c "from soni.flow.step_manager import FlowStepManager; help(FlowStepManager.advance_through_completed_steps)"

# Verificar que la documentación se puede generar (si usas mkdocs)
uv run mkdocs build

# Revisar manualmente los archivos de documentación
cat docs/design/03-components.md
cat docs/design/07-flow-management.md
```

**Resultado esperado:**
- Docstrings son legibles y completos
- Documentación es clara y útil
- Ejemplos funcionan correctamente
- No hay errores de sintaxis en markdown

### Referencias

- `docs/design/03-components.md` - Documentación de componentes
- `docs/design/07-flow-management.md` - Documentación de gestión de flujos
- `docs/analysis/SOLUCION_MULTIPLES_SLOTS.md` - Solución implementada
- `src/soni/flow/step_manager.py` - Código a documentar
- `src/soni/dm/nodes/validate_slot.py` - Código a documentar

### Notas Adicionales

- **Claridad**: La documentación debe ser clara para nuevos desarrolladores
- **Ejemplos**: Incluir ejemplos prácticos de uso
- **Consistencia**: Mantener el mismo estilo que el resto de la documentación
- **Completitud**: Asegurar que todos los aspectos importantes estén documentados
