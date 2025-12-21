# Análisis Completo de Escenarios y Gestión de Estado

## Objetivo

Analizar todos los escenarios posibles en las conversaciones y cómo se gestionan con el estado actual del sistema, identificando problemas y proponiendo soluciones.

## Escenarios Definidos

### Escenario 1: Simple - Flujo Completo Secuencial
**Descripción**: El usuario proporciona los slots uno por uno en secuencia.

**Ejemplo**:
```
Turn 1: "I want to book a flight"
Turn 2: "Madrid" (origin)
Turn 3: "Barcelona" (destination)
Turn 4: "Tomorrow" (departure_date)
```

**Estado Esperado**:
- Turn 1: `flow_stack=[book_flight]`, `current_step=collect_origin`, `waiting_for_slot=origin`
- Turn 2: `flow_stack=[book_flight]`, `current_step=collect_destination`, `waiting_for_slot=destination`, `slots={origin: "Madrid"}`
- Turn 3: `flow_stack=[book_flight]`, `current_step=collect_date`, `waiting_for_slot=departure_date`, `slots={origin: "Madrid", destination: "Barcelona"}`
- Turn 4: `flow_stack=[book_flight]`, `current_step=search_flights`, `conversation_state=ready_for_action`, `slots={origin, destination, departure_date}`

**Estado Actual**: ✅ Funciona correctamente

---

### Escenario 2: Medium - Múltiples Slots en un Mensaje
**Descripción**: El usuario proporciona múltiples slots en un solo mensaje.

**Ejemplo**:
```
Turn 1: "I want to fly from New York to Los Angeles"
Turn 2: "Next Friday"
```

**Estado Esperado**:
- Turn 1:
  - `flow_stack=[book_flight]`
  - `current_step=collect_date` (avanzó desde collect_origin y collect_destination)
  - `waiting_for_slot=departure_date`
  - `slots={origin: "New York", destination: "Los Angeles"}`
- Turn 2:
  - `current_step=search_flights`
  - `conversation_state=ready_for_action`
  - `slots={origin, destination, departure_date}`

**Estado Actual**: ❌ **PROBLEMA IDENTIFICADO**

**Problema Observado**:
```
Turn 1: "I want to fly from New York to Los Angeles"
  - NLU extrae: origin="New York", destination="Los Angeles" ✅
  - Slots guardados: {origin: "New York", destination: "Los Angeles"} ✅
  - PERO: waiting_for_slot="destination" ❌ (debería ser "departure_date")
  - current_prompted_slot="destination" ❌
  - current_step=None ❌ (debería avanzar a collect_date)
  - conversation_state="idle" ❌ (debería ser "waiting_for_slot")
  - Respuesta: "How can I help you?" ❌ (debería preguntar por departure_date)
```

**Análisis del Problema**:

1. **`validate_slot_node` solo procesa el primer slot**:
   ```python
   # En validate_slot.py línea 227
   slot = slots[0]  # ❌ Solo procesa el primer slot
   ```
   Cuando el NLU extrae múltiples slots (`[origin, destination]`), solo se procesa el primero.

2. **No hay lógica para procesar múltiples slots secuencialmente**:
   - El sistema debería:
     1. Procesar el primer slot (origin)
     2. Verificar si el paso está completo
     3. Avanzar al siguiente paso
     4. Procesar el segundo slot (destination)
     5. Verificar si el paso está completo
     6. Avanzar al siguiente paso
     7. Continuar hasta procesar todos los slots

3. **`handle_intent_change` guarda los slots pero no avanza los pasos**:
   ```python
   # En handle_intent_change.py líneas 136-143
   if extracted_slots:
       current_slots = get_all_slots(state)
       current_slots.update(extracted_slots)
       set_all_slots(state, current_slots)
       # ✅ Guarda los slots
       # ❌ PERO no avanza los pasos
   ```
   Los slots se guardan, pero `current_step` no se actualiza para reflejar que los pasos `collect_origin` y `collect_destination` están completos.

4. **`collect_next_slot` se ejecuta sin verificar si hay slots pendientes de procesar**:
   - Cuando se guardan múltiples slots en `handle_intent_change`, el sistema debería:
     1. Verificar qué pasos están completos
     2. Avanzar automáticamente a través de los pasos completos
     3. Solo entonces preguntar por el siguiente slot faltante

---

### Escenario 3: Medium - Corrección de Slot
**Descripción**: El usuario corrige un slot previamente proporcionado.

**Ejemplo**:
```
Turn 1: "Book a flight"
Turn 2: "Chicago" (origin)
Turn 3: "Actually, I meant Denver not Chicago" (corrección)
Turn 4: "Seattle" (destination)
```

**Estado Esperado**:
- Turn 2: `slots={origin: "Chicago"}`, `current_step=collect_destination`
- Turn 3:
  - `slots={origin: "Denver"}` (corregido)
  - `current_step=collect_destination` (vuelve al paso donde estaba)
  - `conversation_state=waiting_for_slot`
- Turn 4: `slots={origin: "Denver", destination: "Seattle"}`, `current_step=collect_date`

**Estado Actual**: ✅ Funciona correctamente (según código en `validate_slot.py` líneas 307-415)

---

### Escenario 4: Complex - Digresión (Pregunta)
**Descripción**: El usuario hace una pregunta en medio del flujo sin cambiar de flujo.

**Ejemplo**:
```
Turn 1: "I want to book a flight"
Turn 2: "San Francisco" (origin)
Turn 3: "What airports do you support?" (digresión)
Turn 4: "Miami" (destination - continúa el flujo)
```

**Estado Esperado**:
- Turn 2: `slots={origin: "San Francisco"}`, `current_step=collect_destination`
- Turn 3:
  - `digression_depth=1`
  - `last_digression_type="question"`
  - `flow_stack=[book_flight]` (NO cambia)
  - `current_step=collect_destination` (NO cambia)
  - `slots={origin: "San Francisco"}` (NO cambia)
  - Respuesta: Información sobre aeropuertos + reprompt del slot
- Turn 4: `slots={origin: "San Francisco", destination: "Miami"}`, `current_step=collect_date`

**Estado Actual**: ⚠️ Necesita verificación (lógica existe en `handle_digression`)

---

### Escenario 5: Edge - Cancelar Flujo
**Descripción**: El usuario cancela el flujo a mitad de camino.

**Ejemplo**:
```
Turn 1: "Book a flight please"
Turn 2: "Boston" (origin)
Turn 3: "Actually, cancel this"
Turn 4: "I want to book a new flight"
```

**Estado Esperado**:
- Turn 2: `flow_stack=[book_flight]`, `slots={origin: "Boston"}`
- Turn 3:
  - `flow_stack=[]` (flujo cancelado)
  - `flow_slots={}` (slots limpiados)
  - `conversation_state=idle`
- Turn 4: `flow_stack=[book_flight]`, `slots={}` (nuevo flujo)

**Estado Actual**: ⚠️ Necesita verificación (lógica de cancelación)

---

## Análisis del Estado Actual

### Campos del Estado (`DialogueState`)

```python
{
    "user_message": str,                    # Mensaje del usuario actual
    "last_response": str,                   # Última respuesta del agente
    "messages": list[dict],                 # Historial de mensajes
    "flow_stack": list[FlowContext],        # Pila de flujos activos
    "flow_slots": dict[str, dict],          # Slots por flow_id
    "conversation_state": str,               # Estado de la conversación
    "current_step": str | None,             # Paso actual en el flujo
    "waiting_for_slot": str | None,         # Slot que se está esperando
    "current_prompted_slot": str | None,    # Slot que se acaba de preguntar
    "nlu_result": dict | None,              # Resultado del NLU
    "last_nlu_call": dict | None,           # Última llamada al NLU
    "digression_depth": int,                # Profundidad de digresiones
    "last_digression_type": str | None,     # Tipo de última digresión
    "turn_count": int,                      # Contador de turnos
    "trace": list[dict],                    # Traza de eventos
    "metadata": dict,                        # Metadatos adicionales
}
```

### Campos del FlowContext

```python
{
    "flow_id": str,                         # ID único del flujo
    "flow_name": str,                       # Nombre del flujo
    "flow_state": str,                      # Estado del flujo (active, paused, completed)
    "current_step": str | None,             # Paso actual en este flujo
    "outputs": dict,                        # Outputs del flujo
    "started_at": float,                    # Timestamp de inicio
    "paused_at": float | None,              # Timestamp de pausa
    "completed_at": float | None,           # Timestamp de finalización
    "context": str | None,                  # Contexto adicional
}
```

### Estados de Conversación Posibles

```python
"idle"                    # Sin flujo activo
"understanding"           # Procesando mensaje del usuario
"waiting_for_slot"        # Esperando valor de slot
"validating_slot"         # Validando slot
"ready_for_action"        # Listo para ejecutar acción
"executing_action"        # Ejecutando acción
"ready_for_confirmation"  # Listo para confirmación
"confirming"              # Procesando confirmación
"generating_response"     # Generando respuesta
"completed"              # Flujo completado
"error"                   # Error en el flujo
```

---

## Problemas Identificados

### Problema 1: Procesamiento de Múltiples Slots (Escenario 2)

**Ubicación**: `validate_slot_node` en `src/soni/dm/nodes/validate_slot.py`

**Código Problemático**:
```python
# Línea 227
slot = slots[0]  # ❌ Solo procesa el primer slot
```

**Problema**:
- Cuando el NLU extrae múltiples slots en un mensaje, solo se procesa el primero
- Los demás slots se pierden o no se procesan correctamente
- El sistema no avanza automáticamente a través de los pasos completos

**Solución Propuesta**:
1. **Procesar todos los slots en `validate_slot_node`**:
   ```python
   # Iterar sobre todos los slots extraídos
   for slot in slots:
       # Procesar cada slot
       # Verificar si el paso está completo
       # Avanzar al siguiente paso si es necesario
   ```

2. **Avanzar automáticamente a través de pasos completos**:
   - Después de procesar cada slot, verificar si el paso actual está completo
   - Si está completo, avanzar al siguiente paso
   - Continuar hasta encontrar un paso que requiera más información

3. **Manejar el caso especial de `handle_intent_change`**:
   - Cuando se activa un flujo con múltiples slots, procesar todos los slots
   - Avanzar automáticamente a través de los pasos completos
   - Solo entonces preguntar por el siguiente slot faltante

---

### Problema 2: Sincronización entre `current_step` y Slots

**Ubicación**: Múltiples nodos (`handle_intent_change`, `validate_slot`, `collect_next_slot`)

**Problema**:
- Los slots se guardan en `flow_slots` pero `current_step` no se actualiza correctamente
- `waiting_for_slot` puede apuntar a un slot que ya está lleno
- `current_prompted_slot` puede estar desincronizado con el estado real

**Ejemplo del Problema**:
```python
# Estado después de guardar múltiples slots:
{
    "flow_slots": {
        "book_flight_abc123": {
            "origin": "New York",
            "destination": "Los Angeles"
        }
    },
    "current_step": None,  # ❌ Debería ser "collect_date"
    "waiting_for_slot": "destination",  # ❌ Ya está lleno
    "current_prompted_slot": "destination"  # ❌ Ya está lleno
}
```

**Solución Propuesta**:
1. **Función helper para sincronizar estado después de guardar slots**:
   ```python
   def sync_state_after_slots_updated(state, context):
       """Sincroniza current_step y waiting_for_slot después de actualizar slots."""
       step_manager = context["step_manager"]

       # Encontrar el primer paso que no está completo
       flow_config = get_flow_config(context, active_flow_name)
       for step in flow_config.steps:
           if step.type == "collect":
               if not is_step_complete(state, step, context):
                   # Este es el siguiente paso
                   state["current_step"] = step.step
                   state["waiting_for_slot"] = step.slot
                   state["current_prompted_slot"] = step.slot
                   break
   ```

2. **Llamar a esta función después de guardar slots en múltiples lugares**:
   - `handle_intent_change` después de guardar slots
   - `validate_slot` después de actualizar un slot
   - Cualquier lugar donde se actualicen múltiples slots

---

### Problema 3: `collect_next_slot` se ejecuta sin verificar slots pendientes

**Ubicación**: `collect_next_slot_node` en `src/soni/dm/nodes/collect_next_slot.py`

**Problema**:
- Cuando se guardan múltiples slots en `handle_intent_change`, el sistema puede ir a `collect_next_slot` sin verificar si hay slots pendientes de procesar
- `collect_next_slot` puede preguntar por un slot que ya está lleno

**Solución Propuesta**:
1. **Verificar slots pendientes antes de preguntar**:
   ```python
   # En collect_next_slot_node
   # Antes de preguntar por un slot, verificar:
   # 1. ¿Hay slots en nlu_result que no se han procesado?
   # 2. ¿El slot que vamos a preguntar ya está lleno?
   # 3. ¿Hay pasos completos que no se han avanzado?
   ```

2. **Sincronizar estado antes de preguntar**:
   - Llamar a `sync_state_after_slots_updated` antes de determinar qué slot preguntar
   - Solo preguntar por slots que realmente faltan

---

### Problema 4: Routing después de múltiples slots

**Ubicación**: `route_after_validate` en `src/soni/dm/routing.py`

**Problema**:
- Después de procesar múltiples slots, el routing puede no ser correcto
- Puede ir a `collect_next_slot` cuando debería ir a `execute_action` si todos los slots están llenos

**Solución Propuesta**:
1. **Verificar si todos los slots están llenos antes de routing**:
   ```python
   # En route_after_validate
   # Después de procesar slots, verificar:
   # 1. ¿Todos los slots requeridos están llenos?
   # 2. ¿Cuál es el siguiente paso (action, confirm, etc.)?
   # 3. Route accordingly
   ```

---

## Soluciones Propuestas

### Solución 1: Procesar Múltiples Slots en `validate_slot_node`

**Cambios Necesarios**:

1. **Modificar `validate_slot_node` para procesar todos los slots**:
   ```python
   async def validate_slot_node(state, runtime):
       nlu_result = state.get("nlu_result", {})
       slots = nlu_result.get("slots", [])

       if not slots:
           # Manejar caso sin slots (código existente)
           ...

       # ✅ NUEVO: Procesar todos los slots
       processed_slots = {}
       step_manager = runtime.context["step_manager"]

       for slot in slots:
           # Procesar cada slot
           slot_name, raw_value = extract_slot_info(slot)
           normalized_value = await normalizer.normalize_slot(slot_name, raw_value)
           processed_slots[slot_name] = normalized_value

           # Actualizar estado con este slot
           flow_slots = state.get("flow_slots", {}).copy()
           flow_id = active_ctx["flow_id"]
           if flow_id not in flow_slots:
               flow_slots[flow_id] = {}
           flow_slots[flow_id][slot_name] = normalized_value
           state["flow_slots"] = flow_slots

           # Verificar si el paso actual está completo
           current_step_config = step_manager.get_current_step_config(state, runtime.context)
           if current_step_config:
               is_complete = step_manager.is_step_complete(state, current_step_config, runtime.context)

               if is_complete:
                   # Avanzar al siguiente paso
                   updates = step_manager.advance_to_next_step(state, runtime.context)
                   state.update(updates)

       # Determinar conversation_state basado en el siguiente paso
       # (código existente para determinar conversation_state)
       ...
   ```

2. **Función helper para sincronizar estado**:
   ```python
   def sync_state_after_slots_updated(
       state: DialogueState,
       context: RuntimeContext
   ) -> dict[str, Any]:
       """Sincroniza current_step y waiting_for_slot después de actualizar slots."""
       step_manager = context["step_manager"]
       flow_manager = context["flow_manager"]

       active_ctx = flow_manager.get_active_context(state)
       if not active_ctx:
           return {}

       flow_name = active_ctx["flow_name"]
       flow_config = get_flow_config(context, flow_name)

       if not flow_config:
           return {}

       # Encontrar el primer paso que no está completo
       for step in flow_config.steps:
           if step.type == "collect" and step.slot:
               if not step_manager.is_step_complete(state, step, context):
                   # Este es el siguiente paso
                   updates = {
                       "current_step": step.step,
                       "waiting_for_slot": step.slot,
                       "current_prompted_slot": step.slot,
                   }

                   # Actualizar también en FlowContext
                   flow_stack = state.get("flow_stack", []).copy()
                   if flow_stack:
                       flow_stack[-1]["current_step"] = step.step
                   updates["flow_stack"] = flow_stack

                   return updates

       # Todos los pasos collect están completos
       # Encontrar el siguiente paso (action, confirm, etc.)
       current_step_name = active_ctx.get("current_step")
       if current_step_name:
           # Encontrar índice del paso actual
           current_index = None
           for i, step in enumerate(flow_config.steps):
               if step.step == current_step_name:
                   current_index = i
                   break

           if current_index is not None and current_index + 1 < len(flow_config.steps):
               next_step = flow_config.steps[current_index + 1]
               updates = {
                   "current_step": next_step.step,
               }

               # Mapear tipo de paso a conversation_state
               step_type_to_state = {
                   "action": "ready_for_action",
                   "collect": "waiting_for_slot",
                   "confirm": "ready_for_confirmation",
                   "say": "generating_response",
               }
               updates["conversation_state"] = step_type_to_state.get(
                   next_step.type, "understanding"
               )

               # Actualizar también en FlowContext
               flow_stack = state.get("flow_stack", []).copy()
               if flow_stack:
                   flow_stack[-1]["current_step"] = next_step.step
               updates["flow_stack"] = flow_stack

               return updates

       return {}
   ```

3. **Usar esta función en `handle_intent_change`**:
   ```python
   # En handle_intent_change.py después de guardar slots
   if extracted_slots:
       current_slots = get_all_slots(state)
       current_slots.update(extracted_slots)
       set_all_slots(state, current_slots)

       # ✅ NUEVO: Sincronizar estado
       sync_updates = sync_state_after_slots_updated(state, runtime.context)
       if sync_updates:
           state.update(sync_updates)
   ```

---

### Solución 2: Mejorar `collect_next_slot` para verificar slots pendientes

**Cambios Necesarios**:

1. **Verificar slots pendientes antes de preguntar**:
   ```python
   async def collect_next_slot_node(state, runtime):
       # ✅ NUEVO: Sincronizar estado primero
       sync_updates = sync_state_after_slots_updated(state, runtime.context)
       if sync_updates:
           state.update(sync_updates)

       # Verificar si hay slots en nlu_result que no se han procesado
       nlu_result = state.get("nlu_result")
       if nlu_result:
           slots = nlu_result.get("slots", [])
           if slots:
               # Hay slots pendientes - no preguntar, ir a validate_slot
               return {"conversation_state": "validating_slot"}

       # Código existente para preguntar por siguiente slot
       ...
   ```

---

### Solución 3: Mejorar routing después de múltiples slots

**Cambios Necesarios**:

1. **Verificar estado completo antes de routing**:
   ```python
   def route_after_validate(state):
       conv_state = state.get("conversation_state")

       # ✅ NUEVO: Si conversation_state es "ready_for_action", ir directamente
       if conv_state == "ready_for_action":
           return "execute_action"

       # Código existente
       ...
   ```

---

## Plan de Implementación

### Fase 1: Análisis y Diseño
- [x] Documentar todos los escenarios
- [x] Identificar problemas
- [x] Proponer soluciones

### Fase 2: Implementación de Soluciones
- [ ] Implementar función `sync_state_after_slots_updated`
- [ ] Modificar `validate_slot_node` para procesar múltiples slots
- [ ] Modificar `handle_intent_change` para sincronizar estado
- [ ] Mejorar `collect_next_slot` para verificar slots pendientes
- [ ] Mejorar routing después de múltiples slots

### Fase 3: Testing
- [ ] Test del Escenario 2 (múltiples slots en un mensaje)
- [ ] Test de todos los escenarios para verificar que no se rompió nada
- [ ] Test de casos edge (múltiples slots + corrección, etc.)

### Fase 4: Documentación
- [ ] Actualizar documentación de diseño
- [ ] Documentar el comportamiento esperado para múltiples slots
- [ ] Actualizar guías de desarrollo

---

## Conclusión

El problema principal identificado es que **el sistema no procesa correctamente múltiples slots extraídos en un solo mensaje**. La solución requiere:

1. **Procesar todos los slots** en lugar de solo el primero
2. **Avanzar automáticamente** a través de los pasos completos
3. **Sincronizar el estado** después de actualizar slots
4. **Verificar slots pendientes** antes de preguntar por nuevos slots

Estas mejoras asegurarán que el Escenario 2 (y otros escenarios similares) funcionen correctamente.

---

## Referencias

**⭐ Para soluciones detalladas y evaluación SOLID/DRY, consultar:**

**[SOLUCION_MULTIPLES_SLOTS.md](SOLUCION_MULTIPLES_SLOTS.md)**

Este documento contiene:
- Análisis completo de las 3 soluciones propuestas
- Evaluación contra principios SOLID y DRY
- Solución recomendada: **Solution 3 - Hybrid Approach with Step Advancement Iterator**
- Plan de implementación detallado
- Estrategia de testing
- Análisis de riesgos

**Solución Recomendada**: Solution 3 - Hybrid Approach
- ✅✅ Excellent SOLID compliance (especially SRP)
- ✅✅ Excellent DRY compliance
- ✅✅ Maximum testability
- ✅ Minimal risk with comprehensive tests
- Esfuerzo estimado: 8-12 horas
