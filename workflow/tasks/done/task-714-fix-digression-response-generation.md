## Task: 714 - Fix Digression Response Generation

**ID de tarea:** 714
**Hito:** Fix Integration Test Failures - Logic Fixes
**Dependencias:** Ninguna
**Duración estimada:** 3-4 horas

### Objetivo

Corregir `handle_digression` para que incluya tanto la respuesta a la pregunta del usuario como el re-prompt del slot que estaba esperando.

### Contexto

**Problema identificado:**
- El test `test_digression_flow_with_mocked_nlu` falla: `assert ('question' in response or 'help' in response)`
- El test usa NLU mockeado, por lo que no es un problema del NLU
- Después de manejar una digresión, la respuesta debe incluir:
  1. La respuesta a la pregunta del usuario
  2. El re-prompt del slot que estaba esperando
- Actualmente, la respuesta no incluye el mensaje de digresión

**Referencias:**
- `docs/analysis/ANALISIS_TESTS_FALLIDOS.md` - Sección 2.2
- `tests/integration/test_dialogue_manager_with_mocked_nlu.py::test_digression_flow_with_mocked_nlu`
- `src/soni/dm/nodes/handle_digression.py` - Manejo de digresiones
- `src/soni/utils/response_generator.py` - Generación de respuestas

### Entregables

- [ ] El test `test_digression_flow_with_mocked_nlu` pasa sin errores
- [ ] `handle_digression` incluye la respuesta a la pregunta del usuario
- [ ] `handle_digression` incluye el re-prompt del slot esperado
- [ ] El `conversation_state` se preserva como `waiting_for_slot`
- [ ] El `waiting_for_slot` se preserva correctamente

### Implementación Detallada

#### Paso 1: Investigar el problema

**Archivo(s) a revisar:**
- `src/soni/dm/nodes/handle_digression.py`
- `src/soni/utils/response_generator.py`
- `src/soni/dm/nodes/generate_response.py`

**Acciones:**
1. Ejecutar el test fallido con debug
2. Verificar qué respuesta genera `handle_digression`
3. Verificar si incluye la respuesta de la digresión
4. Verificar si incluye el re-prompt

**Comando de debug:**
```bash
uv run pytest tests/integration/test_dialogue_manager_with_mocked_nlu.py::test_digression_flow_with_mocked_nlu -v --tb=long -s
```

#### Paso 2: Verificar handle_digression actual

**Archivo(s) a revisar:** `src/soni/dm/nodes/handle_digression.py`

**Verificaciones:**
- ¿Genera la respuesta a la pregunta del usuario?
- ¿Incluye el re-prompt del slot esperado?
- ¿Preserva `waiting_for_slot` y `conversation_state`?

**Código esperado:**

```python
async def handle_digression_node(
    state: DialogueState,
    runtime: NodeRuntime,
) -> dict:
    nlu_result = state.get("nlu_result", {})
    digression_handler = runtime.context["digression_handler"]

    # Obtener respuesta a la pregunta
    digression_response = await digression_handler.handle(
        state, nlu_result.get("message_type"), ...
    )

    # Obtener re-prompt del slot esperado
    waiting_for_slot = state.get("waiting_for_slot")
    if waiting_for_slot:
        slot_config = ...  # Obtener configuración del slot
        reprompt = slot_config.prompt
    else:
        reprompt = ""

    # Combinar respuesta de digresión + re-prompt
    full_response = f"{digression_response}\n\n{reprompt}"

    return {
        "last_response": full_response,
        "conversation_state": "waiting_for_slot",  # Preservar
        "waiting_for_slot": waiting_for_slot,  # Preservar
        # ... otros campos ...
    }
```

#### Paso 3: Corregir handle_digression

**Archivo(s) a modificar:** `src/soni/dm/nodes/handle_digression.py`

**Código específico:**

```python
async def handle_digression_node(
    state: DialogueState,
    runtime: NodeRuntime,
) -> dict:
    """
    Handle digression by answering question and re-prompting for slot.

    Must include:
    1. Answer to user's question (from digression_handler)
    2. Re-prompt for the slot that was being collected
    """
    nlu_result = state.get("nlu_result", {})
    digression_handler = runtime.context.get("digression_handler")
    config = runtime.context["config"]
    flow_manager = runtime.context["flow_manager"]

    # Get active flow context
    active_ctx = flow_manager.get_active_context(state)
    if not active_ctx:
        return {
            "conversation_state": "idle",
            "last_response": "How can I help you?",
        }

    # Get digression response
    message_type = nlu_result.get("message_type")
    user_message = state.get("user_message", "")

    if digression_handler:
        digression_response = await digression_handler.handle(
            state, message_type, user_message
        )
    else:
        # Fallback
        digression_response = "I understand your question. Let me help you with that."

    # Get re-prompt for waiting slot
    waiting_for_slot = state.get("waiting_for_slot")
    reprompt = ""

    if waiting_for_slot:
        # Get slot configuration
        slot_config = config.slots.get(waiting_for_slot)
        if slot_config:
            reprompt = slot_config.prompt
        else:
            # Fallback prompt
            reprompt = f"Now, {waiting_for_slot.replace('_', ' ')}?"

    # Combine digression response + re-prompt
    if reprompt:
        full_response = f"{digression_response}\n\n{reprompt}"
    else:
        full_response = digression_response

    return {
        "last_response": full_response,
        "conversation_state": "waiting_for_slot",  # Preserve
        "waiting_for_slot": waiting_for_slot,  # Preserve
        "user_message": "",  # Clear to prevent loops
        "nlu_result": {},  # Clear to prevent loops
    }
```

**Explicación:**
- Obtener respuesta de digresión del `digression_handler`
- Obtener re-prompt del slot esperado desde la configuración
- Combinar ambos en `last_response`
- Preservar `waiting_for_slot` y `conversation_state`

#### Paso 4: Verificar digression_handler

**Archivo(s) a verificar:** `src/soni/runtime/digression_handler.py` o similar

**Verificaciones:**
- ¿`digression_handler.handle()` genera respuestas apropiadas?
- ¿Maneja diferentes tipos de digresión (question, help, etc.)?

### Tests Requeridos

**Archivo de tests:** `tests/integration/test_dialogue_manager_with_mocked_nlu.py`

**Test existente que debe pasar:**
```python
async def test_digression_flow_with_mocked_nlu(...):
    # Este test ya existe y debe pasar después de la corrección
    # Verifica que la respuesta incluye tanto la digresión como el re-prompt
```

**Tests adicionales a considerar:**
```python
# Test: Digresión sin waiting_for_slot
async def test_digression_without_waiting_slot(...):
    """Test que digresión funciona cuando no hay slot esperando."""

# Test: Digresión con múltiples preguntas
async def test_digression_multiple_questions(...):
    """Test que digresión maneja múltiples preguntas correctamente."""
```

### Criterios de Éxito

- [ ] `test_digression_flow_with_mocked_nlu` pasa sin errores
- [ ] La respuesta incluye la respuesta a la pregunta del usuario
- [ ] La respuesta incluye el re-prompt del slot esperado
- [ ] `conversation_state` se preserva como `waiting_for_slot`
- [ ] `waiting_for_slot` se preserva correctamente
- [ ] Todos los tests de integración relacionados pasan
- [ ] Linting pasa sin errores
- [ ] Type checking pasa sin errores

### Validación Manual

**Comandos para validar:**

```bash
# Ejecutar test específico
uv run pytest tests/integration/test_dialogue_manager_with_mocked_nlu.py::test_digression_flow_with_mocked_nlu -v

# Ejecutar todos los tests de digresión
uv run pytest tests/integration/ -k digression -v

# Ejecutar suite completa de integración
uv run pytest tests/integration/ -v
```

**Resultado esperado:**
- La respuesta incluye la respuesta a la pregunta (ej: información sobre aeropuertos)
- La respuesta incluye el re-prompt (ej: "Where would you like to go?")
- El estado se preserva correctamente

### Referencias

- `docs/analysis/ANALISIS_TESTS_FALLIDOS.md` - Sección 2.2
- `tests/integration/test_dialogue_manager_with_mocked_nlu.py::test_digression_flow_with_mocked_nlu` - Test que debe pasar
- `src/soni/dm/nodes/handle_digression.py` - Implementación actual
- `src/soni/utils/response_generator.py` - Generación de respuestas
- `src/soni/runtime/digression_handler.py` - Manejo de digresiones

### Notas Adicionales

- Esta tarea es parte de la Fase 2 del plan de acción (corrección de lógica)
- El test usa NLU mockeado, por lo que no es un problema del NLU
- La respuesta debe combinar la digresión y el re-prompt
- Verificar que `digression_handler` genera respuestas apropiadas
- Verificar que el formato de la respuesta combinada es legible (usar `\n\n` para separar)
