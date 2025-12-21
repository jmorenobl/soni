# Análisis del Escenario 1: Simple Complete Flight Booking

## Problema Observado

En el **Turn 4**, después de que el usuario proporciona "Tomorrow":
- ✅ El sistema completa todos los slots (origin, destination, departure_date)
- ✅ Ejecuta las acciones y genera outputs (flights, price, booking_ref, confirmation)
- ❌ **PERO** luego pregunta de nuevo: "What is your departure date?"

## Análisis del Flujo

### Estructura del YAML
```yaml
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

### Problemas Identificados

#### 1. **`all_slots_filled` nunca se establece**

En `src/soni/dm/routing.py:272-294`:
```python
def route_after_validate(state: DialogueStateType) -> str:
    # TODO: Check slot requirements from flow definition
    # For now, simple logic
    if state.get("all_slots_filled"):  # ❌ Este flag nunca se establece
        return "execute_action"
    else:
        return "collect_next_slot"  # Siempre va aquí
```

**Consecuencia**: El sistema siempre va a `collect_next_slot` en lugar de `execute_action`, incluso cuando todos los slots están llenos.

#### 2. **`collect_next_slot` es un placeholder**

En `src/soni/dm/nodes/collect_next_slot.py:37-39`:
```python
# Determine next slot to collect
# TODO: Get from flow definition
next_slot = "origin"  # ❌ Placeholder hardcodeado
```

**Consecuencia**: Siempre pregunta por "origin", ignorando:
- Qué slots ya están llenos
- Qué paso del flujo debería ejecutarse
- La secuencia definida en el YAML

#### 3. **El flujo no sigue los pasos del YAML**

El sistema actual **NO** está ejecutando los pasos en secuencia:
- No rastrea `current_step` correctamente
- No avanza de `collect_origin` → `collect_destination` → `collect_date` → `search_flights` → `confirm_booking`
- En su lugar, usa un enfoque genérico de "preguntar por slots"

#### 4. **Las acciones se ejecutan pero el flujo no termina**

Cuando el usuario proporciona "Tomorrow":
1. El NLU extrae `departure_date: "2025-12-06"`
2. Se normaliza y guarda en `flow_slots`
3. Las acciones `search_available_flights` y `confirm_flight_booking` se ejecutan (probablemente porque el NLU las detecta o hay alguna lógica especial)
4. Los outputs se guardan en slots
5. **PERO** el sistema vuelve a `collect_next_slot` que pregunta por "origin" (o "departure_date" si hay alguna lógica que detecta que falta)

## Flujo Actual vs Esperado

### Flujo Actual (Lo que está pasando)
```
Turn 1: "I want to book a flight"
  → understand → handle_intent_change → push_flow("book_flight")
  → collect_next_slot → pregunta "origin"

Turn 2: "Madrid"
  → understand → validate_slot → collect_next_slot → pregunta "destination"

Turn 3: "Barcelona"
  → understand → validate_slot → collect_next_slot → pregunta "departure_date"

Turn 4: "Tomorrow"
  → understand → validate_slot → collect_next_slot → pregunta "departure_date" (❌ DEBERÍA TERMINAR)
```

### Flujo Esperado (Lo que debería pasar)
```
Turn 1: "I want to book a flight"
  → understand → handle_intent_change → push_flow("book_flight")
  → current_step = "collect_origin" → pregunta "origin"

Turn 2: "Madrid"
  → understand → validate_slot → current_step = "collect_destination" → pregunta "destination"

Turn 3: "Barcelona"
  → understand → validate_slot → current_step = "collect_date" → pregunta "departure_date"

Turn 4: "Tomorrow"
  → understand → validate_slot → current_step = "search_flights" → execute_action
  → current_step = "confirm_booking" → execute_action
  → pop_flow() → FINALIZAR
```

## Causa Raíz

El sistema actual **no implementa la ejecución de pasos secuenciales** del YAML. En su lugar:

1. Usa un enfoque genérico de "preguntar por slots faltantes"
2. No rastrea qué paso del flujo está ejecutando
3. No avanza al siguiente paso después de completar uno
4. No detecta cuando todos los pasos están completos

## Hallazgos del Debug Detallado

### Estado en Turn 4 (después de "Tomorrow")

```
Flow: book_flight (stack depth: 1)
Current Step: None                    ❌ No rastrea el paso actual
Conversation State: understanding
Waiting for Slot: None
Current Prompted Slot: None           ✅ No está pidiendo ningún slot
All Slots Filled: False               ❌ NUNCA se establece a True
Slots: {
  "origin": "Madrid",
  "destination": "Barcelona",
  "departure_date": "2025-12-06",
  "flights": [...],                    ✅ Acciones ejecutadas
  "price": 299.99,
  "booking_ref": "BK-AA123-2024-001",
  "confirmation": "..."
}
```

### Observaciones Clave

1. **Las acciones SÍ se ejecutan**: Los outputs (`flights`, `price`, `booking_ref`, `confirmation`) están en los slots, lo que significa que `search_available_flights` y `confirm_flight_booking` se ejecutaron.

2. **`all_slots_filled` nunca se establece**: Aunque todos los slots requeridos están llenos, el flag permanece en `False`.

3. **`current_step` siempre es `None`**: El sistema no está rastreando qué paso del flujo está ejecutando.

4. **`current_prompted_slot` es `None`**: No está pidiendo ningún slot, pero el agente pregunta "What is your departure date?" de nuevo.

5. **El flujo no termina**: Aunque las acciones se ejecutaron, el flujo no se marca como completado y no se hace `pop_flow()`.

## Hipótesis sobre Cómo Funciona Actualmente

El sistema parece tener una lógica especial que:
1. Detecta cuando todos los slots requeridos están llenos (probablemente en el NLU o en algún nodo)
2. Ejecuta las acciones automáticamente
3. Guarda los outputs en los slots
4. **PERO** no marca `all_slots_filled = True`
5. **Y** no avanza al siguiente paso o termina el flujo
6. En su lugar, vuelve a `collect_next_slot` que pregunta por un slot (probablemente el último que se pidió)

## Próximos Pasos para Debug

1. **Buscar dónde se ejecutan las acciones automáticamente**:
   - ¿En el nodo `understand`?
   - ¿En algún nodo especial?
   - ¿Hay alguna lógica que detecta slots completos y ejecuta acciones?

2. **Verificar `generate_response`**:
   - ¿Qué lógica usa para generar la respuesta?
   - ¿Por qué pregunta "What is your departure date?" cuando `current_prompted_slot` es `None`?

3. **Revisar el flujo del grafo**:
   - ¿Qué nodos se ejecutan después de `validate_slot`?
   - ¿Hay algún edge que va directamente a `execute_action` sin pasar por `route_after_validate`?
