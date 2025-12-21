# Análisis: Diseño vs Implementación

## Resumen Ejecutivo

**Problema Principal**: El sistema compila correctamente los pasos del YAML a nodos de LangGraph, pero **NO ejecuta los pasos secuencialmente** como especifica el diseño. En su lugar, usa un enfoque genérico de "preguntar por slots faltantes" que ignora la secuencia definida en el YAML.

## Comparación: Diseño vs Implementación

### 1. Ejecución Secuencial de Pasos

#### Diseño Esperado (05-message-flow.md:350-377)

```python
async def validate_slot_node(state: DialogueState) -> DialogueState:
    # ... validar slot ...

    # Check if we need more slots
    next_slot = get_next_required_slot(state)
    if next_slot:
        return {
            "conversation_state": ConversationState.WAITING_FOR_SLOT,
            "waiting_for_slot": next_slot,
            "last_response": get_slot_prompt(next_slot)
        }
    else:
        # All slots collected - check what's the next step in the flow
        next_step = get_next_step_in_flow(state)  # ✅ Debe obtener el siguiente paso del flujo

        if next_step and next_step.type == "confirm":
            return {
                "conversation_state": ConversationState.READY_FOR_CONFIRMATION,
                "current_step": next_step.name  # ✅ Actualiza current_step
            }
        elif next_step and next_step.type == "action":
            return {
                "conversation_state": ConversationState.READY_FOR_ACTION,
                "current_step": next_step.name  # ✅ Actualiza current_step
            }
```

**Puntos Clave del Diseño**:
- ✅ Debe obtener el siguiente paso del flujo: `get_next_step_in_flow(state)`
- ✅ Debe actualizar `current_step` al avanzar
- ✅ Debe verificar el tipo del siguiente paso (collect, action, confirm, etc.)

#### Implementación Actual (validate_slot.py)

```python
async def validate_slot_node(state: DialogueState, runtime: Any) -> dict:
    # ... validar slot ...

    # ❌ NO obtiene el siguiente paso del flujo
    # ❌ NO actualiza current_step
    # ❌ NO verifica qué tipo de paso sigue

    return {
        "flow_slots": flow_slots,
        "conversation_state": "validating_slot",
    }
```

**Problema**: El nodo valida el slot pero no avanza al siguiente paso del flujo.

### 2. Routing Después de Validar

#### Diseño Esperado (05-message-flow.md:301-311)

```python
def route_after_validate(state: DialogueState) -> str:
    """Route after slot validation"""
    conv_state = ConversationState(state["conversation_state"])

    if conv_state == ConversationState.READY_FOR_CONFIRMATION:
        return "confirm_action"
    elif conv_state == ConversationState.READY_FOR_ACTION:
        return "execute_action"  # ✅ Va a execute_action cuando está listo
    else:
        return "collect_next_slot"
```

**Puntos Clave del Diseño**:
- ✅ Usa `conversation_state` para determinar el siguiente nodo
- ✅ `READY_FOR_ACTION` → `execute_action`
- ✅ `READY_FOR_CONFIRMATION` → `confirm_action`
- ✅ Otros casos → `collect_next_slot`

#### Implementación Actual (routing.py:272-294)

```python
def route_after_validate(state: DialogueStateType) -> str:
    # Check if all required slots filled
    flow_stack = state.get("flow_stack", [])
    active_flow = flow_stack[-1] if flow_stack else None

    if not active_flow:
        return "generate_response"

    # TODO: Check slot requirements from flow definition
    # For now, simple logic
    if state.get("all_slots_filled"):  # ❌ Este flag nunca se establece
        return "execute_action"
    else:
        return "collect_next_slot"  # ❌ Siempre va aquí
```

**Problemas**:
1. ❌ No usa `conversation_state` como especifica el diseño
2. ❌ Depende de `all_slots_filled` que nunca se establece
3. ❌ No verifica qué tipo de paso sigue en el flujo
4. ❌ No considera si el siguiente paso es `action`, `confirm`, o `collect`

### 3. Rastreo de Pasos Actuales

#### Diseño Esperado (04-state-machine.md:121-125)

```python
current_step: str | None
"""
Identifier of current step in active flow.
None if no active flow or flow hasn't started execution.
"""
```

**Puntos Clave del Diseño**:
- ✅ `current_step` debe rastrear qué paso del flujo se está ejecutando
- ✅ Debe actualizarse cuando se avanza al siguiente paso
- ✅ Debe usarse para determinar qué paso ejecutar a continuación

#### Implementación Actual

**Observado en debug**:
```
Current Step: None  # ❌ Siempre es None
```

**Problema**: `current_step` nunca se actualiza, por lo que el sistema no sabe qué paso está ejecutando.

### 4. Collect Next Slot

#### Diseño Esperado (05-message-flow.md:656-690)

```python
async def collect_next_slot_node(state: DialogueState, context: RuntimeContext) -> DialogueState:
    """
    Ask for next slot and PAUSE execution.
    """
    next_slot = get_next_required_slot(state)  # ✅ Obtiene del flujo

    if next_slot:
        # Get current flow from stack
        active_ctx = context.flow_manager.get_active_context(state)
        current_flow_name = active_ctx["flow_name"] if active_ctx else "none"

        slot_config = get_slot_config(current_flow_name, next_slot)  # ✅ Obtiene del flujo

        # Pause here - wait for user input
        user_response = interrupt({
            "type": "slot_request",
            "slot": next_slot,
            "prompt": slot_config.prompt  # ✅ Usa prompt del slot
        })

        return {
            "user_message": user_response,
            "waiting_for_slot": next_slot,
            "conversation_state": ConversationState.WAITING_FOR_SLOT
        }

    return state
```

**Puntos Clave del Diseño**:
- ✅ Debe obtener el siguiente slot requerido del flujo
- ✅ Debe obtener la configuración del slot (incluyendo prompt)
- ✅ Debe usar `interrupt()` para pausar

#### Implementación Actual (collect_next_slot.py:11-59)

```python
async def collect_next_slot_node(state: DialogueState, runtime: Any) -> dict:
    # Get active flow
    flow_manager = runtime.context["flow_manager"]
    active_ctx = flow_manager.get_active_context(state)

    if not active_ctx:
        return {"conversation_state": "idle"}

    # Determine next slot to collect
    # TODO: Get from flow definition  # ❌ TODO no implementado
    next_slot = "origin"  # ❌ Placeholder hardcodeado

    # Generate prompt
    prompt = f"Please provide your {next_slot}."  # ❌ Prompt genérico

    # Pause here - wait for user response
    user_response = interrupt({
        "type": "slot_request",
        "slot": next_slot,
        "prompt": prompt,
    })

    return {
        "user_message": user_response,
        "waiting_for_slot": next_slot,
        "conversation_state": "waiting_for_slot",
        "last_response": prompt,
    }
```

**Problemas**:
1. ❌ `next_slot` está hardcodeado como "origin"
2. ❌ No obtiene el siguiente slot del flujo
3. ❌ No usa la configuración del slot (prompt, validators, etc.)
4. ❌ No rastrea qué paso del flujo está ejecutando

### 5. Compilación del Flujo

#### Diseño Esperado

El diseño especifica que debe existir un compilador que:
1. Parsea los pasos del YAML
2. Crea un DAG (Directed Acyclic Graph) intermedio
3. Convierte el DAG a nodos de LangGraph
4. Cada paso del YAML se convierte en un nodo específico

#### Implementación Actual

✅ **EXISTE Y FUNCIONA**:
- `FlowCompiler` compila YAML → DAG
- `StepCompiler` convierte DAG → StateGraph
- `SoniGraphBuilder` construye el grafo con RuntimeContext
- `RuntimeLoop` usa `build_manual()` que compila el flujo

**PERO**:
- ❌ Los nodos compilados no rastrean `current_step`
- ❌ Los nodos no avanzan al siguiente paso después de completar uno
- ❌ El routing no usa la información del flujo compilado

## Causa Raíz

El problema es una **desconexión entre la compilación y la ejecución**:

1. **Compilación**: ✅ Funciona correctamente - crea nodos desde el YAML
2. **Ejecución**: ❌ No usa la información del flujo compilado
   - No rastrea `current_step`
   - No avanza secuencialmente por los pasos
   - Usa lógica genérica en lugar de seguir la secuencia del YAML

## Lo Que Falta Implementar

### 1. Rastreo de `current_step`

Necesita:
- Actualizar `current_step` cuando se inicia un flujo
- Actualizar `current_step` cuando se completa un paso
- Usar `current_step` para determinar el siguiente paso

### 2. Función `get_next_step_in_flow(state)`

Necesita:
- Obtener el flujo actual desde `flow_stack`
- Obtener la lista de pasos del flujo desde la configuración
- Encontrar el paso actual usando `current_step`
- Retornar el siguiente paso en la secuencia

### 3. Actualización de `validate_slot_node`

Necesita:
- Después de validar un slot, verificar si hay más slots en el paso actual
- Si no hay más slots, obtener el siguiente paso del flujo
- Actualizar `current_step` y `conversation_state` según el tipo de paso

### 4. Actualización de `route_after_validate`

Necesita:
- Usar `conversation_state` en lugar de `all_slots_filled`
- Verificar el tipo del siguiente paso para routing correcto
- Considerar si el siguiente paso es `action`, `confirm`, o `collect`

### 5. Implementación de `collect_next_slot_node`

Necesita:
- Obtener el siguiente slot requerido del paso actual
- Si no hay más slots en el paso actual, avanzar al siguiente paso
- Usar la configuración del slot (prompt, validators, etc.)

## Conclusión

**El diseño es correcto**, pero la implementación está **incompleta**. El sistema compila correctamente los pasos del YAML, pero no ejecuta la secuencia como especifica el diseño. La solución requiere:

1. Implementar el rastreo de `current_step`
2. Implementar `get_next_step_in_flow()`
3. Actualizar los nodos para avanzar secuencialmente
4. Actualizar el routing para usar la información del flujo
