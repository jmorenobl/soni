# Conversation States - Definición y Uso

**Fecha**: 2025-12-05
**Estado**: Alineado con diseño (docs/design/04-state-machine.md)

---

## Estados de Conversación

Los estados de conversación en Soni están completamente alineados con el diseño especificado. Cada estado tiene un propósito específico en el flujo de diálogo.

### Estados Core (Diseño Original)

| Estado | Descripción | Duración Típica | Transiciones |
|--------|-------------|-----------------|--------------|
| `idle` | Sin flujo activo, esperando mensaje del usuario | Hasta que el usuario envía mensaje | → `understanding` |
| `understanding` | Procesando intent del usuario vía NLU | 200-500ms | → `waiting_for_slot`, `executing_action`, `idle`, `error` |
| `waiting_for_slot` | Esperando valor de slot específico del usuario | Hasta que el usuario responde | → `understanding` (siempre vía NLU) |
| `validating_slot` | Validando valor proporcionado | 10-100ms | → `waiting_for_slot`, `confirming`, `executing_action` |
| `executing_action` | Ejecutando acción externa | 100ms-5s | → `completed`, `waiting_for_slot`, `error` |
| `confirming` | **Esperando respuesta de confirmación del usuario** | Hasta que confirma | → `understanding` |
| `completed` | Flujo terminado | Momentáneo | → `idle`, `understanding` |
| `error` | Error ocurrió | Hasta recuperación | → `idle`, `understanding` |

### Estados Intermedios (Extensiones del Diseño)

| Estado | Descripción | Uso | Siguiente Estado |
|--------|-------------|-----|------------------|
| `ready_for_action` | **Intermedio**: Listo para ejecutar acción | Después de validar último slot, antes de ejecutar | → `execute_action` nodo |
| `ready_for_confirmation` | **Intermedio**: Listo para pedir confirmación | Después de validar último slot, antes de confirmar | → `confirm_action` nodo (pendiente) |
| `collecting` | Colectando información (legacy) | Menos específico que `waiting_for_slot` | Usar `waiting_for_slot` preferentemente |
| `generating_response` | Generando respuesta final | Antes de END | → END |

---

## Diferencia Clave: `confirming` vs `ready_for_confirmation`

**Esta es la distinción crítica que alinea con el diseño:**

### `ready_for_confirmation` (Estado Intermedio)
- **Cuándo**: Después de `validate_slot` cuando el siguiente paso es `confirm`
- **Significado**: "El sistema está listo para PEDIR confirmación"
- **Acción siguiente**: Ir al nodo `confirm_action`
- **No espera input del usuario todavía**

```python
# En validate_slot_node, después de validar último slot
if next_step.type == "confirm":
    return {"conversation_state": "ready_for_confirmation"}
```

### `confirming` (Estado Activo)
- **Cuándo**: En el nodo `confirm_action`, DESPUÉS de hacer `interrupt()`
- **Significado**: "El sistema está ESPERANDO la respuesta de confirmación del usuario"
- **Acción siguiente**: Usuario responde → `understand_node` → routing según respuesta
- **Está esperando input del usuario**

```python
# En confirm_action_node
user_response = interrupt({
    "type": "confirmation_request",
    "prompt": "¿Es correcto?"
})

return {
    "conversation_state": "confirming",  # AHORA está esperando
    "last_response": "¿Es correcto?"
}
```

---

## Análogo: `ready_for_action` vs `executing_action`

La misma lógica se aplica a las acciones:

### `ready_for_action` (Estado Intermedio)
- **Cuándo**: Después de `validate_slot` cuando el siguiente paso es `action`
- **Significado**: "El sistema está listo para ejecutar la acción"
- **Acción siguiente**: Ir al nodo `execute_action`

### `executing_action` (Estado Activo)
- **Cuándo**: EN el nodo `execute_action`, mientras ejecuta
- **Significado**: "La acción se está ejecutando"
- **Acción siguiente**: Depende del resultado de la acción

---

## Flujo Completo de Ejemplo

### Escenario: Reservar Vuelo con Confirmación

```
1. [idle] → Usuario: "Quiero reservar un vuelo"

2. [understanding] → NLU clasifica: new_intent="book_flight"
   → push_flow("book_flight")
   → current_step = "collect_origin" (tipo: collect)

3. [waiting_for_slot] → Sistema: "¿De dónde sales?"
   → interrupt() (esperando respuesta)

4. [understanding] → Usuario: "Madrid"
   → NLU clasifica: slot_value

5. [validating_slot] → Normaliza "Madrid" → "MAD"
   → Verifica si paso completo
   → Sí está completo → advance_to_next_step()
   → next_step = "collect_destination" (tipo: collect)

6. [waiting_for_slot] → Sistema: "¿A dónde vas?"
   → interrupt() (esperando respuesta)

7. [understanding] → Usuario: "Barcelona"

8. [validating_slot] → Normaliza "Barcelona" → "BCN"
   → Verifica si paso completo
   → Sí está completo → advance_to_next_step()
   → next_step = "confirm_booking" (tipo: confirm)

9. [ready_for_confirmation] ← ESTADO INTERMEDIO
   → Routing: route_after_validate() → "confirm_action"

10. (Nodo confirm_action - cuando se implemente)
    → Muestra: "Origen: MAD, Destino: BCN. ¿Correcto?"
    → interrupt() (esperando confirmación)
    → Estado cambia a [confirming] ← ESTADO ACTIVO

11. [understanding] → Usuario: "Sí"
    → NLU clasifica: confirmation=yes

12. [ready_for_action] ← ESTADO INTERMEDIO
    → Routing → "execute_action"

13. [executing_action] ← ESTADO ACTIVO
    → Ejecuta: search_flights(origin="MAD", destination="BCN")
    → advance_to_next_step()
    → No hay más pasos

14. [completed] → Flujo terminado
    → pop_flow()

15. [idle] → Esperando nuevo mensaje
```

---

## Estados en Código

### src/soni/core/types.py
```python
ConversationState = Literal[
    "idle",                      # ✅ Diseño original
    "understanding",             # ✅ Diseño original
    "waiting_for_slot",          # ✅ Diseño original
    "validating_slot",           # ✅ Diseño original
    "collecting",                # ⚠️  Legacy (usar waiting_for_slot)
    "ready_for_action",          # ✅ Intermedio (diseño)
    "ready_for_confirmation",    # ✅ Intermedio (diseño)
    "confirming",                # ✅ Activo (diseño original)
    "executing_action",          # ✅ Diseño original
    "completed",                 # ✅ Diseño original
    "generating_response",       # ✅ Antes de END
    "error",                     # ✅ Diseño original
]
```

### src/soni/flow/step_manager.py

```python
def advance_to_next_step(self, state, context):
    """Avanza al siguiente paso y establece conversation_state apropiado."""
    next_step = self.get_next_step_config(state, context)

    if not next_step:
        return {"conversation_state": "completed"}

    # Mapeo tipo de paso → estado intermedio
    step_type_to_state = {
        "action": "ready_for_action",           # Intermedio antes de ejecutar
        "collect": "waiting_for_slot",          # Activo esperando input
        "confirm": "ready_for_confirmation",    # Intermedio antes de confirmar
        "branch": "understanding",              # Evaluación de lógica
        "say": "generating_response",           # Solo mostrar mensaje
    }

    conversation_state = step_type_to_state.get(step_type, "waiting_for_slot")

    return {
        "flow_stack": flow_stack,
        "conversation_state": conversation_state,
    }
```

---

## Validación de Transiciones

Según `docs/design/04-state-machine.md`, las transiciones válidas son:

```python
VALID_TRANSITIONS = {
    "idle": ["understanding"],
    "understanding": ["waiting_for_slot", "executing_action", "idle", "error"],
    "waiting_for_slot": ["understanding"],  # Siempre vía NLU
    "validating_slot": ["waiting_for_slot", "confirming", "executing_action"],
    "executing_action": ["confirming", "completed", "waiting_for_slot", "error"],
    "confirming": ["understanding", "executing_action", "waiting_for_slot"],
    "completed": ["idle", "understanding"],
    "error": ["idle", "understanding"],
}
```

**Nota**: Los estados intermedios (`ready_for_action`, `ready_for_confirmation`) no tienen transiciones validadas porque son momentáneos - se establecen y se consumen inmediatamente en el routing.

---

## Resumen

✅ **Total alineación con el diseño**:
- Estados core del diseño: implementados
- Estados intermedios del diseño: implementados
- Distinción clara entre "ready_for" (intermedio) y estados activos
- `confirming` agregado para esperar respuesta de confirmación del usuario

⚠️ **Pendiente**:
- Implementar nodo `confirm_action` que use el estado `confirming`
- Deprecar `collecting` en favor de `waiting_for_slot`

---

**Última actualización**: 2025-12-05
**Estado**: ✅ Alineado con diseño
