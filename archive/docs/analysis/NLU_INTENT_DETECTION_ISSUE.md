# Análisis: Problema de Detección de Intent en Tests E2E

## Problema Identificado

Cuando se ejecutan los tests de integración en conjunto, 29 tests fallan. El problema principal es que el NLU está clasificando "I want to book a flight" como `continuation` con `command: None` en lugar de `INTERRUPTION` con `command: "book_flight"`.

## Análisis

### Comportamiento Esperado

Cuando el usuario dice "I want to book a flight" y no hay flow activo:
- **message_type**: `INTERRUPTION`
- **command**: `"book_flight"`
- **slots**: `[]`

### Comportamiento Actual en Tests E2E

- **message_type**: `continuation`
- **command**: `None`
- **slots**: `[]`

### Comportamiento en Tests Aislados

Cuando se prueba el NLU directamente con el mismo contexto, funciona correctamente:
- **message_type**: `INTERRUPTION`
- **command**: `"book_flight"`
- **slots**: `[]`

## Causa Raíz

El problema está en el **two-stage prediction** en `understand_node`:

1. Cuando `current_flow_name == "none"` y no hay `expected_slots`, se usa two-stage prediction
2. En la primera etapa, se llama al NLU con `expected_slots=[]` para detectar solo el comando
3. El NLU puede devolver `continuation` con `command: None` si no detecta el comando claramente
4. Si `command` es `None` o vacío, el código usa `intent_result` tal cual (línea 155), que puede ser `continuation`

### Código Problemático

```python
# src/soni/dm/nodes/understand.py:153-155
else:
    # No command detected - use intent_result as-is
    nlu_result = intent_result
```

Si `intent_result` tiene `message_type: continuation` y `command: None`, el sistema no activa ningún flow y simplemente genera una respuesta genérica.

## Solución Propuesta

### Opción 1: Mejorar el Signature del NLU (Ya implementado)

Se mejoró el signature para ser más explícito sobre cuándo usar `INTERRUPTION`:

```python
CANCELLATION vs INTERRUPTION:
- INTERRUPTION: User wants to start a flow that exists in available_flows
  * When current_flow="none" and user mentions a flow from available_flows → INTERRUPTION
  * Set command to the flow name from available_flows (e.g., "book_flight")
```

### Opción 2: Mejorar el Two-Stage Prediction

Si el NLU no detecta un comando en la primera etapa, en lugar de usar `intent_result` tal cual, se podría:

1. Verificar si el mensaje del usuario menciona algún flow de `available_flows`
2. Si es así, forzar `INTERRUPTION` con el comando correspondiente
3. O hacer un fallback a single-stage prediction con todos los `expected_slots` combinados

### Opción 3: Eliminar Two-Stage Prediction

Si el two-stage prediction está causando más problemas que beneficios, se podría eliminar y usar siempre single-stage prediction con `expected_slots` combinados de todos los flows disponibles.

## Próximos Pasos

1. ✅ Mejorar el signature del NLU (completado)
2. ⏳ Ejecutar tests de integración para ver si la mejora del signature ayuda
3. ⏳ Si no ayuda, implementar Opción 2 o 3
4. ⏳ Verificar que los tests aislados del NLU sigan pasando

## Referencias

- `src/soni/dm/nodes/understand.py:69-155` - Two-stage prediction logic
- `src/soni/du/signatures.py` - NLU signature definition
- `tests/integration/test_e2e.py:76-118` - Failing test
