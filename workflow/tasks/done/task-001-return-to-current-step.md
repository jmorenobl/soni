## Task: 001 - Implement "Return to Current Step" Logic for Corrections

**ID de tarea:** 001
**Hito:** 10
**Dependencias:** Ninguna
**Duración estimada:** 8-12 horas

### Objetivo

Implementar la lógica para que cuando ocurre una corrección o modificación, el sistema vuelva al step donde estaba el usuario, en lugar de avanzar al siguiente step. Esto es crítico para cumplir con el diseño especificado en `docs/design/10-dsl-specification/06-patterns.md`.

### Contexto

**Problema actual:**
Cuando un usuario corrige un slot, el sistema:
1. Actualiza el slot correctamente ✓
2. Verifica si el `current_step` está completo
3. Si está completo, **avanza al siguiente step** ✗ (INCORRECTO según diseño)

**Comportamiento esperado (según diseño):**
- Actualizar el slot ✓
- Rastrear el step donde estaba el usuario
- Volver a ese step (re-mostrar confirmación, continuar desde acción, etc.) ✓

**Referencias:**
- Diseño: `docs/design/10-dsl-specification/06-patterns.md` línea 71: "Both patterns are handled the same way: **update the slot, return to current step**."
- Inconsistencias: `docs/analysis/DESIGN_IMPLEMENTATION_INCONSISTENCIES.md` - Inconsistencia #2
- Tests: `tests/integration/test_design_compliance_corrections.py`

### Entregables

- [ ] Sistema rastrea el step donde estaba el usuario cuando ocurre corrección/modificación
- [ ] `validate_slot_node` vuelve al step rastreado en lugar de avanzar
- [ ] Correcciones durante confirmación vuelven a confirmación
- [ ] Correcciones después de todos los slots llenos vuelven al step actual
- [ ] Todos los tests relacionados pasan

### Implementación Detallada

#### Paso 1: Rastrear el step actual antes de procesar corrección

**Archivo(s) a modificar:** `src/soni/dm/nodes/validate_slot.py`

**Explicación:**
- Antes de actualizar el slot, capturar el `current_step` y `conversation_state` actual
- Guardar esta información en el estado o en variables temporales
- Esto permite volver al step correcto después de actualizar el slot

**Código específico:**

```python
async def validate_slot_node(
    state: DialogueState,
    runtime: Any,
) -> dict:
    # ... código existente para obtener slot ...

    # Paso 1: Capturar step actual ANTES de actualizar
    active_ctx = flow_manager.get_active_context(state)
    if active_ctx:
        previous_step = active_ctx.get("current_step")
        previous_conversation_state = state.get("conversation_state")

        # Guardar en metadata para referencia
        metadata = state.get("metadata", {})
        metadata["_previous_step_before_correction"] = previous_step
        metadata["_previous_state_before_correction"] = previous_conversation_state
```

#### Paso 2: Detectar si es corrección/modificación

**Archivo(s) a modificar:** `src/soni/dm/nodes/validate_slot.py`

**Explicación:**
- Verificar el `message_type` del NLU result
- Si es `correction` o `modification`, aplicar lógica especial de "volver al step"

**Código específico:**

```python
    nlu_result = state.get("nlu_result", {})
    message_type = nlu_result.get("message_type", "")
    is_correction_or_modification = message_type in ("correction", "modification")
```

#### Paso 3: Implementar lógica de "volver al step"

**Archivo(s) a modificar:** `src/soni/dm/nodes/validate_slot.py`

**Explicación:**
- Después de actualizar el slot, en lugar de verificar si el step está completo y avanzar:
  - Si es corrección/modificación, usar el step guardado anteriormente
  - Determinar el `conversation_state` apropiado basado en el step anterior
  - Retornar actualizaciones que restablezcan el step anterior

**Código específico:**

```python
    # Actualizar slot (código existente)
    flow_slots[flow_id][slot_name] = normalized_value
    state["flow_slots"] = flow_slots

    # Si es corrección/modificación, volver al step anterior
    if is_correction_or_modification and previous_step:
        # Determinar conversation_state basado en el step anterior
        previous_step_config = step_manager.get_current_step_config(
            {**state, "current_step": previous_step}, runtime.context
        )

        if previous_step_config:
            step_type_to_state = {
                "action": "ready_for_action",
                "collect": "waiting_for_slot",
                "confirm": "ready_for_confirmation",
                "say": "generating_response",
            }
            new_state = step_type_to_state.get(
                previous_step_config.type, previous_conversation_state
            )

            # Restablecer al step anterior
            active_ctx["current_step"] = previous_step

            return {
                "flow_slots": flow_slots,
                "conversation_state": new_state,
                "current_step": previous_step,
                "flow_stack": state["flow_stack"],
            }

    # Si no es corrección/modificación, continuar con lógica normal
    # ... resto del código existente ...
```

#### Paso 4: Manejar caso especial de confirmación

**Archivo(s) a modificar:** `src/soni/dm/nodes/validate_slot.py`

**Explicación:**
- Si el step anterior era de confirmación, asegurar que se vuelva a mostrar la confirmación
- Esto puede requerir coordinación con `handle_confirmation_node`

**Código específico:**

```python
    # Si volvemos a un step de confirmación, asegurar que se re-muestre
    if previous_step_config and previous_step_config.type == "confirm":
        # El routing debería llevar a handle_confirmation que re-muestra
        # Pero podemos asegurar el estado aquí
        return {
            "flow_slots": flow_slots,
            "conversation_state": "ready_for_confirmation",
            "current_step": previous_step,
            "flow_stack": state["flow_stack"],
        }
```

### Tests Requeridos

**Archivo de tests:** `tests/integration/test_design_compliance_corrections.py`

**Tests específicos que deben pasar:**

```python
# Estos tests ya existen y deben pasar después de esta implementación:
- test_correction_during_confirmation_returns_to_confirmation
- test_modification_during_confirmation_returns_to_confirmation
- test_correction_returns_to_current_step_not_next
```

**Test adicional recomendado:**

```python
@pytest.mark.integration
@pytest.mark.asyncio
async def test_correction_during_action_returns_to_action(runtime, skip_without_api_key):
    """Test that corrections during action step return to action, not advance."""
    # Arrange: Llegar a un step de acción
    # Act: Corregir un slot
    # Assert: Sistema vuelve a acción, no avanza
```

### Criterios de Éxito

- [ ] `test_correction_during_confirmation_returns_to_confirmation` pasa
- [ ] `test_modification_during_confirmation_returns_to_confirmation` pasa
- [ ] `test_correction_returns_to_current_step_not_next` pasa
- [ ] `test_e2e_slot_correction` pasa
- [ ] No hay regresiones en tests existentes
- [ ] Linting pasa sin errores
- [ ] Type checking pasa sin errores

### Validación Manual

**Comandos para validar:**

```bash
# Ejecutar tests de cumplimiento del diseño
uv run pytest tests/integration/test_design_compliance_corrections.py::test_correction_returns_to_current_step_not_next -v

# Ejecutar test E2E de corrección
uv run pytest tests/integration/test_e2e.py::test_e2e_slot_correction -v

# Ejecutar todos los tests para verificar regresiones
uv run pytest tests/integration/ -v
```

**Resultado esperado:**
- Los tests de corrección pasan
- El sistema vuelve al step anterior después de corregir
- No se avanza incorrectamente al siguiente step

### Referencias

- Diseño: `docs/design/10-dsl-specification/06-patterns.md` (líneas 51-71)
- Análisis: `docs/analysis/DESIGN_IMPLEMENTATION_INCONSISTENCIES.md` (Inconsistencia #2)
- Backlog: `docs/analysis/BACKLOG_DESIGN_COMPLIANCE.md` (Fix #1)
- Código actual: `src/soni/dm/nodes/validate_slot.py` (líneas 98-134)
- Tests: `tests/integration/test_design_compliance_corrections.py`

### Notas Adicionales

- Esta tarea es crítica y debe completarse antes de las tareas #003 y #002
- La lógica debe funcionar tanto para correcciones como modificaciones
- Considerar edge cases: ¿Qué pasa si el step anterior ya no existe? ¿Qué pasa si el flow cambió?
- Puede ser necesario actualizar el estado de `DialogueState` para incluir campos de tracking si no existen
