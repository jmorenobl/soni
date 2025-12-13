## Task: 002 - Phase 2: Update Nodes to Use New Infrastructure

**ID de tarea:** MULTI-SLOTS-002
**Hito:** 1 - Multiple Slots Processing (Solution 3)
**Dependencias:** MULTI-SLOTS-001 (Phase 1 debe estar completa)
**Duración estimada:** 2-3 horas

### Objetivo

Refactorizar `validate_slot_node` y `handle_intent_change_node` para usar la nueva infraestructura (`advance_through_completed_steps` y funciones helper), eliminando lógica duplicada y habilitando el procesamiento de múltiples slots.

### Contexto

Una vez que la infraestructura core está implementada (Phase 1), necesitamos actualizar los nodos existentes para usar las nuevas funciones. Esto eliminará duplicación de código y habilitará el procesamiento correcto de múltiples slots en un solo mensaje.

**Referencias:**
- `docs/analysis/SOLUCION_MULTIPLES_SLOTS.md` - Solución recomendada (Solution 3)
- `src/soni/dm/nodes/validate_slot.py` - Archivo a refactorizar
- `src/soni/dm/nodes/handle_intent_change.py` - Archivo a refactorizar
- `src/soni/flow/step_manager.py` - Nueva infraestructura (Phase 1)

### Entregables

- [ ] `validate_slot_node` refactorizado para usar helpers
- [ ] `handle_intent_change_node` refactorizado para usar `advance_through_completed_steps`
- [ ] Función helper `_extract_slots_from_nlu` extraída
- [ ] Tests de regresión para Scenario 1 (Simple sequential flow)
- [ ] Tests de regresión para Scenario 3 (Correction)
- [ ] Test nuevo para Scenario 2 (Multiple slots) - DEBE pasar
- [ ] Todos los tests pasan
- [ ] Linting y type checking pasan

### Implementación Detallada

#### Paso 1: Refactorizar `validate_slot_node`

**Archivo(s) a crear/modificar:** `src/soni/dm/nodes/validate_slot.py`

**Código específico:**

```python
async def validate_slot_node(
    state: DialogueState,
    runtime: Any,
) -> dict:
    """Validate and normalize slot values."""
    normalizer = runtime.context["normalizer"]
    flow_manager = runtime.context["flow_manager"]
    step_manager = runtime.context["step_manager"]
    nlu_result = state.get("nlu_result", {})

    slots = nlu_result.get("slots", [])

    # ... existing fallback logic (lines 28-225) ...
    # (preserve all existing fallback logic)

    active_ctx = flow_manager.get_active_context(state)
    if not active_ctx:
        return {"conversation_state": "error"}

    # Detect correction/modification
    previous_step = active_ctx.get("current_step")
    previous_conversation_state = state.get("conversation_state")
    message_type = nlu_result.get("message_type", "")

    is_correction_or_modification = _detect_correction_or_modification(
        slots, message_type
    )

    try:
        # Process all slots using helper
        flow_slots = await _process_all_slots(slots, state, active_ctx, normalizer)
        state["flow_slots"] = flow_slots

        # Handle correction/modification (preserve existing logic)
        if is_correction_or_modification:
            return _handle_correction_flow(
                state, runtime, flow_slots, previous_step
            )

        # Normal flow: Advance through completed steps
        updates = step_manager.advance_through_completed_steps(state, runtime.context)
        updates["flow_slots"] = flow_slots

        return updates

    except Exception as e:
        logger.error(f"Validation failed: {e}")
        return {"conversation_state": "error", "validation_error": str(e)}
```

**Explicación:**
- Reemplazar procesamiento manual de slots (línea 227) con `_process_all_slots`
- Reemplazar detección manual de correcciones con `_detect_correction_or_modification`
- Reemplazar lógica de corrección inline con `_handle_correction_flow`
- Reemplazar avance manual de pasos (líneas 417-453) con `advance_through_completed_steps`
- Preservar toda la lógica de fallback existente (líneas 28-225)

#### Paso 2: Extraer helper `_extract_slots_from_nlu`

**Archivo(s) a crear/modificar:** `src/soni/dm/nodes/handle_intent_change.py`

**Código específico:**

```python
def _extract_slots_from_nlu(slots_from_nlu: list) -> dict[str, Any]:
    """Extract slots from NLU result into a dictionary.

    Args:
        slots_from_nlu: List of slots from NLU result (can be dict or SlotValue)

    Returns:
        Dictionary of {slot_name: slot_value}
    """
    extracted_slots: dict[str, Any] = {}
    for slot in slots_from_nlu:
        if isinstance(slot, dict):
            slot_name = slot.get("name")
            slot_value = slot.get("value")
            if slot_name and slot_value is not None:
                extracted_slots[slot_name] = slot_value
        elif hasattr(slot, "name") and hasattr(slot, "value"):
            # SlotValue model
            extracted_slots[slot.name] = slot.value

    return extracted_slots
```

**Explicación:**
- Extraer lógica de extracción de slots de líneas 125-134
- Manejar tanto dict como SlotValue model
- Retornar diccionario simple

#### Paso 3: Refactorizar `handle_intent_change_node`

**Archivo(s) a crear/modificar:** `src/soni/dm/nodes/handle_intent_change.py`

**Código específico:**

```python
async def handle_intent_change_node(
    state: DialogueState,
    runtime: Any,
) -> dict:
    # ... existing flow activation logic (lines 15-117) ...
    # (preserve all existing flow activation logic)

    # Save slots from NLU result
    slots_from_nlu = nlu_result.get("slots", [])
    if slots_from_nlu and active_ctx:
        extracted_slots = _extract_slots_from_nlu(slots_from_nlu)
        if extracted_slots:
            current_slots = get_all_slots(state)
            current_slots.update(extracted_slots)
            set_all_slots(state, current_slots)
            logger.info(
                f"Saved {len(extracted_slots)} slot(s) from NLU result: {list(extracted_slots.keys())}"
            )

    # Advance through completed steps using centralized method
    step_manager = runtime.context["step_manager"]
    updates = step_manager.advance_through_completed_steps(state, runtime.context)
    updates["flow_stack"] = state["flow_stack"]
    updates["flow_slots"] = state["flow_slots"]
    updates["user_message"] = ""  # Clear after processing

    return updates
```

**Explicación:**
- Reemplazar lógica manual de avance de pasos (líneas 149-197) con `advance_through_completed_steps`
- Usar helper `_extract_slots_from_nlu` para extraer slots
- Preservar toda la lógica de activación de flujo existente
- Limpiar `user_message` después de procesar

### Tests Requeridos

**Archivo de tests:** `tests/integration/test_multiple_slots_scenario.py`

**Tests específicos a implementar:**

```python
class TestScenario2MultipleSlots:
    """Test Scenario 2: Multiple slots in one message."""

    async def test_multiple_slots_in_one_message(self, runtime_loop):
        """Test: 'I want to fly from New York to Los Angeles'"""
        # Turn 1: Start flow with multiple slots
        response1 = await runtime_loop.process_message(
            "I want to fly from New York to Los Angeles",
            user_id="test_user"
        )

        # Get state
        config = {"configurable": {"thread_id": "test_user"}}
        snapshot = await runtime_loop.graph.aget_state(config)
        state = state_from_dict(snapshot.values, allow_partial=True)

        # Assertions:
        slots = get_all_slots(state)
        assert slots["origin"] == "New York"
        assert slots["destination"] == "Los Angeles"
        assert state["current_step"] == "collect_date"  # Not collect_destination!
        assert state["waiting_for_slot"] == "departure_date"
        assert state["conversation_state"] == "waiting_for_slot"

        # Turn 2: Provide last slot
        response2 = await runtime_loop.process_message(
            "tomorrow",
            user_id="test_user"
        )

        snapshot = await runtime_loop.graph.aget_state(config)
        state = state_from_dict(snapshot.values, allow_partial=True)

        # Assertions:
        assert state["current_step"] == "search_flights"
        assert state["conversation_state"] == "ready_for_action"

    async def test_all_slots_at_once(self, runtime_loop):
        """Test: 'I want to fly from X to Y on Z'"""
        response = await runtime_loop.process_message(
            "I want to fly from Boston to Seattle tomorrow",
            user_id="test_user"
        )

        config = {"configurable": {"thread_id": "test_user"}}
        snapshot = await runtime_loop.graph.aget_state(config)
        state = state_from_dict(snapshot.values, allow_partial=True)

        # Should advance all the way to action
        assert state["current_step"] == "search_flights"
        assert state["conversation_state"] == "ready_for_action"
        slots = get_all_slots(state)
        assert len(slots) == 3
        assert "origin" in slots
        assert "destination" in slots
        assert "departure_date" in slots
```

**Archivo de tests:** `tests/regression/test_scenario_1_sequential.py`

**Tests específicos a implementar:**

```python
class TestScenario1Regression:
    """Regression test for Scenario 1: Sequential slot collection."""

    async def test_scenario_1_sequential_flow(self, runtime_loop):
        """Ensure Scenario 1 still works after refactoring."""
        # Turn 1: Trigger flow
        await runtime_loop.process_message("I want to book a flight", user_id="test")

        # Turn 2: Provide origin
        await runtime_loop.process_message("Madrid", user_id="test")

        # Turn 3: Provide destination
        await runtime_loop.process_message("Barcelona", user_id="test")

        # Turn 4: Provide date
        response = await runtime_loop.process_message("Tomorrow", user_id="test")

        # Assertions: Flow should complete correctly
        config = {"configurable": {"thread_id": "test"}}
        snapshot = await runtime_loop.graph.aget_state(config)
        state = state_from_dict(snapshot.values, allow_partial=True)

        slots = get_all_slots(state)
        assert slots["origin"] == "Madrid"
        assert slots["destination"] == "Barcelona"
        assert "departure_date" in slots
```

**Archivo de tests:** `tests/regression/test_scenario_3_correction.py`

**Tests específicos a implementar:**

```python
class TestScenario3Regression:
    """Regression test for Scenario 3: Slot correction."""

    async def test_scenario_3_correction(self, runtime_loop):
        """Ensure Scenario 3 still works after refactoring."""
        # Turn 1: Trigger flow
        await runtime_loop.process_message("Book a flight", user_id="test")

        # Turn 2: Provide origin
        await runtime_loop.process_message("Chicago", user_id="test")

        # Turn 3: Correct origin
        await runtime_loop.process_message("Actually, I meant Denver not Chicago", user_id="test")

        # Turn 4: Provide destination
        response = await runtime_loop.process_message("Seattle", user_id="test")

        # Assertions: Correction should work
        config = {"configurable": {"thread_id": "test"}}
        snapshot = await runtime_loop.graph.aget_state(config)
        state = state_from_dict(snapshot.values, allow_partial=True)

        slots = get_all_slots(state)
        assert slots["origin"] == "Denver"  # Corrected value
        assert slots["destination"] == "Seattle"
```

### Criterios de Éxito

- [ ] `validate_slot_node` refactorizado usando helpers
- [ ] `handle_intent_change_node` refactorizado usando `advance_through_completed_steps`
- [ ] Helper `_extract_slots_from_nlu` extraído
- [ ] Test Scenario 2 (Multiple slots) PASA ✅
- [ ] Test Scenario 1 (Sequential) PASA ✅ (regresión)
- [ ] Test Scenario 3 (Correction) PASA ✅ (regresión)
- [ ] Todos los tests pasan
- [ ] Linting pasa sin errores
- [ ] Type checking pasa sin errores
- [ ] No se rompe funcionalidad existente

### Validación Manual

**Comandos para validar:**

```bash
# Run integration tests for Scenario 2
uv run pytest tests/integration/test_multiple_slots_scenario.py -v

# Run regression tests
uv run pytest tests/regression/ -v

# Run all tests
uv run pytest tests/ -v

# Run linting
uv run ruff check src/soni/dm/nodes/validate_slot.py src/soni/dm/nodes/handle_intent_change.py

# Run type checking
uv run mypy src/soni/dm/nodes/validate_slot.py src/soni/dm/nodes/handle_intent_change.py

# Run debug script for Scenario 2
uv run python scripts/debug_scenarios.py 2
```

**Resultado esperado:**
- Test Scenario 2 PASA ✅ (crítico)
- Todos los tests de regresión pasan
- Script de debug muestra estado correcto:
  - `current_step == "collect_date"` (no "collect_destination")
  - `waiting_for_slot == "departure_date"`
  - Slots `origin` y `destination` están llenos

### Referencias

- `docs/analysis/SOLUCION_MULTIPLES_SLOTS.md` - Solución recomendada (Solution 3)
- `src/soni/dm/nodes/validate_slot.py` - Archivo a refactorizar (líneas 227-465)
- `src/soni/dm/nodes/handle_intent_change.py` - Archivo a refactorizar (líneas 119-197)
- `scripts/debug_scenarios.py` - Script para validar manualmente

### Notas Adicionales

- **Crítico**: No romper funcionalidad existente - todos los tests de regresión deben pasar
- **Prioridad**: El test de Scenario 2 DEBE pasar después de esta fase
- **Preservar lógica**: Mantener toda la lógica de fallback y correcciones existente
- **Validación**: Usar `scripts/debug_scenarios.py 2` para validar visualmente el comportamiento
