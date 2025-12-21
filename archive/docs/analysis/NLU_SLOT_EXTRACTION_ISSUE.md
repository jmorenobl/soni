# Análisis: Problema de Extracción de Slots en NLU

## Problema Identificado

Cuando el usuario responde con un valor directo (ej: "Madrid" cuando se espera el slot `origin`), el NLU:
1. ✅ Clasifica correctamente el mensaje como `message_type: slot_value`
2. ❌ **NO extrae el slot** - retorna `slots: []` (lista vacía)
3. ❌ Esto causa un bucle infinito porque `validate_slot` no puede procesar sin slots

## Flujo Actual (Problemático)

```
User: "Madrid"
  ↓
understand_node:
  - Recibe: waiting_for_slot="origin", expected_slots=["origin", "destination", ...]
  - Construye DialogueContext con current_prompted_slot="origin"
  - Llama a NLU con contexto completo
  ↓
NLU (SoniDU):
  - Retorna: message_type="slot_value", command="provide_location", slots=[]
  ↓
validate_slot_node:
  - Detecta que no hay slots
  - Retorna: conversation_state="idle", last_response="I didn't understand..."
  ↓
generate_response_node:
  - Retorna: conversation_state="idle"
  ↓
[LOOP] - El sistema vuelve a collect_next_slot → understand → ...
```

## Análisis del Diseño

### Según `docs/design/05-message-flow.md`:

El diseño especifica que `validate_slot_node` espera:
```python
nlu_result = state["nlu_result"]
slot_name = state["waiting_for_slot"]
value = nlu_result.slot_value  # ← Espera slot_value directo
```

Pero la implementación actual usa:
```python
slots = nlu_result.get("slots", [])  # ← Lista de SlotValue
```

### Según `docs/design/06-nlu-system.md`:

El NLU debería:
1. **Usar `current_prompted_slot`** para priorizar la extracción
2. **Extraer slots de `expected_slots`** que coincidan con el mensaje
3. **Retornar lista de `SlotValue`** con `name`, `value`, `confidence`, `action`

### Manejo de Casos Sin Slots

El diseño menciona:
- **Confidence thresholds**: Si confianza < 0.4, pedir clarificación
- **Fallback mechanisms**: Retornar resultado de fallback cuando hay errores
- **Clarification**: Si el usuario pregunta algo, tratar como digresión/clarificación

**PERO**: No especifica explícitamente qué hacer cuando:
- `message_type = slot_value`
- `slots = []` (lista vacía)
- `waiting_for_slot` está definido

## Problemas Identificados

### 1. Prompt del NLU No Es Suficientemente Claro

El `DialogueUnderstanding` signature dice:
```
"context: DialogueContext = dspy.InputField(
    desc="Dialogue state: current_flow, expected_slots (use these EXACT names), "
    "current_slots (already filled - check for corrections), current_prompted_slot, available_flows"
)"
```

Pero no instruye explícitamente:
- "Si `current_prompted_slot` está presente, el mensaje del usuario DEBE ser un valor para ese slot"
- "Extrae el valor del mensaje y asócialo al slot `current_prompted_slot`"

### 2. Falta de Manejo Explícito en `validate_slot`

La implementación actual maneja el caso de "no slots" pero:
- Retorna `idle` que causa routing a `generate_response`
- No diferencia entre "NLU no entendió" vs "NLU no pudo extraer"

### 3. No Hay Clarificación Automática

Según el diseño, cuando la confianza es baja (< 0.4), debería:
- Pedir clarificación
- Mostrar opciones
- Usar fallback

Pero esto no se está aplicando cuando `slots = []` con `message_type = slot_value`.

## Soluciones Propuestas

### Solución 1: Mejorar el Prompt del NLU

Modificar `DialogueUnderstanding` signature para ser más explícito:

```python
class DialogueUnderstanding(dspy.Signature):
    """Analyze user message in dialogue context to determine intent and extract all slot values.

    CRITICAL: If current_prompted_slot is provided, the user's message is likely a direct
    answer to that prompt. Extract the value and associate it with current_prompted_slot.

    Example:
    - current_prompted_slot="origin", user_message="Madrid"
    - → Extract: SlotValue(name="origin", value="Madrid", action="provide")
    """

    user_message: str = dspy.InputField(desc="The user's message to analyze")
    history: dspy.History = dspy.InputField(desc="Conversation history")
    context: DialogueContext = dspy.InputField(
        desc="Dialogue state: current_flow, expected_slots (use these EXACT names), "
        "current_slots (already filled - check for corrections), "
        "current_prompted_slot (CRITICAL: if present, user message is answer to this slot), "
        "available_flows"
    )
    current_datetime: str = dspy.InputField(
        desc="Current datetime in ISO format for relative date resolution",
        default="",
    )

    result: NLUOutput = dspy.OutputField(
        desc="Analysis with message_type, command, and all extracted slots (list) with their actions. "
        "MUST extract at least one slot if current_prompted_slot is provided and message_type is slot_value."
    )
```

### Solución 2: Fallback en `validate_slot` Cuando No Hay Slots

Mejorar el manejo cuando `slots = []` pero `message_type = slot_value`:

```python
if not slots:
    message_type = nlu_result.get("message_type", "")
    waiting_for_slot = state.get("waiting_for_slot")

    if message_type == "slot_value" and waiting_for_slot:
        # NLU clasificó como slot_value pero no extrajo el slot
        # Esto puede ser porque:
        # 1. El valor no es reconocible (ej: "xyz123")
        # 2. El NLU necesita mejor contexto
        # 3. El prompt no fue suficientemente claro

        # FALLBACK: Intentar extraer manualmente usando el valor crudo
        user_message = state.get("user_message", "")
        if user_message and user_message.strip():
            # Asumir que el mensaje completo es el valor del slot
            logger.warning(
                f"NLU didn't extract slot '{waiting_for_slot}' from message '{user_message}'. "
                f"Using fallback: treating entire message as slot value."
            )

            # Crear SlotValue manualmente
            slot = {
                "name": waiting_for_slot,
                "value": user_message.strip(),
                "confidence": 0.5,  # Baja confianza - necesita validación
                "action": "provide"
            }
            slots = [slot]

            # Continuar con validación normal
            # (el código después procesará este slot)
        else:
            # No hay mensaje - error
            return {"conversation_state": "error"}
    else:
        # No es slot_value o no hay waiting_for_slot
        # Manejar como antes...
```

### Solución 3: Usar Confidence para Decidir

Si el NLU retorna `confidence < 0.4` y `slots = []`:
- Tratar como clarificación
- Preguntar al usuario: "I didn't understand. Could you rephrase?"

### Solución 4: Mejorar el Contexto del NLU

Asegurar que `expected_slots` siempre incluya el `waiting_for_slot`:

```python
# En understand_node, antes de construir DialogueContext:
if waiting_for_slot and waiting_for_slot not in expected_slots:
    expected_slots = [waiting_for_slot] + expected_slots
    logger.debug(f"Added waiting_for_slot '{waiting_for_slot}' to expected_slots")
```

## Recomendación

**Implementar Solución 1 + Solución 2**:

1. **Mejorar el prompt** para que el NLU entienda que `current_prompted_slot` es crítico
2. **Agregar fallback** en `validate_slot` para cuando el NLU no extrae pero el mensaje es claro
3. **Mantener el manejo actual** de retornar `idle` cuando no hay slots, pero solo después de intentar el fallback

Esto asegura:
- ✅ El NLU intenta extraer correctamente (mejor prompt)
- ✅ Si falla, hay un fallback que evita el bucle
- ✅ El usuario recibe feedback útil en lugar de un bucle infinito

## Próximos Pasos

1. ✅ Investigar por qué el NLU no extrae slots
2. ⏳ Mejorar el prompt del NLU
3. ⏳ Implementar fallback en `validate_slot`
4. ⏳ Agregar tests para este caso específico
5. ⏳ Documentar el comportamiento esperado
