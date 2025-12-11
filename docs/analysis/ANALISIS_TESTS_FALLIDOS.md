# Análisis de Tests Fallidos - 10 Fallos Restantes

## Resumen Ejecutivo

De los 10 tests que fallan:
- **5 son problemas del NLU** (clasificación incorrecta) - Se resolverán con optimización
- **3 son problemas de lógica/configuración** - Requieren corrección
- **2 son problemas de configuración de tests** (optimizadores) - Requieren ajuste de tests

---

## 1. Problemas del NLU (5 tests) - ✅ Se resolverán con optimización

### 1.1. `test_nlu_cancellation_detection`
**Error**: `AssertionError: assert <MessageType.interruption> == <MessageType.cancellation>`

**Problema**: El NLU clasifica "Cancel" como `INTERRUPTION` en lugar de `CANCELLATION`.

**Contexto**:
- `current_flow="book_flight"`
- `available_flows={"book_flight": "Book a flight"}`
- El NLU interpreta "Cancel" como querer cambiar a otro flow (INTERRUPTION) en lugar de cancelar el actual (CANCELLATION)

**Solución**: Mejorar el signature del NLU para distinguir mejor CANCELLATION vs INTERRUPTION. La optimización debería ayudar.

---

### 1.2. `test_e2e_flight_booking_complete_flow`
**Error**: `AssertionError: Response should mention flight/booking or error, got: What is your departure date?`

**Problema**: Después de proporcionar la fecha, el sistema pregunta por la fecha de nuevo en lugar de ejecutar la acción `search_flights`.

**Contexto**:
- Después de `collect_date`, el siguiente paso es `search_flights` (acción)
- El sistema debería ejecutar la acción, pero pregunta por date de nuevo

**Posible causa**:
- El NLU no está extrayendo correctamente el slot `departure_date`
- O hay un problema con `advance_through_completed_steps` que no avanza al siguiente paso (acción)

**Nota**: Este es el mismo problema del `last_response` que estábamos investigando, pero también podría ser que el NLU no extrae el slot correctamente.

---

### 1.3. `test_mix_new_slots_and_corrections`
**Error**: `AssertionError: assert 'Chicago' == 'Denver'`

**Problema**: Cuando el usuario dice "Actually, I meant Denver, and I want to go to Seattle", el sistema no corrige `origin` de "Chicago" a "Denver".

**Contexto**:
- Slot actual: `origin="Chicago"`
- Usuario corrige: "Actually, I meant Denver"
- También proporciona nuevo slot: "I want to go to Seattle" (destination)

**Posible causa**:
- El NLU no está detectando correctamente la corrección cuando hay múltiples intenciones en el mismo mensaje
- O no está extrayendo ambos slots (corrección + nuevo slot) correctamente

**Solución**: La optimización del NLU debería mejorar la extracción de múltiples slots y la detección de correcciones.

---

### 1.4. `test_complete_confirmation_flow_no_then_modify`
**Error**: `AssertionError: assert ('change' in 'i found flights for your trip:\n- from: new york\...`

**Problema**: Cuando el usuario dice "No, change the destination" después de una confirmación, el sistema no detecta la modificación.

**Contexto**:
- Estado: `conversation_state="confirming"`
- Usuario: "No, change the destination"
- Esperado: Sistema pregunta qué cambiar o permite modificar
- Actual: Sistema muestra resultados de vuelos (como si hubiera confirmado)

**Posible causa**:
- El NLU no está clasificando correctamente como `MODIFICATION` cuando `conversation_state="confirming"`
- O el routing no está manejando correctamente la modificación después de confirmación

**Solución**: La optimización del NLU debería mejorar la detección de modificaciones en contexto de confirmación.

---

### 1.5. `test_confirmation_max_retries`
**Error**: `AssertionError: assert 'understand' in 'your flight aa123 from chicago to denver on 20...'`

**Problema**: Después de respuestas poco claras a la confirmación, el sistema no está manejando correctamente los reintentos.

**Contexto**:
- Estado: `conversation_state="confirming"`
- Usuario da respuestas poco claras: "maybe", "hmm", "I don't know"
- Esperado: Sistema debería pedir clarificación o mostrar error después de max retries
- Actual: Sistema procesa como si fuera una confirmación positiva

**Posible causa**:
- El NLU no está clasificando correctamente respuestas poco claras como `CLARIFICATION` o `DIGRESSION`
- O el sistema no está manejando correctamente los reintentos de confirmación

**Solución**: La optimización del NLU debería mejorar la detección de respuestas poco claras.

---

## 2. Problemas de Lógica/Configuración (3 tests) - ⚠️ Requieren corrección

### 2.1. `test_scenario_5_cancellation`
**Error**: `GraphRecursionError: Recursion limit of 25 reached`

**Problema**: Loop infinito cuando el usuario cancela el flow.

**Contexto**:
- Usuario: "Actually, cancel this"
- El sistema entra en un loop infinito

**Posible causa**:
- El routing después de `handle_cancellation` no está funcionando correctamente
- O `handle_cancellation` no está limpiando correctamente el estado

**Solución**: Revisar la lógica de `handle_cancellation` y el routing después de cancelación.

---

### 2.2. `test_digression_flow_with_mocked_nlu`
**Error**: `AssertionError: assert 'idle' == 'waiting_for_slot'`

**Problema**: Después de una digresión, el `conversation_state` es `idle` en lugar de `waiting_for_slot`.

**Contexto**:
- El NLU está mockeado (no es problema del NLU)
- Después de manejar una digresión, el sistema debería mantener `waiting_for_slot`
- Pero el estado es `idle`

**Posible causa**:
- `handle_digression` no está preservando correctamente el `conversation_state`
- O `generate_response` está cambiando el estado a `idle` incorrectamente

**Solución**: Revisar la lógica de `handle_digression` y cómo preserva el estado.

---

### 2.3. `test_correction_uses_acknowledgment_template`
**Error**: `AssertionError: Response should acknowledge correction using template. Got: I found fl...`

**Problema**: Cuando se corrige un slot, el sistema no está usando el template de acknowledgment.

**Contexto**:
- Usuario corrige: "Actually, change the date to next Monday"
- Esperado: Sistema debería usar template `correction_acknowledged: "Got it, I've updated {slot_name} to {new_value}."`
- Actual: Sistema muestra resultados de vuelos (como si no hubiera detectado la corrección)

**Posible causa**:
- `handle_correction` no está generando correctamente el acknowledgment
- O el routing no está yendo a `handle_correction` cuando debería

**Nota**: Este podría ser también un problema del NLU si no está detectando la corrección, pero el error sugiere que el sistema está procesando como si fuera una acción normal.

**Solución**: Revisar la lógica de `handle_correction` y el uso de templates.

---

## 3. Problemas de Configuración de Tests (2 tests) - ⚠️ Requieren ajuste

### 3.1-3.2. Tests de Optimizadores
**Error**: `RuntimeError: Optimization failed: Minibatch size cannot exceed the size of the valset. Valset size: 1.`

**Problema**: Los tests de optimización están usando un valset demasiado pequeño (1 ejemplo).

**Tests afectados**:
- `test_optimize_soni_du_returns_module_and_metrics`
- `test_optimize_soni_du_saves_module`
- `test_optimize_soni_du_integration`

**Solución**: Ajustar los tests para usar un valset más grande o configurar el optimizador para aceptar valsets pequeños.

---

## Recomendaciones

### Prioridad Alta (Problemas de Lógica)
1. **`test_scenario_5_cancellation`**: Loop infinito - crítico, bloquea funcionalidad
2. **`test_digression_flow_with_mocked_nlu`**: Estado incorrecto - afecta UX
3. **`test_correction_uses_acknowledgment_template`**: Templates no se usan - afecta UX

### Prioridad Media (Problemas del NLU - se resolverán con optimización)
4. **`test_nlu_cancellation_detection`**: Clasificación incorrecta
5. **`test_e2e_flight_booking_complete_flow`**: No avanza después de fecha (podría ser lógica también)
6. **`test_mix_new_slots_and_corrections`**: No extrae múltiples slots
7. **`test_complete_confirmation_flow_no_then_modify`**: No detecta modificación
8. **`test_confirmation_max_retries`**: No maneja respuestas poco claras

### Prioridad Baja (Configuración de Tests)
9-10. **Tests de optimizadores**: Ajustar configuración de tests

---

## Conclusión

**5 de 10 fallos son problemas del NLU** que deberían resolverse con la optimización.

**3 de 10 son problemas de lógica** que requieren corrección independiente de la optimización.

**2 de 10 son problemas de configuración de tests** que requieren ajuste.

La optimización del NLU debería resolver la mayoría de los problemas de clasificación y extracción, pero los problemas de lógica (especialmente el loop infinito en cancelación) requieren atención inmediata.
