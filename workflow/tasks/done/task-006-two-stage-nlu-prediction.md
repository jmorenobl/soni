## Task: 006 - Implement Two-Stage NLU Prediction for Scalability

**ID de tarea:** 006
**Hito:** 10
**Dependencias:** Ninguna (puede hacerse después de las tareas de design compliance)
**Duración estimada:** 6-8 horas

### Objetivo

Implementar un enfoque de dos pasos en `understand_node` para detectar el comando/intent primero y luego extraer slots con los `expected_slots` correctos del flow detectado. Esto resuelve el problema de escalabilidad cuando hay muchos flows disponibles, evitando pasar todos los `expected_slots` combinados al NLU.

### Contexto

**Problema actual:**
La solución implementada en `task-001` combina todos los `expected_slots` de todos los `available_flows` cuando no hay flow activo. Esto funciona para casos simples pero no escala:

- Si hay 10 flows con 5 slots cada uno → `expected_slots` tendría 50 slots
- El LLM puede confundirse o extraer slots incorrectos de otros flows
- No es eficiente ni preciso con muchos flows

**Análisis:**
- El NLU necesita `expected_slots` para extraer slots (restricción: "Slot name must match expected_slots")
- Cuando no hay flow activo, no sabemos qué slots buscar
- La solución actual combina todos los slots de todos los flows (no escala)

**Solución propuesta:**
Implementar un enfoque de dos pasos en `understand_node`:
1. **Paso 1**: Detectar comando/intent con `expected_slots=[]`
2. **Paso 2**: Si se detecta un comando válido, mapear a flow y re-predecir con `expected_slots` del flow detectado

**Por qué en `understand_node`:**
- Ya tiene acceso a `config` y `scope_manager`
- No requiere cambios en la interfaz de `SoniDU`
- Mantiene la lógica de routing donde corresponde
- Es más simple y directo

**Referencias:**
- Análisis: `docs/analysis/NLU_CONTEXT_IMPROVEMENT.md`
- Código actual: `src/soni/dm/nodes/understand.py` (líneas 50-69)
- Routing: `src/soni/dm/routing.py` - `activate_flow_by_intent()`
- Scope: `src/soni/core/scope.py` - `get_expected_slots()`

### Entregables

- [ ] `understand_node` implementa enfoque de dos pasos cuando no hay flow activo
- [ ] Paso 1: Detecta comando con `expected_slots=[]`
- [ ] Paso 2: Mapea comando a flow y re-predice con `expected_slots` correctos
- [ ] Maneja casos edge: comando no válido, múltiples flows posibles
- [ ] Tests para validar el comportamiento de dos pasos
- [ ] Documentación del enfoque en código

### Implementación Detallada

#### Paso 1: Detectar comando/intent primero

**Archivo(s) a modificar:** `src/soni/dm/nodes/understand.py`

**Código específico:**

```python
# En understand_node, después de construir el contexto inicial
if current_flow_name == "none" and not expected_slots and available_flows:
    logger.debug(
        "No active flow and no expected_slots - using two-stage prediction: "
        "first detect command, then extract slots"
    )

    # Stage 1: Detect command/intent only (no slots needed)
    intent_context = DialogueContext(
        current_slots=(state["flow_slots"].get(active_ctx["flow_id"], {}) if active_ctx else {}),
        available_actions=available_actions,
        available_flows=available_flows,
        current_flow="none",
        expected_slots=[],  # Empty - just detect intent
        current_prompted_slot=waiting_for_slot,
    )

    # First NLU call: detect command only
    intent_result_raw = await nlu_provider.predict(
        state["user_message"],
        history,
        intent_context,
    )
    intent_result = intent_result_raw.model_dump(mode="json")

    # Extract command from first prediction
    command = intent_result.get("command")

    # Stage 2: If command detected, map to flow and re-predict with correct expected_slots
    if command:
        # Map command to flow using existing routing logic
        from soni.dm.routing import activate_flow_by_intent

        detected_flow = activate_flow_by_intent(
            command=command,
            current_flow="none",
            config=runtime.context["config"]
        )

        if detected_flow != "none":
            # Get expected_slots for detected flow
            detected_expected_slots = scope_manager.get_expected_slots(
                flow_name=detected_flow,
                available_actions=available_actions,
            )

            logger.debug(
                f"Two-stage NLU: detected command '{command}' -> flow '{detected_flow}', "
                f"expected_slots={detected_expected_slots}"
            )

            # Stage 2: Re-predict with correct expected_slots
            slot_context = DialogueContext(
                current_slots=(state["flow_slots"].get(active_ctx["flow_id"], {}) if active_ctx else {}),
                available_actions=available_actions,
                available_flows=available_flows,
                expected_slots=detected_expected_slots,  # Now we have the right slots!
                current_flow=detected_flow,
                current_prompted_slot=waiting_for_slot,
            )

            # Second NLU call: extract slots with correct expected_slots
            final_result_raw = await nlu_provider.predict(
                state["user_message"],
                history,
                slot_context,
            )
            final_result = final_result_raw.model_dump(mode="json")

            # Use final_result (has both command and slots)
            nlu_result = final_result
        else:
            # Command detected but couldn't map to flow - use intent_result
            logger.warning(
                f"Command '{command}' detected but couldn't map to flow. "
                f"Available flows: {available_flows}"
            )
            nlu_result = intent_result
    else:
        # No command detected - use intent_result as-is
        nlu_result = intent_result
else:
    # Normal single-stage prediction (flow active or expected_slots provided)
    nlu_result_raw = await nlu_provider.predict(
        state["user_message"],
        history,
        dialogue_context,
    )
    nlu_result = nlu_result_raw.model_dump(mode="json")
```

**Explicación:**
- Solo aplica cuando `current_flow == "none"` y `expected_slots == []` y hay `available_flows`
- Primera llamada: detecta comando sin slots (más rápido, menos tokens)
- Segunda llamada: extrae slots con `expected_slots` correctos del flow detectado
- Si no se detecta comando o no se mapea a flow, usa el resultado de la primera llamada
- Mantiene compatibilidad: si hay flow activo o `expected_slots` ya proporcionados, usa flujo normal

#### Paso 2: Optimizar caché para dos pasos

**Archivo(s) a modificar:** `src/soni/du/modules.py` (opcional, para optimización)

**Explicación:**
- El caché actual usa el contexto completo como clave
- Para el paso 1 (intent detection), podríamos usar una clave más simple
- Esto es opcional - el caché actual funcionará pero podría ser más eficiente

**Consideración:**
- Por ahora, dejamos el caché como está (funciona correctamente)
- Si hay problemas de rendimiento, optimizar después

#### Paso 3: Manejar edge cases

**Archivo(s) a modificar:** `src/soni/dm/nodes/understand.py`

**Edge cases a manejar:**

1. **Comando no válido o no mapeable:**
   - Usar resultado de primera llamada (puede tener slots genéricos)
   - Log warning para debugging

2. **Múltiples flows posibles:**
   - `activate_flow_by_intent` ya maneja esto (devuelve el mejor match)
   - Si hay ambigüedad, el sistema puede pedir clarificación después

3. **Usuario proporciona slots pero no comando claro:**
   - Primera llamada puede detectar slots genéricos
   - Segunda llamada puede no ejecutarse si no hay comando
   - Aceptable: el sistema puede inferir el flow después

4. **Performance:**
   - Dos llamadas al LLM cuando no hay flow activo
   - Trade-off aceptable: mejor precisión vs. latencia ligeramente mayor
   - Solo afecta el primer mensaje cuando no hay flow activo

### Tests Requeridos

**Archivo de tests:** `tests/integration/test_nlu_two_stage.py` (nuevo archivo)

**Tests específicos a implementar:**

```python
@pytest.mark.integration
@pytest.mark.asyncio
async def test_two_stage_prediction_without_active_flow(runtime, skip_without_api_key):
    """Test that two-stage prediction works when no flow is active."""
    user_id = "test-two-stage-001"
    await runtime._ensure_graph_initialized()

    # Act - User provides all slots at once without active flow
    response = await runtime.process_message(
        "I want to book a flight from NYC to LAX tomorrow", user_id
    )

    # Assert - System should extract all slots correctly
    # (This test should pass with two-stage approach)
    assert isinstance(response, str)
    assert len(response) > 0

    # Verify slots were extracted (check state if possible)
    # Or verify response indicates slots were understood

@pytest.mark.integration
@pytest.mark.asyncio
async def test_two_stage_with_invalid_command(runtime, skip_without_api_key):
    """Test that two-stage handles invalid commands gracefully."""
    user_id = "test-two-stage-002"
    await runtime._ensure_graph_initialized()

    # Act - User says something that doesn't map to a flow
    response = await runtime.process_message(
        "I want to do something weird that doesn't exist", user_id
    )

    # Assert - System should handle gracefully (not crash)
    assert isinstance(response, str)
    # Should either ask for clarification or indicate it doesn't understand

@pytest.mark.integration
@pytest.mark.asyncio
async def test_two_stage_skipped_when_flow_active(runtime, skip_without_api_key):
    """Test that two-stage is skipped when flow is already active."""
    user_id = "test-two-stage-003"
    await runtime._ensure_graph_initialized()

    # Arrange - Start a flow first
    await runtime.process_message("I want to book a flight", user_id)

    # Act - Provide slots (flow is now active)
    response = await runtime.process_message("from NYC to LAX", user_id)

    # Assert - Should use single-stage (flow is active)
    # Verify it works correctly (slots extracted)
    assert isinstance(response, str)
```

### Criterios de Éxito

- [ ] `test_two_stage_prediction_without_active_flow` pasa
- [ ] `test_two_stage_with_invalid_command` pasa
- [ ] `test_two_stage_skipped_when_flow_active` pasa
- [ ] Tests existentes siguen pasando (no regresiones)
- [ ] Linting pasa sin errores
- [ ] Type checking pasa sin errores
- [ ] Logs muestran claramente cuando se usa two-stage vs single-stage
- [ ] Performance aceptable (dos llamadas solo cuando necesario)

### Validación Manual

**Comandos para validar:**

```bash
# Ejecutar tests de two-stage
uv run pytest tests/integration/test_nlu_two_stage.py -v

# Ejecutar todos los tests de integración para verificar no hay regresiones
uv run pytest tests/integration/ -v

# Verificar logs para two-stage
uv run pytest tests/integration/test_nlu_two_stage.py -v -s --log-cli-level=DEBUG | grep -i "two-stage\|stage"
```

**Resultado esperado:**
- Tests pasan correctamente
- Logs muestran "using two-stage prediction" cuando corresponde
- Slots se extraen correctamente incluso con muchos flows disponibles
- No hay regresiones en tests existentes

### Referencias

- Análisis del problema: `docs/analysis/NLU_CONTEXT_IMPROVEMENT.md`
- Código actual: `src/soni/dm/nodes/understand.py`
- Routing logic: `src/soni/dm/routing.py` - `activate_flow_by_intent()`
- Scope manager: `src/soni/core/scope.py` - `get_expected_slots()`
- Diseño NLU: `docs/design/06-nlu-system.md`
- Diseño Message Flow: `docs/design/05-message-flow.md`

### Notas Adicionales

**Trade-offs:**
- **Pros**: Escalable, preciso, no confunde slots entre flows
- **Cons**: Dos llamadas al LLM cuando no hay flow activo (solo primer mensaje)
- **Mitigación**: Caché ayuda, y solo afecta el primer mensaje

**Alternativas consideradas:**
1. Combinar todos los slots (actual) - No escala ❌
2. Callback en SoniDU - Más complejo, requiere cambios en interfaz ❌
3. Two-stage en understand_node - Recomendado ✅

**Optimizaciones futuras (opcional):**
- Cachear resultado de intent detection para reutilizar
- Usar un predictor más ligero para intent detection (si DSPy lo soporta)
- Paralelizar ambas llamadas si el LLM lo permite (probablemente no)

**Consideraciones de diseño:**
- Mantiene el principio "Always Through NLU First"
- No cambia la arquitectura (solo implementación HOW)
- Compatible con diseño existente
- Mejora la precisión sin romper funcionalidad existente
