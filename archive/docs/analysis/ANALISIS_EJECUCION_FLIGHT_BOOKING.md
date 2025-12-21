# Análisis de Ejecución: Flight Booking Flow

**Fecha**: 2025-12-08
**Objetivo**: Explicar cómo se ejecuta el framework Soni cuando un usuario interactúa con el asistente usando el ejemplo `flight_booking/soni.yaml`

## Resumen Ejecutivo

Este documento traza el flujo completo de ejecución del framework Soni desde que el usuario envía su primer mensaje hasta que se completa el flujo de reserva de vuelo. Se asume que el NLU devuelve los resultados esperados en cada paso.

## Arquitectura General

### Componentes Principales

1. **RuntimeLoop**: Orquestador principal que recibe mensajes del usuario
2. **LangGraph**: Máquina de estados que coordina los nodos
3. **Nodos del Grafo**:
   - `understand`: Procesa NLU
   - `validate_slot`: Valida y normaliza slots
   - `collect_next_slot`: Solicita el siguiente slot (con interrupt)
   - `execute_action`: Ejecuta acciones externas
   - `generate_response`: Genera respuesta final
4. **FlowManager**: Gestiona el stack de flujos activos
5. **StepManager**: Gestiona la progresión secuencial de pasos

### Flujo de Alto Nivel

```
Usuario → RuntimeLoop → LangGraph → Nodos → Estado Actualizado → Respuesta
```

## Escenario Completo: Reserva de Vuelo

### Configuración del Flujo (YAML)

```yaml
flows:
  book_flight:
    steps:
      - step: collect_origin
        type: collect
        slot: origin
      - step: collect_destination
        type: collect
        slot: destination
      - step: collect_date
        type: collect
        slot: departure_date
      - step: search_flights
        type: action
        call: search_available_flights
      - step: confirm_booking
        type: action
        call: confirm_flight_booking
```

---

## Turno 1: Inicio del Flujo

### Mensaje del Usuario
```
"I want to book a flight"
```

### 1. RuntimeLoop.process_message()

**Ubicación**: `src/soni/runtime/runtime.py:629`

```python
async def process_message(self, user_msg: str, user_id: str) -> str:
    # 1. Validar y sanitizar inputs
    sanitized_msg, sanitized_user_id = self._validate_inputs(user_msg, user_id)

    # 2. Asegurar que el grafo está inicializado
    await self._ensure_graph_initialized()

    # 3. Cargar o crear estado
    state = await self._load_or_create_state(sanitized_user_id, sanitized_msg)

    # 4. Ejecutar grafo
    result = await self._execute_graph(state, sanitized_user_id)

    # 5. Extraer y retornar respuesta
    return self._extract_response(result, sanitized_user_id)
```

**Estado Inicial Creado**:
```python
{
    "user_message": "I want to book a flight",
    "messages": [{"role": "user", "content": "I want to book a flight"}],
    "flow_stack": [],
    "flow_slots": {},
    "turn_count": 1,
    "conversation_state": "idle",
    "waiting_for_slot": None,
    ...
}
```

### 2. RuntimeLoop._execute_graph()

**Ubicación**: `src/soni/runtime/runtime.py:403`

```python
# Verificar si el grafo está interrumpido
snapshot = await self.graph.aget_state(config)

if snapshot and snapshot.next:
    # Grafo interrumpido - reanudar con mensaje del usuario
    result = await self.graph.ainvoke(
        Command(resume=state["user_message"]),
        config=config
    )
else:
    # Nueva conversación - iniciar desde el principio
    result = await self.graph.ainvoke(
        state_to_dict(state),
        config=config
    )
```

**En este caso**: No hay estado previo, así que se ejecuta `ainvoke()` con el estado inicial.

### 3. LangGraph: START → understand

**Grafo**: `src/soni/dm/builder.py:101`
```python
builder.add_edge(START, "understand")
```

El grafo siempre comienza en el nodo `understand`.

### 4. Nodo: understand_node()

**Ubicación**: `src/soni/dm/nodes/understand.py:12`

**Proceso**:

1. **Construir contexto NLU**:
   ```python
   active_ctx = flow_manager.get_active_context(state)  # None (no hay flujo activo)
   current_flow_name = "none"
   available_flows = {"book_flight": FlowConfig(...)}
   expected_slots = []  # No hay flujo activo aún
   ```

2. **Detección de comando (two-stage prediction)**:
   ```python
   # Stage 1: Detectar comando/intent
   intent_context = DialogueContext(
       current_flow="none",
       expected_slots=[],  # Vacío - solo detectar intent
       available_flows=available_flows,
       ...
   )
   intent_result = await nlu_provider.predict(
       "I want to book a flight",
       history,
       intent_context
   )
   # Resultado esperado: command = "book_flight"
   ```

3. **Stage 2: Mapear comando a flujo y re-predecir**:
   ```python
   detected_flow = activate_flow_by_intent(
       command="book_flight",
       current_flow="none",
       config=config
   )
   # detected_flow = "book_flight"

   # Obtener expected_slots para el flujo detectado
   detected_expected_slots = ["origin", "destination", "departure_date"]

   # Stage 2: Re-predecir con expected_slots correctos
   slot_context = DialogueContext(
       current_flow="book_flight",
       expected_slots=["origin", "destination", "departure_date"],
       ...
   )
   final_result = await nlu_provider.predict(
       "I want to book a flight",
       history,
       slot_context
   )
   ```

4. **Resultado NLU** (asumido):
   ```python
   {
       "command": "book_flight",
       "message_type": "intent_change",  # Cambio de intent (no hay flujo activo)
       "slots": [],  # No se extrajeron slots del mensaje inicial
       "confidence": 0.95
   }
   ```

5. **Retorno del nodo**:
   ```python
   return {
       "nlu_result": nlu_result,
       "conversation_state": "understanding",
       "last_nlu_call": time.time()
   }
   ```

### 5. Routing: route_after_understand()

**Ubicación**: `src/soni/dm/routing.py:225`

```python
def route_after_understand(state: DialogueStateType) -> str:
    nlu_result = state.get("nlu_result")
    message_type = nlu_result.get("message_type")  # "intent_change"

    match message_type:
        case "intent_change":
            return "handle_intent_change"
```

**Ruta seleccionada**: `handle_intent_change`

### 6. Nodo: handle_intent_change_node()

**Proceso**:

1. **Activar flujo**:
   ```python
   flow_manager = runtime.context["flow_manager"]
   flow_id = flow_manager.push_flow(
       state,
       flow_name="book_flight",
       inputs=None,
       reason="User intent: book_flight"
   )
   # flow_id = "book_flight_a3f7b2c1"
   ```

2. **Estado actualizado**:
   ```python
   {
       "flow_stack": [
           {
               "flow_id": "book_flight_a3f7b2c1",
               "flow_name": "book_flight",
               "flow_state": "active",
               "current_step": "collect_origin",  # Primer paso del flujo
               "started_at": 1234567890.0
           }
       ],
       "flow_slots": {
           "book_flight_a3f7b2c1": {}  # Slots vacíos inicialmente
       }
   }
   ```

3. **Avanzar al primer paso**:
   ```python
   step_manager = runtime.context["step_manager"]
   step_updates = step_manager.advance_to_next_step(state, runtime.context)
   # step_updates = {
   #     "conversation_state": "waiting_for_slot",  # Siguiente paso es "collect"
   #     "flow_stack": [...]
   # }
   ```

4. **Retorno**:
   ```python
   return {
       **step_updates,
       "conversation_state": "waiting_for_slot"
   }
   ```

### 7. Routing: Después de handle_intent_change

**Grafo**: `src/soni/dm/builder.py:158`
```python
builder.add_edge("handle_intent_change", "understand")
```

**Nota**: Después de cambiar de intent, el grafo vuelve a `understand` para procesar el mensaje original con el nuevo contexto del flujo activo.

### 8. Nodo: understand_node() (Segunda vez)

Ahora con flujo activo:

```python
active_ctx = flow_manager.get_active_context(state)
current_flow_name = "book_flight"
expected_slots = ["origin", "destination", "departure_date"]
waiting_for_slot = None  # Aún no se ha preguntado por ningún slot
```

**NLU con contexto completo**:
```python
dialogue_context = DialogueContext(
    current_flow="book_flight",
    expected_slots=["origin", "destination", "departure_date"],
    current_prompted_slot=None,
    ...
)

nlu_result = await nlu_provider.predict(
    "I want to book a flight",
    history,
    dialogue_context
)
```

**Resultado NLU** (asumido):
```python
{
    "command": "book_flight",
    "message_type": "continuation",  # Continuar con el flujo
    "slots": [],  # No se extrajeron slots
    "confidence": 0.95
}
```

### 9. Routing: route_after_understand()

```python
match message_type:
    case "continuation":
        if has_active_flow:
            return "collect_next_slot"  # Continuar recopilando slots
```

**Ruta seleccionada**: `collect_next_slot`

### 10. Nodo: collect_next_slot_node()

**Ubicación**: `src/soni/dm/nodes/collect_next_slot.py:11`

**Proceso**:

1. **Obtener paso actual**:
   ```python
   current_step_config = step_manager.get_current_step_config(state, runtime.context)
   # current_step_config = StepConfig(
   #     step="collect_origin",
   #     type="collect",
   #     slot="origin"
   # )
   ```

2. **Obtener siguiente slot requerido**:
   ```python
   next_slot = step_manager.get_next_required_slot(
       state,
       current_step_config,
       runtime.context
   )
   # next_slot = "origin"
   ```

3. **Obtener prompt del slot**:
   ```python
   slot_config = get_slot_config(runtime.context, "origin")
   prompt = slot_config.prompt  # "Where would you like to fly from?"
   ```

4. **Interrumpir y esperar respuesta**:
   ```python
   from langgraph.types import interrupt
   user_response = interrupt(prompt)
   ```

**Interrupt Pattern**:
- El nodo llama a `interrupt(prompt)`
- LangGraph pausa la ejecución
- El prompt se guarda en `result["__interrupt__"]`
- El grafo queda en estado "interrupted" esperando reanudación

5. **Retorno** (después de reanudación):
   ```python
   return {
       "user_message": user_response,  # Valor del resume
       "waiting_for_slot": "origin",
       "current_prompted_slot": "origin",
       "conversation_state": "waiting_for_slot"
   }
   ```

### 11. RuntimeLoop._process_interrupts()

**Ubicación**: `src/soni/runtime/runtime.py:528`

```python
def _process_interrupts(self, result: dict[str, Any]) -> None:
    interrupts = result["__interrupt__"]
    first_interrupt = interrupts[0]
    prompt = first_interrupt.value  # "Where would you like to fly from?"
    result["last_response"] = prompt
```

### 12. Respuesta al Usuario

```
"Where would you like to fly from?"
```

**Estado del Grafo**: Interrumpido, esperando reanudación con `Command(resume=user_message)`

---

## Turno 2: Proporcionar Origen

### Mensaje del Usuario
```
"New York"
```

### 1. RuntimeLoop.process_message()

El estado se carga desde el checkpoint:
```python
state = await self._load_or_create_state(user_id, "New York")
# state["flow_stack"] = [FlowContext con current_step="collect_origin"]
# state["waiting_for_slot"] = "origin"
```

### 2. RuntimeLoop._execute_graph()

```python
snapshot = await self.graph.aget_state(config)
# snapshot.next = ("collect_next_slot",)  # Grafo interrumpido

# Reanudar con mensaje del usuario
result = await self.graph.ainvoke(
    Command(resume="New York"),
    config=config
)
```

**Comportamiento de LangGraph**:
- Detecta que el grafo está interrumpido
- Reanuda desde el nodo `collect_next_slot`
- `interrupt()` retorna el valor del `Command(resume=...)`
- El nodo continúa su ejecución

### 3. Nodo: collect_next_slot_node() (Reanudado)

```python
# interrupt() ahora retorna "New York"
user_response = interrupt(prompt)  # Retorna "New York"

return {
    "user_message": "New York",  # Mensaje del usuario
    "waiting_for_slot": "origin",
    "current_prompted_slot": "origin",
    "conversation_state": "waiting_for_slot"
}
```

**Nota**: El grafo continúa desde `collect_next_slot` pero necesita procesar el mensaje del usuario, así que el routing lo lleva a `understand`.

### 4. Routing: Después de collect_next_slot

**Grafo**: `src/soni/dm/builder.py:158`
```python
builder.add_edge("collect_next_slot", "understand")
```

**Ruta**: `collect_next_slot` → `understand`

### 5. Nodo: understand_node()

**Contexto**:
```python
active_ctx = flow_manager.get_active_context(state)
current_flow_name = "book_flight"
expected_slots = ["origin", "destination", "departure_date"]
waiting_for_slot = "origin"  # Estamos esperando este slot
```

**NLU con contexto**:
```python
dialogue_context = DialogueContext(
    current_flow="book_flight",
    expected_slots=["origin", "destination", "departure_date"],
    current_prompted_slot="origin",  # Prioridad: este slot
    ...
)

nlu_result = await nlu_provider.predict(
    "New York",
    history,
    dialogue_context
)
```

**Resultado NLU** (asumido):
```python
{
    "command": "book_flight",
    "message_type": "slot_value",  # Proporciona un valor de slot
    "slots": [
        {
            "name": "origin",
            "value": "New York",
            "action": "provide",
            "confidence": 0.98
        }
    ],
    "confidence": 0.98
}
```

### 6. Routing: route_after_understand()

```python
match message_type:
    case "slot_value":
        if has_active_flow:
            return "validate_slot"
```

**Ruta seleccionada**: `validate_slot`

### 7. Nodo: validate_slot_node()

**Ubicación**: `src/soni/dm/nodes/validate_slot.py:269`

**Proceso**:

1. **Procesar slots**:
   ```python
   slots = nlu_result.get("slots", [])
   # slots = [{"name": "origin", "value": "New York"}]

   flow_slots = await _process_all_slots(
       slots,
       state,
       active_ctx,
       normalizer
   )
   # flow_slots = {
   #     "book_flight_a3f7b2c1": {
   #         "origin": "New York"  # Normalizado
   #     }
   # }
   ```

2. **Normalización**:
   ```python
   normalized_value = await normalizer.normalize_slot("origin", "New York")
   # normalized_value = "New York"  # (o "NYC" si hay normalización)
   ```

3. **Validación**:
   ```python
   validator = ValidatorRegistry.get("city_name")
   is_valid = await validator.validate("origin", "New York")
   # is_valid = True
   ```

4. **Avanzar al siguiente paso**:
   ```python
   step_updates = step_manager.advance_to_next_step(state, runtime.context)
   # step_updates = {
   #     "conversation_state": "waiting_for_slot",  # Siguiente paso es "collect"
   #     "flow_stack": [{
   #         "current_step": "collect_destination"  # Actualizado
   #     }]
   # }
   ```

5. **Retorno**:
   ```python
   return {
       "flow_slots": flow_slots,
       "waiting_for_slot": None,  # Ya no estamos esperando
       "current_prompted_slot": None,
       **step_updates
   }
   ```

### 8. Routing: route_after_validate()

**Ubicación**: `src/soni/dm/routing.py:426`

```python
def route_after_validate(state: DialogueStateType) -> str:
    conv_state = state.get("conversation_state")  # "waiting_for_slot"

    if conv_state == "waiting_for_slot":
        return "collect_next_slot"
```

**Ruta seleccionada**: `collect_next_slot`

### 9. Nodo: collect_next_slot_node()

**Proceso**:

1. **Obtener paso actual**:
   ```python
   current_step_config = step_manager.get_current_step_config(state, runtime.context)
   # current_step_config = StepConfig(
   #     step="collect_destination",
   #     type="collect",
   #     slot="destination"
   # )
   ```

2. **Obtener siguiente slot**:
   ```python
   next_slot = step_manager.get_next_required_slot(...)
   # next_slot = "destination"
   ```

3. **Obtener prompt**:
   ```python
   slot_config = get_slot_config(runtime.context, "destination")
   prompt = slot_config.prompt  # "Where would you like to fly to?"
   ```

4. **Interrumpir**:
   ```python
   user_response = interrupt(prompt)
   ```

### 10. Respuesta al Usuario

```
"Where would you like to fly to?"
```

---

## Turno 3: Proporcionar Destino

### Mensaje del Usuario
```
"Los Angeles"
```

### Flujo Similar al Turno 2

1. **RuntimeLoop**: Carga estado, reanuda grafo
2. **collect_next_slot**: Retorna con `user_message="Los Angeles"`
3. **understand**: NLU extrae `destination="Los Angeles"`
4. **validate_slot**: Valida, normaliza, guarda en `flow_slots`
5. **advance_to_next_step**: Avanza a `collect_date`
6. **collect_next_slot**: Pregunta por `departure_date`

### Estado Actualizado

```python
{
    "flow_stack": [{
        "flow_id": "book_flight_a3f7b2c1",
        "current_step": "collect_date",  # Avanzado
        ...
    }],
    "flow_slots": {
        "book_flight_a3f7b2c1": {
            "origin": "New York",
            "destination": "Los Angeles"
        }
    }
}
```

### Respuesta al Usuario

```
"When would you like to depart?"
```

---

## Turno 4: Proporcionar Fecha

### Mensaje del Usuario
```
"Tomorrow"
```

### Flujo Similar

1. **understand**: NLU extrae `departure_date="Tomorrow"`
2. **validate_slot**:
   - Normaliza "Tomorrow" → "2025-12-09" (ISO format)
   - Valida con `future_date_only`
   - Guarda en `flow_slots`
3. **advance_to_next_step**: Avanza a `search_flights` (tipo "action")
4. **route_after_validate**: `conversation_state="ready_for_action"` → `execute_action`

### Estado Actualizado

```python
{
    "flow_stack": [{
        "current_step": "search_flights",  # Paso de acción
        ...
    }],
    "flow_slots": {
        "book_flight_a3f7b2c1": {
            "origin": "New York",
            "destination": "Los Angeles",
            "departure_date": "2025-12-09"
        }
    },
    "conversation_state": "ready_for_action"
}
```

---

## Turno 4 (Continuación): Ejecutar Acción de Búsqueda

### 1. Nodo: execute_action_node()

**Ubicación**: `src/soni/dm/nodes/execute_action.py:11`

**Proceso**:

1. **Obtener paso actual**:
   ```python
   current_step_config = step_manager.get_current_step_config(state, runtime.context)
   # current_step_config = StepConfig(
   #     step="search_flights",
   #     type="action",
   #     call="search_available_flights"
   # )
   ```

2. **Obtener inputs de la acción**:
   ```python
   flow_slots = state["flow_slots"][active_ctx["flow_id"]]
   # flow_slots = {
   #     "origin": "New York",
   #     "destination": "Los Angeles",
   #     "departure_date": "2025-12-09"
   # }
   ```

3. **Ejecutar acción**:
   ```python
   action_result = await action_handler.execute(
       action_name="search_available_flights",
       inputs=flow_slots
   )
   # action_result = {
   #     "flights": [
   #         {"id": "AA123", "price": 299.99, ...},
   #         {"id": "UA456", "price": 349.99, ...}
   #     ],
   #     "price": 299.99
   # }
   ```

4. **Mapear outputs**:
   ```python
   # Según YAML: map_outputs: {flights: flights, price: price}
   mapped_slots = {
       "flights": action_result["flights"],
       "price": action_result["price"]
   }
   set_all_slots(state, mapped_slots)
   ```

5. **Avanzar al siguiente paso**:
   ```python
   step_updates = step_manager.advance_to_next_step(state, runtime.context)
   # step_updates = {
   #     "conversation_state": "ready_for_action",  # Siguiente paso es "action"
   #     "flow_stack": [{
   #         "current_step": "confirm_booking"
   #     }]
   # }
   ```

6. **Retorno**:
   ```python
   return {
       "action_result": action_result,
       "flow_slots": state["flow_slots"],
       **step_updates
   }
   ```

### 2. Routing: route_after_validate (después de execute_action)

**Grafo**: `src/soni/dm/builder.py:665`
```python
builder.add_edge("execute_action", "generate_response")
```

**Nota**: Después de ejecutar una acción, el grafo va directamente a `generate_response` para mostrar resultados.

### 3. Nodo: generate_response_node()

**Proceso**:

1. **Generar respuesta**:
   ```python
   # El nodo genera una respuesta basada en los resultados de la acción
   response = "I found 2 flights available. The cheapest is $299.99. Would you like to confirm?"
   ```

2. **Retorno**:
   ```python
   return {
       "last_response": response,
       "conversation_state": "ready_for_action"  # Listo para confirmar
   }
   ```

### 4. Respuesta al Usuario

```
"I found 2 flights available. The cheapest is $299.99. Would you like to confirm?"
```

**Nota**: El grafo no está interrumpido, así que el siguiente mensaje del usuario iniciará un nuevo turno.

---

## Turno 5: Confirmar Reserva

### Mensaje del Usuario
```
"Yes, please confirm"
```

### 1. understand_node()

**NLU Result** (asumido):
```python
{
    "command": "book_flight",
    "message_type": "confirmation",
    "slots": [],
    "confidence": 0.95
}
```

### 2. Routing: route_after_understand()

```python
match message_type:
    case "confirmation":
        return "handle_confirmation"
```

### 3. Nodo: handle_confirmation_node()

**Proceso**:

1. **Verificar paso actual**:
   ```python
   current_step_config = step_manager.get_current_step_config(state, runtime.context)
   # current_step_config = StepConfig(
   #     step="confirm_booking",
   #     type="action",
   #     call="confirm_flight_booking"
   # )
   ```

2. **Ejecutar acción de confirmación**:
   ```python
   action_result = await action_handler.execute(
       action_name="confirm_flight_booking",
       inputs={
           "flights": state["flow_slots"][flow_id]["flights"],
           "origin": "New York",
           "destination": "Los Angeles",
           "departure_date": "2025-12-09"
       }
   )
   # action_result = {
   #     "booking_ref": "BK123456",
   #     "confirmation": "Your flight has been confirmed!"
   # }
   ```

3. **Avanzar al siguiente paso**:
   ```python
   step_updates = step_manager.advance_to_next_step(state, runtime.context)
   # step_updates = {
   #     "conversation_state": "completed",  # No hay más pasos
   #     "flow_stack": [{
   #         "current_step": None  # Flujo completado
   #     }]
   # }
   ```

### 4. generate_response_node()

```python
response = f"Your booking is confirmed! Reference: BK123456. {action_result['confirmation']}"
return {
    "last_response": response,
    "conversation_state": "completed"
}
```

### 5. Respuesta Final

```
"Your booking is confirmed! Reference: BK123456. Your flight has been confirmed!"
```

---

## Diagrama de Flujo Completo

```
┌─────────────────────────────────────────────────────────────────┐
│                    TURNO 1: "I want to book a flight"           │
└─────────────────────────────────────────────────────────────────┘
                              │
                              ▼
                    RuntimeLoop.process_message()
                              │
                              ▼
                    _execute_graph() (nuevo)
                              │
                              ▼
                    START → understand_node()
                              │
                    ┌─────────┴─────────┐
                    │                   │
              NLU detecta          NLU no detecta
              "book_flight"        comando
                    │                   │
                    ▼                   ▼
        handle_intent_change    generate_response
                    │
                    ▼
        push_flow("book_flight")
                    │
                    ▼
        advance_to_next_step()
        (current_step = "collect_origin")
                    │
                    ▼
        collect_next_slot_node()
                    │
                    ▼
        interrupt("Where would you like to fly from?")
                    │
                    ▼
        [GRAFO INTERRUMPIDO - Esperando respuesta]

┌─────────────────────────────────────────────────────────────────┐
│                    TURNO 2: "New York"                          │
└─────────────────────────────────────────────────────────────────┘
                              │
                              ▼
                    RuntimeLoop.process_message()
                              │
                              ▼
                    _execute_graph() (reanudar)
                              │
                              ▼
        Command(resume="New York")
                              │
                              ▼
        collect_next_slot_node() (reanudado)
        interrupt() retorna "New York"
                              │
                              ▼
        collect_next_slot → understand_node()
                              │
                              ▼
        NLU extrae: origin="New York"
                              │
                              ▼
        validate_slot_node()
        - Normaliza "New York"
        - Valida con "city_name"
        - Guarda en flow_slots
        - advance_to_next_step()
        (current_step = "collect_destination")
                              │
                              ▼
        route_after_validate()
        (conversation_state = "waiting_for_slot")
                              │
                              ▼
        collect_next_slot_node()
        interrupt("Where would you like to fly to?")
                              │
                              ▼
        [GRAFO INTERRUMPIDO]

┌─────────────────────────────────────────────────────────────────┐
│                    TURNO 3: "Los Angeles"                       │
└─────────────────────────────────────────────────────────────────┘
                              │
                    [Flujo similar al Turno 2]
                              │
                    destination guardado
                              │
                    current_step = "collect_date"
                              │
                    Pregunta: "When would you like to depart?"

┌─────────────────────────────────────────────────────────────────┐
│                    TURNO 4: "Tomorrow"                           │
└─────────────────────────────────────────────────────────────────┘
                              │
                    understand_node()
                    NLU extrae: departure_date="Tomorrow"
                              │
                              ▼
                    validate_slot_node()
                    - Normaliza "Tomorrow" → "2025-12-09"
                    - Valida con "future_date_only"
                    - Guarda en flow_slots
                    - advance_to_next_step()
                    (current_step = "search_flights")
                              │
                              ▼
                    route_after_validate()
                    (conversation_state = "ready_for_action")
                              │
                              ▼
                    execute_action_node()
                    - Ejecuta search_available_flights
                    - Mapea outputs (flights, price)
                    - advance_to_next_step()
                    (current_step = "confirm_booking")
                              │
                              ▼
                    generate_response_node()
                    "I found 2 flights available..."

┌─────────────────────────────────────────────────────────────────┐
│                    TURNO 5: "Yes, please confirm"                │
└─────────────────────────────────────────────────────────────────┘
                              │
                    understand_node()
                    NLU detecta: message_type="confirmation"
                              │
                              ▼
                    handle_confirmation_node()
                    - Ejecuta confirm_flight_booking
                    - advance_to_next_step()
                    (current_step = None, flow completado)
                              │
                              ▼
                    generate_response_node()
                    "Your booking is confirmed! Reference: BK123456"
```

---

## Detalles Técnicos Clave

### 1. Patrón de Interrupt

El patrón `interrupt()` permite pausar la ejecución del grafo y esperar input del usuario:

```python
# En collect_next_slot_node()
user_response = interrupt(prompt)
```

**Comportamiento**:
- Primera ejecución: El grafo se pausa, `interrupt()` no retorna
- Reanudación: Con `Command(resume=msg)`, `interrupt()` retorna el mensaje
- El prompt se extrae de `result["__interrupt__"]` para mostrar al usuario

### 2. Progresión de Pasos

El `StepManager` gestiona la progresión secuencial:

```python
# Después de validar un slot
step_updates = step_manager.advance_to_next_step(state, context)
# Actualiza current_step en flow_stack
# Establece conversation_state según el tipo del siguiente paso
```

**Estados posibles**:
- `waiting_for_slot`: Siguiente paso es "collect"
- `ready_for_action`: Siguiente paso es "action"
- `ready_for_confirmation`: Siguiente paso es "confirm"
- `completed`: No hay más pasos

### 3. Routing Basado en Estado

Las funciones de routing (`route_after_understand`, `route_after_validate`) deciden el siguiente nodo basándose en:

- `message_type` del NLU (slot_value, intent_change, etc.)
- `conversation_state` (waiting_for_slot, ready_for_action, etc.)

### 4. Gestión de Slots

Los slots se almacenan en `flow_slots[flow_id]`:

```python
{
    "flow_slots": {
        "book_flight_a3f7b2c1": {
            "origin": "New York",
            "destination": "Los Angeles",
            "departure_date": "2025-12-09"
        }
    }
}
```

**Importante**: Se usa `flow_id` (instancia única) no `flow_name` (definición) para permitir múltiples instancias del mismo flujo.

### 5. Checkpointing

LangGraph guarda automáticamente el estado después de cada nodo:

```python
# En RuntimeLoop._load_or_create_state()
existing_state_snapshot = await self.graph.aget_state(config)
# Carga estado previo si existe
```

Esto permite:
- Reanudar conversaciones interrumpidas
- Mantener contexto entre turnos
- Soporte para múltiples usuarios simultáneos

---

## Conclusiones

1. **Flujo Secuencial**: El framework ejecuta los pasos del YAML en orden secuencial
2. **Interrupt Pattern**: Los pasos "collect" pausan el grafo esperando input del usuario
3. **NLU Siempre Primero**: Cada mensaje pasa por `understand_node` antes de cualquier procesamiento
4. **Routing Dinámico**: Las funciones de routing deciden el siguiente nodo basándose en el estado y el resultado NLU
5. **Estado Persistente**: El estado se guarda automáticamente entre turnos usando checkpointing
6. **Separación de Responsabilidades**: Cada componente tiene una responsabilidad única (SRP):
   - `FlowManager`: Gestión del stack de flujos
   - `StepManager`: Progresión de pasos
   - `ActionHandler`: Ejecución de acciones
   - `NLUProvider`: Comprensión de lenguaje natural

Este diseño permite un sistema de diálogo flexible, mantenible y escalable que sigue los principios SOLID y la arquitectura Zero-Leakage.
