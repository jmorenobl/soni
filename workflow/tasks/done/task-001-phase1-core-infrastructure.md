## Task: 001 - Phase 1: Core Infrastructure for Multiple Slots Processing

**ID de tarea:** MULTI-SLOTS-001
**Hito:** 1 - Multiple Slots Processing (Solution 3)
**Dependencias:** Ninguna
**Duración estimada:** 4-6 horas

### Objetivo

Implementar la infraestructura core para procesar múltiples slots en un solo mensaje, siguiendo la Solución 3 (Hybrid Approach). Esto incluye agregar el método `advance_through_completed_steps` a `FlowStepManager` y extraer funciones helper en `validate_slot_node`.

### Contexto

El sistema actual falla cuando el usuario proporciona múltiples slots en un mensaje (ej: "I want to fly from New York to Los Angeles"). El NLU extrae correctamente ambos slots, pero el sistema solo procesa el primero. Esta tarea implementa la base para procesar todos los slots y avanzar iterativamente a través de los pasos completos.

**Referencias:**
- `docs/analysis/SOLUCION_MULTIPLES_SLOTS.md` - Solución recomendada (Solution 3)
- `docs/analysis/ANALISIS_ESCENARIOS_COMPLETO.md` - Análisis del problema
- `src/soni/flow/step_manager.py` - Archivo a modificar
- `src/soni/dm/nodes/validate_slot.py` - Archivo a modificar

### Entregables

- [ ] Método `advance_through_completed_steps` implementado en `FlowStepManager`
- [ ] Función helper `_process_all_slots` extraída en `validate_slot.py`
- [ ] Función helper `_detect_correction_or_modification` extraída en `validate_slot.py`
- [ ] Función helper `_handle_correction_flow` extraída en `validate_slot.py`
- [ ] Tests unitarios para `advance_through_completed_steps` (4 tests)
- [ ] Tests unitarios para funciones helper (3+ tests)
- [ ] Todos los tests pasan
- [ ] Linting y type checking pasan

### Implementación Detallada

#### Paso 1: Agregar `advance_through_completed_steps` a FlowStepManager

**Archivo(s) a crear/modificar:** `src/soni/flow/step_manager.py`

**Código específico:**

```python
def advance_through_completed_steps(
    self,
    state: DialogueState,
    context: RuntimeContext,
) -> dict[str, Any]:
    """Advance through all completed steps until finding an incomplete one.

    This function iteratively checks if the current step is complete and advances
    to the next step until it finds a step that is not complete, or until the flow
    is finished.

    Critical for handling cases where multiple slots are provided in one message.

    Args:
        state: Current dialogue state (will be mutated in-place)
        context: Runtime context with dependencies

    Returns:
        State updates dict with:
        - current_step: Final step name or None if flow complete
        - conversation_state: Updated based on final step type
        - flow_stack: Updated flow stack
        - waiting_for_slot: Updated if final step is collect type
        - current_prompted_slot: Updated if final step is collect type

    Example:
        >>> # User provides origin and destination in one message
        >>> # After saving slots, call this method
        >>> updates = step_manager.advance_through_completed_steps(state, context)
        >>> # Will advance through collect_origin and collect_destination
        >>> # Stop at collect_date (incomplete)
        >>> assert updates["current_step"] == "collect_date"
        >>> assert updates["waiting_for_slot"] == "departure_date"
    """
    max_iterations = 20  # Safety limit to prevent infinite loops
    iterations = 0

    while iterations < max_iterations:
        iterations += 1

        # Get current step configuration
        current_step_config = self.get_current_step_config(state, context)

        if not current_step_config:
            # No current step - flow might be complete or not started
            logger.info(
                f"No current step after {iterations} iteration(s) - flow complete"
            )
            return {"conversation_state": "completed"}

        # Check if current step is complete
        is_complete = self.is_step_complete(state, current_step_config, context)

        if not is_complete:
            # Found a step that is not complete - stop here
            logger.info(
                f"Stopped at incomplete step '{current_step_config.step}' "
                f"(type={current_step_config.type}) after {iterations} iteration(s)"
            )

            # Determine conversation_state based on step type
            step_type_to_state = {
                "action": "ready_for_action",
                "collect": "waiting_for_slot",
                "confirm": "ready_for_confirmation",
                "branch": "understanding",
                "say": "generating_response",
            }
            conversation_state = step_type_to_state.get(
                current_step_config.type, "understanding"
            )

            updates = {
                "flow_stack": state.get("flow_stack", []),
                "conversation_state": conversation_state,
            }

            # If it's a collect step, set waiting_for_slot
            if current_step_config.type == "collect":
                updates["waiting_for_slot"] = current_step_config.slot
                updates["current_prompted_slot"] = current_step_config.slot

            return updates

        # Current step is complete - advance to next step
        logger.debug(
            f"Step '{current_step_config.step}' is complete, advancing... "
            f"(iteration {iterations})"
        )

        advance_updates = self.advance_to_next_step(state, context)

        # Check if flow is complete
        if advance_updates.get("conversation_state") == "completed":
            logger.info(f"Flow completed after {iterations} iteration(s)")
            return advance_updates

        # Update state in place for next iteration
        state.update(advance_updates)

    # Safety: reached max iterations
    logger.error(
        f"advance_through_completed_steps reached max iterations ({max_iterations}). "
        f"This may indicate an infinite loop or a very long flow."
    )
    return {"conversation_state": "error"}
```

**Explicación:**
- Agregar el método después de `get_next_required_slot` en la clase `FlowStepManager`
- Incluir límite de seguridad de 20 iteraciones para prevenir loops infinitos
- Mutar el estado in-place (documentado en docstring)
- Mapear tipos de paso a estados de conversación usando diccionario
- Incluir logging comprehensivo para debugging

#### Paso 2: Extraer función helper `_process_all_slots`

**Archivo(s) a crear/modificar:** `src/soni/dm/nodes/validate_slot.py`

**Código específico:**

```python
async def _process_all_slots(
    slots: list,
    state: DialogueState,
    active_ctx: FlowContext,
    normalizer: INormalizer,
) -> dict[str, dict[str, Any]]:
    """Process and normalize all slots from NLU result.

    Args:
        slots: List of slots from NLU result (can be dict, SlotValue, or str)
        state: Current dialogue state
        active_ctx: Active flow context
        normalizer: Slot normalizer for value normalization

    Returns:
        Dictionary of flow_slots structure: {flow_id: {slot_name: normalized_value}}
    """
    flow_id = active_ctx["flow_id"]
    flow_slots = state.get("flow_slots", {}).copy()
    if flow_id not in flow_slots:
        flow_slots[flow_id] = {}

    for slot in slots:
        # Extract slot info
        if hasattr(slot, "name"):
            slot_name = slot.name
            raw_value = slot.value
        elif isinstance(slot, dict):
            slot_name = slot.get("name")
            raw_value = slot.get("value")
        elif isinstance(slot, str):
            slot_name = state.get("waiting_for_slot")
            raw_value = slot
        else:
            logger.warning(f"Unknown slot format: {type(slot)}, skipping")
            continue

        if not slot_name:
            logger.warning(f"Slot has no name, skipping: {slot}")
            continue

        # Normalize slot value
        normalized_value = await normalizer.normalize_slot(slot_name, raw_value)
        flow_slots[flow_id][slot_name] = normalized_value

        logger.debug(f"Processed slot '{slot_name}' = '{normalized_value}'")

    return flow_slots
```

**Explicación:**
- Extraer lógica de procesamiento de slots de `validate_slot_node`
- Manejar diferentes formatos de slot (dict, SlotValue model, string)
- Retornar estructura `flow_slots` completa
- Incluir logging para debugging

#### Paso 3: Extraer función helper `_detect_correction_or_modification`

**Archivo(s) a crear/modificar:** `src/soni/dm/nodes/validate_slot.py`

**Código específico:**

```python
def _detect_correction_or_modification(
    slots: list,
    message_type: str,
) -> bool:
    """Detect if message is a correction or modification.

    Args:
        slots: List of slots from NLU result
        message_type: Message type from NLU result

    Returns:
        True if this is a correction or modification, False otherwise
    """
    # Check if this is a fallback slot (created when NLU didn't extract)
    # Fallback slots have action=PROVIDE and confidence=0.5
    is_fallback_slot = (
        len(slots) == 1
        and isinstance(slots[0], dict)
        and slots[0].get("action") == "provide"
        and slots[0].get("confidence", 1.0) == 0.5
    )

    # Check slot actions - a slot with CORRECT or MODIFY action indicates correction/modification
    slot_actions = [
        slot.get("action") if isinstance(slot, dict) else getattr(slot, "action", None)
        for slot in slots
    ]
    has_correct_or_modify_action = any(
        action in ("correct", "modify", "CORRECT", "MODIFY")
        for action in slot_actions
        if action
    )

    # Fallback slots should NEVER be treated as corrections/modifications
    is_correction_or_modification = not is_fallback_slot and (
        message_type in ("correction", "modification") or has_correct_or_modify_action
    )

    return is_correction_or_modification
```

**Explicación:**
- Extraer lógica de detección de correcciones/modificaciones
- Preservar lógica existente de líneas 267-290 en `validate_slot.py`
- No tratar fallback slots como correcciones

#### Paso 4: Extraer función helper `_handle_correction_flow`

**Archivo(s) a crear/modificar:** `src/soni/dm/nodes/validate_slot.py`

**Código específico:**

```python
def _handle_correction_flow(
    state: DialogueState,
    runtime: Any,
    flow_slots: dict[str, dict[str, Any]],
    previous_step: str | None,
) -> dict[str, Any]:
    """Handle correction/modification flow.

    Args:
        state: Current dialogue state
        runtime: Runtime context
        flow_slots: Updated flow slots
        previous_step: Previous step name before correction

    Returns:
        State updates for correction flow
    """
    # Preserve existing correction handling logic from lines 309-415
    # This includes:
    # - Determining target step to return to
    # - Checking if all slots are filled
    # - Mapping step type to conversation_state
    # - Restoring target step in both DialogueState and FlowContext
    # ... (preserve existing implementation)
```

**Explicación:**
- Extraer lógica de manejo de correcciones de líneas 309-415
- Preservar toda la lógica existente sin cambios
- Solo extraer para mejorar organización del código

### Tests Requeridos

**Archivo de tests:** `tests/unit/flow/test_step_manager.py`

**Tests específicos a implementar:**

```python
class TestAdvanceThroughCompletedSteps:
    """Test iterative step advancement."""

    def test_single_step_advancement(self, mock_state, mock_context):
        """Test advancing through one completed step."""
        # Arrange: One collect step complete, next step incomplete
        # Act: Call advance_through_completed_steps
        # Assert: Advance once and stop at incomplete step

    def test_multiple_steps_advancement(self, mock_state, mock_context):
        """Test advancing through multiple completed steps."""
        # Arrange: Three collect steps all complete
        # Act: Call advance_through_completed_steps
        # Assert: Advance through all three, stop at action step

    def test_flow_completion(self, mock_state, mock_context):
        """Test advancement when flow completes."""
        # Arrange: All steps complete
        # Act: Call advance_through_completed_steps
        # Assert: conversation_state = "completed"

    def test_max_iterations_safety(self, mock_state, mock_context):
        """Test that max_iterations prevents infinite loops."""
        # Arrange: Create scenario that would loop (should never happen)
        # Act: Call advance_through_completed_steps
        # Assert: Stops after max_iterations, returns error state
```

**Archivo de tests:** `tests/unit/dm/nodes/test_validate_slot_helpers.py`

**Tests específicos a implementar:**

```python
class TestProcessAllSlots:
    """Test slot processing helper."""

    async def test_process_dict_slots(self):
        """Test processing slots in dict format."""

    async def test_process_slotvalue_slots(self):
        """Test processing SlotValue model slots."""

    async def test_process_string_slots(self):
        """Test processing string slots."""

class TestDetectCorrectionOrModification:
    """Test correction detection helper."""

    def test_detect_correction_by_message_type(self):
        """Test detection via message_type."""

    def test_detect_correction_by_slot_action(self):
        """Test detection via slot action."""

    def test_fallback_slot_not_correction(self):
        """Test that fallback slots are not treated as corrections."""
```

### Criterios de Éxito

- [ ] Método `advance_through_completed_steps` implementado y documentado
- [ ] Tres funciones helper extraídas y documentadas
- [ ] Todos los tests unitarios pasan (7+ tests)
- [ ] Linting pasa sin errores (`uv run ruff check .`)
- [ ] Type checking pasa sin errores (`uv run mypy src/soni`)
- [ ] Cobertura de código ≥ 90% para nuevas funciones
- [ ] Docstrings completos en todas las funciones nuevas

### Validación Manual

**Comandos para validar:**

```bash
# Run unit tests
uv run pytest tests/unit/flow/test_step_manager.py::TestAdvanceThroughCompletedSteps -v
uv run pytest tests/unit/dm/nodes/test_validate_slot_helpers.py -v

# Run linting
uv run ruff check src/soni/flow/step_manager.py src/soni/dm/nodes/validate_slot.py

# Run type checking
uv run mypy src/soni/flow/step_manager.py src/soni/dm/nodes/validate_slot.py

# Check coverage
uv run pytest --cov=src/soni/flow/step_manager --cov=src/soni/dm/nodes/validate_slot --cov-report=term-missing
```

**Resultado esperado:**
- Todos los tests pasan
- No hay errores de linting
- No hay errores de type checking
- Cobertura ≥ 90% para nuevas funciones

### Referencias

- `docs/analysis/SOLUCION_MULTIPLES_SLOTS.md` - Solución recomendada (Solution 3)
- `docs/analysis/ANALISIS_ESCENARIOS_COMPLETO.md` - Análisis del problema
- `src/soni/flow/step_manager.py` - Archivo base
- `src/soni/dm/nodes/validate_slot.py` - Archivo base (líneas 227-465)

### Notas Adicionales

- **Importante**: Preservar toda la lógica existente de correcciones/modificaciones
- **Seguridad**: El límite de 20 iteraciones es crítico para prevenir loops infinitos
- **Mutación de estado**: El método muta `state` in-place, esto está documentado y es intencional
- **Backwards compatibility**: No debe romper ningún comportamiento existente
