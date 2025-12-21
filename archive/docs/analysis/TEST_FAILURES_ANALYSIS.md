# Análisis de Tests Fallidos

## Resumen Ejecutivo

Se analizaron 6 tests fallidos para determinar si los problemas son del NLU (no reconociendo bien) o de la lógica del sistema. El análisis muestra una mezcla de ambos tipos de problemas.

## Tests Fallidos

### 1. `test_scenario_1_complete_flow` - Problema de NLU

**Error**: `assert 'destination' in ('departure_date', None)`

**Descripción**: Después de proporcionar "Barcelona" como destino, el sistema está esperando `departure_date` en lugar de `destination`, lo que sugiere que no reconoció "Barcelona" como el valor del slot `destination`.

**Análisis**:
- **Tipo**: Problema de NLU
- **Causa probable**: El NLU no extrajo "Barcelona" como valor del slot `destination`
- **Evidencia**: El sistema avanzó directamente a `departure_date`, lo que indica que asumió que `destination` ya estaba lleno o no lo reconoció
- **Ubicación**: `src/soni/dm/nodes/validate_slot.py` - El fallback de NLU debería manejar este caso, pero parece que no está funcionando correctamente

**Solución sugerida**:
1. Verificar que el NLU está recibiendo el contexto correcto con `current_prompted_slot="destination"`
2. Revisar el fallback en `validate_slot.py` (líneas 312-451) para asegurar que se ejecuta correctamente
3. Verificar que el NLU está optimizado para reconocer nombres de ciudades como valores de slots

---

### 2. `test_scenario_4_digression` - Problema de NLU

**Error**: `assert 'Miami' == 'San Francisco'`

**Descripción**: Después de una digresión y proporcionar "Miami" como destino, el sistema mantiene "San Francisco" (el origen) como destino.

**Análisis**:
- **Tipo**: Problema de NLU
- **Causa probable**: El NLU no está extrayendo "Miami" como un nuevo valor de slot `destination`, o está confundiendo el origen con el destino
- **Evidencia**: El slot `destination` contiene "San Francisco" (que es el origen) en lugar de "Miami"
- **Ubicación**: `src/soni/dm/nodes/validate_slot.py` o `src/soni/du/modules.py`

**Solución sugerida**:
1. Verificar que después de una digresión, el NLU recibe el contexto correcto con `waiting_for_slot="destination"`
2. Asegurar que el NLU distingue entre origen y destino correctamente
3. Revisar el manejo de digresiones en `handle_digression.py` para asegurar que preserva el contexto correcto

---

### 3. `test_action_to_confirmation_flow` - Problema de Lógica

**Error**: `Recursion limit of 25 reached without hitting a stop condition`

**Descripción**: El sistema entra en un loop infinito después de ejecutar la acción y llegar a la confirmación.

**Análisis**:
- **Tipo**: Problema de Lógica
- **Causa probable**: Hay un ciclo en el grafo de LangGraph que no tiene una condición de parada
- **Evidencia**: El sistema alcanza el límite de recursión (25 iteraciones) sin llegar a un estado terminal
- **Ubicación**: Probablemente en el routing después de `confirm_action` o `execute_action`

**Solución sugerida**:
1. Revisar `route_after_action` y `route_after_confirmation` en `routing.py`
2. Verificar que después de mostrar la confirmación, el sistema espera input del usuario (no continúa automáticamente)
3. Asegurar que `conversation_state="confirming"` detiene el flujo correctamente
4. Revisar `should_continue_flow` para asegurar que detecta cuando debe parar

---

### 4. `test_complete_confirmation_flow_no_then_modify` - Problema de NLU

**Error**: `assert ('change' in 'i found flights for your trip:\n- from: new york\n- to: \n- date: 2025-12-15\n- price: $299.99\...`

**Descripción**: Después de "No, change the destination", el sistema muestra información de vuelos en lugar de preguntar qué cambiar.

**Análisis**:
- **Tipo**: Problema de NLU (principalmente) con posible problema de lógica
- **Causa probable**:
  - El NLU no reconoció "No, change the destination" como una negación de confirmación
  - O el routing no está enviando a `handle_modification` correctamente
- **Evidencia**: La respuesta contiene información de vuelos, lo que sugiere que el sistema ejecutó la acción en lugar de manejar la negación
- **Ubicación**: `src/soni/dm/routing.py` (línea 378-396) - routing de confirmación

**Solución sugerida**:
1. Verificar que el NLU reconoce "No, change the destination" como `message_type="confirmation"` con `confirmation_value=False`
2. Revisar `handle_confirmation_node` para asegurar que maneja correctamente las negaciones con modificaciones
3. Verificar que cuando `confirmation_value=False`, el sistema no ejecuta la acción

---

### 5. `test_confirmation_max_retries` - Problema de Lógica

**Error**: `assert ('trouble' in 'i understand your question. we need this information to proceed.' or 'start over' in ...`

**Descripción**: Después de 3 respuestas poco claras, el sistema no muestra el mensaje de error esperado.

**Análisis**:
- **Tipo**: Problema de Lógica
- **Causa probable**: El contador de intentos no se está incrementando correctamente, o la condición de max retries no se está evaluando
- **Evidencia**: El sistema responde con "I understand your question..." en lugar del mensaje de error esperado
- **Ubicación**: `src/soni/dm/nodes/handle_confirmation.py` (líneas 44-66, 140-162)

**Solución sugerida**:
1. Verificar que `MetadataManager.increment_confirmation_attempts` está funcionando correctamente
2. Revisar la lógica de max retries en `handle_confirmation_node` - parece que hay dos checks (líneas 51 y 147) que podrían estar en conflicto
3. Asegurar que el mensaje de error se genera correctamente cuando se alcanza el límite

---

### 6. `test_e2e_flight_booking_complete_flow` - Problema de NLU

**Error**: `Response should mention flight/booking or error, got: Got it, I've updated destination to Los Angeles.`

**Descripción**: Después de proporcionar "Next Friday" como fecha, el sistema responde como si fuera una corrección del destino.

**Análisis**:
- **Tipo**: Problema de NLU
- **Causa probable**: El NLU está interpretando "Next Friday" como una corrección del slot `destination` en lugar de reconocerlo como una fecha para `departure_date`
- **Evidencia**: La respuesta es "Got it, I've updated destination to Los Angeles", lo que indica que el NLU clasificó el mensaje como `modification` o `correction` en lugar de `slot_value`
- **Ubicación**: `src/soni/du/modules.py` - clasificación de mensajes

**Solución sugerida**:
1. Verificar que el NLU está recibiendo `waiting_for_slot="departure_date"` en el contexto
2. Revisar la clasificación de mensajes en el NLU - "Next Friday" debería ser claramente reconocido como una fecha
3. Asegurar que el NLU prioriza `current_prompted_slot` al clasificar mensajes
4. Revisar el routing en `route_after_understand` (línea 278-330) para asegurar que no está malinterpretando el tipo de mensaje

---

## Resumen por Tipo de Problema

### Problemas de NLU (4 tests)
1. `test_scenario_1_complete_flow` - No reconoce "Barcelona" como destino
2. `test_scenario_4_digression` - No reconoce "Miami" como destino después de digresión
3. `test_complete_confirmation_flow_no_then_modify` - No reconoce negación con modificación
4. `test_e2e_flight_booking_complete_flow` - Interpreta "Next Friday" como corrección en lugar de fecha

### Problemas de Lógica (2 tests)
1. `test_action_to_confirmation_flow` - Loop infinito en confirmación
2. `test_confirmation_max_retries` - No maneja correctamente max retries

## Recomendaciones Prioritarias

### Prioridad Alta (Bloqueantes)
1. **Arreglar el loop infinito en confirmación** (`test_action_to_confirmation_flow`)
   - Revisar routing después de `confirm_action`
   - Asegurar que el flujo se detiene cuando `conversation_state="confirming"`

2. **Mejorar reconocimiento de slots por NLU**
   - Verificar que `current_prompted_slot` se está pasando correctamente al NLU
   - Revisar el fallback en `validate_slot.py` para asegurar que funciona
   - Optimizar el NLU para reconocer nombres de ciudades y fechas

### Prioridad Media
3. **Arreglar max retries en confirmación** (`test_confirmation_max_retries`)
   - Revisar la lógica de incremento de contador
   - Asegurar que el mensaje de error se muestra correctamente

4. **Mejorar reconocimiento de negaciones con modificaciones**
   - Asegurar que "No, change X" se clasifica correctamente
   - Verificar que el routing envía a `handle_modification` cuando corresponde

### Prioridad Baja
5. **Mejorar manejo de digresiones**
   - Asegurar que el contexto se preserva correctamente después de digresiones
   - Verificar que el NLU recibe el contexto correcto después de digresiones

## Archivos a Revisar

1. `src/soni/dm/routing.py` - Routing después de confirmación y acción
2. `src/soni/dm/nodes/validate_slot.py` - Fallback de NLU
3. `src/soni/dm/nodes/handle_confirmation.py` - Lógica de max retries
4. `src/soni/du/modules.py` - Clasificación de mensajes en NLU
5. `src/soni/dm/nodes/handle_digression.py` - Preservación de contexto
