## Task: 003 - Phase 3: Testing & Validation

**ID de tarea:** MULTI-SLOTS-003
**Hito:** 1 - Multiple Slots Processing (Solution 3)
**Dependencias:** MULTI-SLOTS-002 (Phase 2 debe estar completa)
**Duración estimada:** 3-4 horas

### Objetivo

Implementar tests de integración completos para todos los escenarios y casos edge, asegurando que la solución funciona correctamente y no rompe funcionalidad existente.

### Contexto

Después de implementar la infraestructura y refactorizar los nodos (Phases 1 y 2), necesitamos validar exhaustivamente que:
1. Todos los escenarios existentes siguen funcionando (regresión)
2. El nuevo escenario (múltiples slots) funciona correctamente
3. Los casos edge están manejados correctamente

**Referencias:**
- `docs/analysis/ANALISIS_ESCENARIOS_COMPLETO.md` - Todos los escenarios definidos
- `scripts/debug_scenarios.py` - Script de debug para validación manual
- `tests/integration/test_e2e.py` - Tests de integración existentes

### Entregables

- [ ] Tests de integración para Scenario 1 (Simple sequential) ✅
- [ ] Tests de integración para Scenario 2 (Multiple slots) ✅
- [ ] Tests de integración para Scenario 3 (Correction) ✅
- [ ] Tests de integración para Scenario 4 (Digression) ✅
- [ ] Tests de integración para Scenario 5 (Cancellation) ✅
- [ ] Test edge case: Todos los slots a la vez
- [ ] Test edge case: Mix de slots nuevos y correcciones
- [ ] Test edge case: Valores inválidos con múltiples slots
- [ ] Test edge case: Flujos muy largos (max_iterations)
- [ ] Todos los tests pasan
- [ ] Cobertura de código ≥ 90%

### Implementación Detallada

#### Paso 1: Tests de Integración para Todos los Escenarios

**Archivo(s) a crear/modificar:** `tests/integration/test_all_scenarios.py`

**Código específico:**

```python
"""Integration tests for all conversation scenarios."""

import pytest
from soni.core.state import DialogueState, get_all_slots, get_current_flow, state_from_dict
from soni.runtime import RuntimeLoop
from pathlib import Path


class TestScenario1Sequential:
    """Test Scenario 1: Simple sequential slot collection."""

    @pytest.mark.asyncio
    async def test_scenario_1_complete_flow(self):
        """Test complete sequential flow."""
        config_path = Path("examples/flight_booking/soni.yaml")
        runtime = RuntimeLoop(config_path)
        runtime.config.settings.persistence.backend = "memory"
        await runtime._ensure_graph_initialized()

        user_id = "test_scenario_1"

        # Turn 1: Trigger flow
        response1 = await runtime.process_message("I want to book a flight", user_id)
        config = {"configurable": {"thread_id": user_id}}
        snapshot = await runtime.graph.aget_state(config)
        state = state_from_dict(snapshot.values, allow_partial=True)

        assert get_current_flow(state) == "book_flight"
        assert state["current_step"] == "collect_origin"
        assert state["waiting_for_slot"] == "origin"

        # Turn 2: Provide origin
        response2 = await runtime.process_message("Madrid", user_id)
        snapshot = await runtime.graph.aget_state(config)
        state = state_from_dict(snapshot.values, allow_partial=True)

        slots = get_all_slots(state)
        assert slots["origin"] == "Madrid"
        assert state["current_step"] == "collect_destination"
        assert state["waiting_for_slot"] == "destination"

        # Turn 3: Provide destination
        response3 = await runtime.process_message("Barcelona", user_id)
        snapshot = await runtime.graph.aget_state(config)
        state = state_from_dict(snapshot.values, allow_partial=True)

        slots = get_all_slots(state)
        assert slots["destination"] == "Barcelona"
        assert state["current_step"] == "collect_date"
        assert state["waiting_for_slot"] == "departure_date"

        # Turn 4: Provide date
        response4 = await runtime.process_message("Tomorrow", user_id)
        snapshot = await runtime.graph.aget_state(config)
        state = state_from_dict(snapshot.values, allow_partial=True)

        slots = get_all_slots(state)
        assert "departure_date" in slots
        assert state["current_step"] == "search_flights"
        assert state["conversation_state"] == "ready_for_action"

        await runtime.cleanup()


class TestScenario2MultipleSlots:
    """Test Scenario 2: Multiple slots in one message."""

    @pytest.mark.asyncio
    async def test_multiple_slots_in_one_message(self):
        """Test: 'I want to fly from New York to Los Angeles'"""
        config_path = Path("examples/flight_booking/soni.yaml")
        runtime = RuntimeLoop(config_path)
        runtime.config.settings.persistence.backend = "memory"
        await runtime._ensure_graph_initialized()

        user_id = "test_scenario_2"

        # Turn 1: Provide multiple slots
        response1 = await runtime.process_message(
            "I want to fly from New York to Los Angeles",
            user_id
        )
        config = {"configurable": {"thread_id": user_id}}
        snapshot = await runtime.graph.aget_state(config)
        state = state_from_dict(snapshot.values, allow_partial=True)

        slots = get_all_slots(state)
        assert slots["origin"] == "New York"
        assert slots["destination"] == "Los Angeles"
        # CRITICAL: Should advance to collect_date, not stay at collect_destination
        assert state["current_step"] == "collect_date"
        assert state["waiting_for_slot"] == "departure_date"
        assert state["conversation_state"] == "waiting_for_slot"

        # Turn 2: Provide last slot
        response2 = await runtime.process_message("Next Friday", user_id)
        snapshot = await runtime.graph.aget_state(config)
        state = state_from_dict(snapshot.values, allow_partial=True)

        slots = get_all_slots(state)
        assert "departure_date" in slots
        assert state["current_step"] == "search_flights"
        assert state["conversation_state"] == "ready_for_action"

        await runtime.cleanup()

    @pytest.mark.asyncio
    async def test_all_slots_at_once(self):
        """Test: 'I want to fly from X to Y on Z'"""
        config_path = Path("examples/flight_booking/soni.yaml")
        runtime = RuntimeLoop(config_path)
        runtime.config.settings.persistence.backend = "memory"
        await runtime._ensure_graph_initialized()

        user_id = "test_all_slots"

        # Provide all slots in one message
        response = await runtime.process_message(
            "I want to fly from Boston to Seattle tomorrow",
            user_id
        )
        config = {"configurable": {"thread_id": user_id}}
        snapshot = await runtime.graph.aget_state(config)
        state = state_from_dict(snapshot.values, allow_partial=True)

        slots = get_all_slots(state)
        assert len(slots) == 3
        assert slots["origin"] == "Boston"
        assert slots["destination"] == "Seattle"
        assert "departure_date" in slots

        # Should advance all the way to action
        assert state["current_step"] == "search_flights"
        assert state["conversation_state"] == "ready_for_action"

        await runtime.cleanup()


class TestScenario3Correction:
    """Test Scenario 3: Slot correction."""

    @pytest.mark.asyncio
    async def test_scenario_3_correction(self):
        """Test correction of a previously provided slot."""
        config_path = Path("examples/flight_booking/soni.yaml")
        runtime = RuntimeLoop(config_path)
        runtime.config.settings.persistence.backend = "memory"
        await runtime._ensure_graph_initialized()

        user_id = "test_scenario_3"

        # Turn 1: Trigger flow
        await runtime.process_message("Book a flight", user_id)

        # Turn 2: Provide origin
        await runtime.process_message("Chicago", user_id)
        config = {"configurable": {"thread_id": user_id}}
        snapshot = await runtime.graph.aget_state(config)
        state = state_from_dict(snapshot.values, allow_partial=True)

        slots = get_all_slots(state)
        assert slots["origin"] == "Chicago"

        # Turn 3: Correct origin
        await runtime.process_message("Actually, I meant Denver not Chicago", user_id)
        snapshot = await runtime.graph.aget_state(config)
        state = state_from_dict(snapshot.values, allow_partial=True)

        slots = get_all_slots(state)
        assert slots["origin"] == "Denver"  # Corrected value
        assert state["current_step"] == "collect_destination"  # Should return to this step

        # Turn 4: Provide destination
        await runtime.process_message("Seattle", user_id)
        snapshot = await runtime.graph.aget_state(config)
        state = state_from_dict(snapshot.values, allow_partial=True)

        slots = get_all_slots(state)
        assert slots["origin"] == "Denver"
        assert slots["destination"] == "Seattle"

        await runtime.cleanup()


class TestScenario4Digression:
    """Test Scenario 4: Digression (question during flow)."""

    @pytest.mark.asyncio
    async def test_scenario_4_digression(self):
        """Test question during flow without changing flow."""
        config_path = Path("examples/flight_booking/soni.yaml")
        runtime = RuntimeLoop(config_path)
        runtime.config.settings.persistence.backend = "memory"
        await runtime._ensure_graph_initialized()

        user_id = "test_scenario_4"

        # Turn 1: Trigger flow
        await runtime.process_message("I want to book a flight", user_id)

        # Turn 2: Provide origin
        await runtime.process_message("San Francisco", user_id)
        config = {"configurable": {"thread_id": user_id}}
        snapshot = await runtime.graph.aget_state(config)
        state = state_from_dict(snapshot.values, allow_partial=True)

        slots = get_all_slots(state)
        assert slots["origin"] == "San Francisco"
        assert get_current_flow(state) == "book_flight"

        # Turn 3: Ask question (digression)
        response3 = await runtime.process_message("What airports do you support?", user_id)
        snapshot = await runtime.graph.aget_state(config)
        state = state_from_dict(snapshot.values, allow_partial=True)

        # Flow should NOT change
        assert get_current_flow(state) == "book_flight"
        assert state["current_step"] == "collect_destination"  # Should stay the same
        slots = get_all_slots(state)
        assert slots["origin"] == "San Francisco"  # Should not change

        # Turn 4: Continue with destination after digression
        await runtime.process_message("Miami", user_id)
        snapshot = await runtime.graph.aget_state(config)
        state = state_from_dict(snapshot.values, allow_partial=True)

        slots = get_all_slots(state)
        assert slots["origin"] == "San Francisco"
        assert slots["destination"] == "Miami"

        await runtime.cleanup()


class TestScenario5Cancellation:
    """Test Scenario 5: Flow cancellation."""

    @pytest.mark.asyncio
    async def test_scenario_5_cancellation(self):
        """Test canceling flow mid-way."""
        config_path = Path("examples/flight_booking/soni.yaml")
        runtime = RuntimeLoop(config_path)
        runtime.config.settings.persistence.backend = "memory"
        await runtime._ensure_graph_initialized()

        user_id = "test_scenario_5"

        # Turn 1: Trigger flow
        await runtime.process_message("Book a flight please", user_id)

        # Turn 2: Provide origin
        await runtime.process_message("Boston", user_id)
        config = {"configurable": {"thread_id": user_id}}
        snapshot = await runtime.graph.aget_state(config)
        state = state_from_dict(snapshot.values, allow_partial=True)

        assert get_current_flow(state) == "book_flight"
        slots = get_all_slots(state)
        assert slots["origin"] == "Boston"

        # Turn 3: Cancel flow
        await runtime.process_message("Actually, cancel this", user_id)
        snapshot = await runtime.graph.aget_state(config)
        state = state_from_dict(snapshot.values, allow_partial=True)

        # Flow should be canceled
        assert len(state.get("flow_stack", [])) == 0
        assert get_current_flow(state) == "none"
        assert state["conversation_state"] == "idle"

        # Turn 4: Start fresh
        await runtime.process_message("I want to book a new flight", user_id)
        snapshot = await runtime.graph.aget_state(config)
        state = state_from_dict(snapshot.values, allow_partial=True)

        assert get_current_flow(state) == "book_flight"
        slots = get_all_slots(state)
        assert len(slots) == 0  # New flow, no slots yet

        await runtime.cleanup()
```

#### Paso 2: Tests de Edge Cases

**Archivo(s) a crear/modificar:** `tests/integration/test_edge_cases_multiple_slots.py`

**Código específico:**

```python
"""Edge case tests for multiple slots processing."""

import pytest
from soni.core.state import DialogueState, get_all_slots, state_from_dict
from soni.runtime import RuntimeLoop
from pathlib import Path


class TestEdgeCasesMultipleSlots:
    """Edge cases for multiple slots processing."""

    @pytest.mark.asyncio
    async def test_mix_new_slots_and_corrections(self):
        """Test providing multiple slots while correcting one."""
        config_path = Path("examples/flight_booking/soni.yaml")
        runtime = RuntimeLoop(config_path)
        runtime.config.settings.persistence.backend = "memory"
        await runtime._ensure_graph_initialized()

        user_id = "test_mix"

        # Turn 1: Trigger flow and provide origin
        await runtime.process_message("I want to book a flight from Chicago", user_id)

        # Turn 2: Correct origin and provide destination
        await runtime.process_message(
            "Actually, I meant Denver, and I want to go to Seattle",
            user_id
        )
        config = {"configurable": {"thread_id": user_id}}
        snapshot = await runtime.graph.aget_state(config)
        state = state_from_dict(snapshot.values, allow_partial=True)

        slots = get_all_slots(state)
        assert slots["origin"] == "Denver"  # Corrected
        assert slots["destination"] == "Seattle"  # New

        await runtime.cleanup()

    @pytest.mark.asyncio
    async def test_invalid_slot_with_multiple_slots(self):
        """Test validation error when multiple slots provided but one is invalid."""
        config_path = Path("examples/flight_booking/soni.yaml")
        runtime = RuntimeLoop(config_path)
        runtime.config.settings.persistence.backend = "memory"
        await runtime._ensure_graph_initialized()

        user_id = "test_invalid"

        # Provide multiple slots where one might be invalid
        # (This depends on validators - adjust based on actual validator behavior)
        response = await runtime.process_message(
            "I want to fly from New York to Los Angeles on yesterday",  # Invalid date
            user_id
        )
        config = {"configurable": {"thread_id": user_id}}
        snapshot = await runtime.graph.aget_state(config)
        state = state_from_dict(snapshot.values, allow_partial=True)

        # Should handle validation error gracefully
        # Valid slots should be saved, invalid one should trigger error
        slots = get_all_slots(state)
        assert slots["origin"] == "New York"
        assert slots["destination"] == "Los Angeles"
        # departure_date should not be saved if invalid

        await runtime.cleanup()

    @pytest.mark.asyncio
    async def test_max_iterations_safety(self):
        """Test that max_iterations prevents infinite loops."""
        # This test requires a flow with many collect steps
        # Create a test flow with 25+ collect steps to test max_iterations
        # For now, this is a placeholder - actual implementation depends on test flow
        pass
```

### Tests Requeridos

**Archivo de tests:** `tests/integration/test_all_scenarios.py`

**Tests específicos a implementar:**
- Test Scenario 1: Sequential flow completo
- Test Scenario 2: Multiple slots (2 tests: básico y todos a la vez)
- Test Scenario 3: Correction
- Test Scenario 4: Digression
- Test Scenario 5: Cancellation

**Archivo de tests:** `tests/integration/test_edge_cases_multiple_slots.py`

**Tests específicos a implementar:**
- Test mix de slots nuevos y correcciones
- Test valores inválidos con múltiples slots
- Test max_iterations safety (placeholder)

### Criterios de Éxito

- [ ] Todos los tests de integración pasan (5 escenarios)
- [ ] Tests de edge cases pasan (3+ tests)
- [ ] Scenario 2 (Multiple slots) PASA ✅ (crítico)
- [ ] Todos los escenarios existentes siguen funcionando (regresión)
- [ ] Cobertura de código ≥ 90%
- [ ] Script `debug_scenarios.py` muestra comportamiento correcto para todos los escenarios

### Validación Manual

**Comandos para validar:**

```bash
# Run all integration tests
uv run pytest tests/integration/test_all_scenarios.py -v
uv run pytest tests/integration/test_edge_cases_multiple_slots.py -v

# Run all tests
uv run pytest tests/ -v

# Check coverage
uv run pytest --cov=src/soni --cov-report=term-missing --cov-report=html

# Run debug script for all scenarios
uv run python scripts/debug_scenarios.py 1
uv run python scripts/debug_scenarios.py 2  # CRITICAL - must pass
uv run python scripts/debug_scenarios.py 3
uv run python scripts/debug_scenarios.py 4
uv run python scripts/debug_scenarios.py 5
```

**Resultado esperado:**
- Todos los tests pasan
- Scenario 2 muestra estado correcto:
  - `current_step == "collect_date"` (no "collect_destination")
  - `waiting_for_slot == "departure_date"`
  - Slots `origin` y `destination` están llenos
- Cobertura ≥ 90%

### Referencias

- `docs/analysis/ANALISIS_ESCENARIOS_COMPLETO.md` - Todos los escenarios
- `scripts/debug_scenarios.py` - Script de debug
- `tests/integration/test_e2e.py` - Tests existentes de referencia

### Notas Adicionales

- **Prioridad**: Scenario 2 DEBE pasar - es el objetivo principal de esta implementación
- **Regresión**: Asegurar que ningún escenario existente se rompe
- **Edge cases**: Implementar los más importantes primero, agregar más según necesidad
- **Cobertura**: Enfocarse en cubrir las nuevas funciones y flujos
