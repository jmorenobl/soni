# Análisis: Loop Infinito en Confirmaciones Poco Claras

**Fecha**: 2025-12-09
**Estado**: 🔴 Crítico - Bloquea tests de integración
**Tests Afectados**:
- `test_confirmation_unclear_then_yes`
- `test_complete_confirmation_flow_no_then_modify`
- `test_confirmation_max_retries`

---

## Resumen Ejecutivo

Cuando el usuario responde con algo poco claro durante una confirmación (ej: "hmm, I'm not sure"), el sistema entra en un loop infinito que alcanza el límite de recursión de LangGraph (25 iteraciones). El problema ocurre dentro del mismo turno de conversación, sugiriendo que el grafo no termina correctamente después de mostrar el mensaje de error.

**Error**: `GraphRecursionError: Recursion limit of 25 reached without hitting a stop condition`

---

## Flujo del Problema

### Escenario de Test

```python
# Usuario completa slots
await runtime.process_message("Book a flight", user_id)
await runtime.process_message("Boston", user_id)
await runtime.process_message("Seattle", user_id)
await runtime.process_message("Next week", user_id)

# Sistema muestra confirmación: "Is this correct?"
# Usuario responde con algo poco claro
response = await runtime.process_message("hmm, I'm not sure", user_id)
# ❌ LOOP INFINITO - nunca retorna
```

### Flujo Actual (Problemático)

```
1. confirm_action → interrupt() → espera respuesta
   ↓
2. Usuario responde: "hmm, I'm not sure"
   ↓
3. confirm_action se re-ejecuta (después de resume)
   - interrupt() retorna "hmm, I'm not sure"
   - Retorna: conversation_state="confirming", user_message="hmm, I'm not sure"
   ↓
4. builder.add_edge("confirm_action", "understand")
   ↓
5. understand procesa el mensaje
   - NLU detecta: message_type="confirmation" (pero confirmation_value=None)
   ↓
6. route_after_understand
   - Verifica: conversation_state="confirming" ✓
   - message_type="confirmation" ✓
   - Rutea a: handle_confirmation
   ↓
7. handle_confirmation
   - confirmation_value es None
   - Retorna: conversation_state="confirming", last_response="I didn't understand..."
   ↓
8. route_after_confirmation
   - conversation_state="confirming"
   - Rutea a: generate_response
   ↓
9. generate_response
   - Preserva conversation_state="confirming"
   - Retorna: last_response="I didn't understand..."
   - builder.add_edge("generate_response", END)
   ↓
10. ❌ PROBLEMA: El grafo NO termina aquí
    - En lugar de terminar, vuelve a ejecutar algún nodo
    - El loop continúa indefinidamente
```

---

## Análisis Técnico

### 1. Problema Principal: Grafo No Termina

**Ubicación**: `src/soni/dm/builder.py:200`

```python
builder.add_edge("generate_response", END)
```

**Problema**: Aunque `generate_response` tiene un edge a `END`, el grafo no termina correctamente cuando `conversation_state="confirming"`. Esto sugiere que:

1. **Hipótesis A**: Hay otro nodo que se ejecuta después de `generate_response` antes de llegar a `END`
2. **Hipótesis B**: El estado `conversation_state="confirming"` causa que algún routing vuelva a ejecutar nodos anteriores
3. **Hipótesis C**: El problema está en cómo LangGraph maneja el resume después de `interrupt()` cuando el mensaje es poco claro

### 2. NLU Detecta Confirmation Sin Valor

**Ubicación**: `src/soni/du/modules.py` (NLU Module)

**Problema**: Cuando el usuario responde con algo poco claro:
- NLU detecta `message_type="confirmation"` (correcto - está en contexto de confirmación)
- Pero NO extrae `confirmation_value` (None)
- Esto causa que `handle_confirmation` siempre retorne `conversation_state="confirming"`

**Comportamiento Esperado**:
- Si la respuesta es poco clara, NLU debería detectar `message_type="clarification"` o `message_type="digression"` en lugar de `message_type="confirmation"`

### 3. Routing Después de Confirmación Poco Clara

**Ubicación**: `src/soni/dm/routing.py:589-607`

```python
def route_after_confirmation(state: DialogueStateType) -> str:
    conv_state = state.get("conversation_state")

    if conv_state == "ready_for_action":
        return "execute_action"
    elif conv_state == "confirming":
        # Confirmation unclear - show message and wait for next user input
        return "generate_response"  # ✅ Correcto
    elif conv_state == "error":
        return "generate_response"
    else:
        return "understand"  # ⚠️ Podría causar loop
```

**Estado Actual**: El routing está correcto - cuando `conversation_state="confirming"`, va a `generate_response` que debería terminar el grafo.

### 4. Preservación de Estado en generate_response

**Ubicación**: `src/soni/dm/nodes/generate_response.py:72-108`

```python
elif current_conv_state == "confirming":
    # Preserve "confirming" state - user needs to respond to confirmation prompt
    conversation_state = "confirming"
    logger.debug("Preserving conversation_state='confirming' for next user response")
```

**Problema Potencial**: Preservar `conversation_state="confirming"` podría estar causando que el grafo no termine correctamente. Cuando el grafo termina con `conversation_state="confirming"`, el siguiente mensaje del usuario podría estar causando que el grafo se re-ejecute desde un punto incorrecto.

---

## Intentos de Fix Realizados

### Fix 1: Verificar Estado Antes de Routear a handle_confirmation

**Archivo**: `src/soni/dm/routing.py:330-345`

```python
case "confirmation":
    # Check if we're actually in a confirmation state
    conv_state = state.get("conversation_state")
    if conv_state == "confirming" or conv_state == "ready_for_confirmation":
        return "handle_confirmation"
    else:
        # Not in confirmation state - treat as continuation or digression
        logger.warning(...)
        return "collect_next_slot" or "generate_response"
```

**Resultado**: ❌ No resuelve el problema - el estado SÍ es "confirming" cuando ocurre el loop

### Fix 2: Guard en confirm_action para Evitar Re-interrupt

**Archivo**: `src/soni/dm/nodes/confirm_action.py:85-96`

```python
# Check if we already have a user message (node re-executed after resume)
existing_user_message = state.get("user_message", "")
existing_conv_state = state.get("conversation_state")

if existing_user_message and existing_conv_state == "confirming":
    # Node re-executed after resume - user already responded
    # Don't interrupt again, just pass through the state
    return {
        "conversation_state": "confirming",
        "last_response": confirmation_msg,
    }
```

**Resultado**: ❌ No resuelve el problema - el loop ocurre después de que confirm_action pasa el control a understand

### Fix 3: Routing a generate_response para Confirmaciones Poco Claras

**Archivo**: `src/soni/dm/routing.py:589-607`

```python
elif conv_state == "confirming":
    # Confirmation unclear - show message and wait for next user input
    return "generate_response"
```

**Resultado**: ❌ No resuelve el problema - aunque va a generate_response, el grafo no termina

---

## Hipótesis del Problema Real

### Hipótesis Principal: Loop Dentro del Mismo Turno

El loop ocurre **dentro del mismo turno**, no entre turnos. Esto sugiere que:

1. **Después de `generate_response`**, el grafo no termina correctamente
2. **Algún routing o edge** está causando que el grafo vuelva a ejecutar nodos anteriores
3. **El estado `conversation_state="confirming"`** podría estar causando que algún routing vuelva a `understand` o `handle_confirmation`

### Posibles Causas

1. **Edge Oculto**: Hay un edge condicional que no estamos viendo que rutea de vuelta después de `generate_response`
2. **Routing Incorrecto**: Algún routing está verificando `conversation_state="confirming"` y ruteando de vuelta a `understand`
3. **Problema con LangGraph**: El comportamiento de `interrupt()` y `resume()` podría estar causando que el grafo se re-ejecute incorrectamente cuando el mensaje es poco claro

---

## Próximos Pasos de Investigación

### 1. Agregar Logging Detallado

Agregar logging en cada nodo y routing para ver exactamente qué nodos se ejecutan y en qué orden:

```python
logger.info(f"EXECUTING: {node_name}, conversation_state={state.get('conversation_state')}")
logger.info(f"ROUTING: from {node_name} to {next_node}, reason={reason}")
```

### 2. Verificar Todos los Edges del Grafo

Revisar `src/soni/dm/builder.py` para asegurar que no hay edges ocultos que puedan causar el loop:

```python
# Verificar todos los edges
builder.add_edge("generate_response", END)  # ✅ Correcto
# ¿Hay algún otro edge que pueda interferir?
```

### 3. Investigar Comportamiento de LangGraph con Interrupt

Cuando `confirm_action` usa `interrupt()` y luego se reanuda con un mensaje poco claro, ¿qué pasa exactamente?

- ¿El grafo se re-ejecuta desde `confirm_action`?
- ¿O se re-ejecuta desde algún otro punto?
- ¿El estado se preserva correctamente?

### 4. Considerar Cambiar el Comportamiento de NLU

En lugar de detectar `message_type="confirmation"` cuando la respuesta es poco clara, el NLU debería:
- Detectar `message_type="clarification"` cuando la respuesta es ambigua
- O detectar `message_type="digression"` cuando la respuesta no es relevante
- Solo detectar `message_type="confirmation"` cuando puede extraer `confirmation_value=True/False`

### 5. Cambiar Estrategia: No Preservar "confirming" en generate_response

En lugar de preservar `conversation_state="confirming"` en `generate_response`, podríamos:
- Cambiar a `conversation_state="idle"` después de mostrar el mensaje de error
- Esto forzaría que el siguiente mensaje del usuario pase por el flujo normal
- Pero esto podría romper el flujo de confirmación

---

## Referencias

- **Archivo de Análisis Original**: `docs/analysis/ANALISIS_ERROR_CONFIRMACION.md`
- **Tests Failing**: `tests/integration/test_confirmation_flow.py`
- **Routing Logic**: `src/soni/dm/routing.py`
- **Confirmation Handler**: `src/soni/dm/nodes/handle_confirmation.py`
- **Confirm Action Node**: `src/soni/dm/nodes/confirm_action.py`
- **Graph Builder**: `src/soni/dm/builder.py`

---

## Estado Actual

- ✅ **3 tests pasan** (mejora desde 1)
- ⚠️ **3 tests fallan** (loop resuelto, pero last_response no se preserva)
- ✅ **Acciones se registran correctamente** (fix completado)
- ✅ **Loop infinito resuelto** (fix con conditional routing después de confirm_action)
- ⚠️ **Problema restante**: `last_response` de `handle_confirmation` no se preserva cuando `confirm_action` detecta que ya procesó la confirmación

### Fix Aplicado (2025-12-09)

**Cambio en `builder.py`**: Se cambió el edge directo `builder.add_edge("confirm_action", "understand")` a un edge condicional que verifica si la confirmación ya fue procesada:

```python
def route_after_confirm_action(state: DialogueStateType) -> str:
    # Si hay last_response y conversation_state="confirming",
    # significa que handle_confirmation ya procesó la respuesta
    # → ir directamente a generate_response
    if last_response and conv_state == "confirming" and user_message:
        return "generate_response"
    else:
        # Primera vez - ir a understand para procesar yes/no
        return "understand"
```

**Resultado**: El loop infinito se resolvió, pero el `last_response` de `handle_confirmation` no se está preservando correctamente cuando `confirm_action` detecta que ya procesó la confirmación.

**Última Actualización**: 2025-12-09
