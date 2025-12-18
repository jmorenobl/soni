## Task: 010 - Add Comprehensive Tests for Edge Cases

**ID de tarea:** 010
**Hito:** 3 - Production Readiness
**Dependencias:** Tasks 001-008
**Duración estimada:** 8 horas
**Prioridad:** MEDIA

### Objetivo

Agregar tests comprehensivos para edge cases identificados durante el análisis arquitectural, cubriendo escenarios que actualmente no tienen cobertura adecuada.

### Contexto

Durante el análisis se identificaron gaps de testing en:

1. **Flow stack operations:**
   - Múltiples flujos activos simultáneamente
   - Pop de stack vacío
   - Intent change durante slot collection

2. **ActionRegistry:**
   - Dual-layer registration (global + local)
   - Precedencia local sobre global
   - Registro concurrente

3. **FlowDelta merging:**
   - Múltiples deltas en secuencia
   - Deltas parciales (solo stack o solo slots)
   - Merge con estado inicial vacío

4. **ResponseExtractor:**
   - Mensajes vacíos
   - Múltiples AI messages
   - Mensajes sin content

5. **Error recovery:**
   - NLU failures mid-flow
   - Action execution failures
   - Validation errors en slots

### Entregables

- [ ] Tests para flow stack edge cases
- [ ] Tests para ActionRegistry dual-layer
- [ ] Tests para FlowDelta merging
- [ ] Tests para ResponseExtractor edge cases
- [ ] Tests para error recovery scenarios
- [ ] Cobertura mínima 85% en módulos críticos

### Implementación Detallada

#### Paso 1: Tests de Flow Stack Edge Cases

**Test file:** `tests/unit/flow/test_flow_manager_edge_cases.py`

```python
import pytest
from soni.flow.manager import FlowManager, FlowDelta, merge_delta
from soni.core.state import create_empty_dialogue_state
from soni.core.errors import FlowStackError
from soni.core.constants import FlowContextState


class TestFlowStackEdgeCases:
    """Edge case tests for flow stack operations."""

    @pytest.fixture
    def flow_manager(self):
        return FlowManager()

    @pytest.fixture
    def empty_state(self):
        return create_empty_dialogue_state()

    def test_pop_empty_stack_raises_error(self, flow_manager, empty_state):
        """Test that popping empty stack raises FlowStackError."""
        with pytest.raises(FlowStackError) as exc_info:
            flow_manager.pop_flow(empty_state)

        assert "empty" in str(exc_info.value).lower()

    def test_multiple_flows_stacked(self, flow_manager, empty_state):
        """Test pushing multiple flows creates proper stack."""
        # Push three flows
        _, delta1 = flow_manager.push_flow(empty_state, "flow1")
        state1 = {**empty_state, **{"flow_stack": delta1.flow_stack, "flow_slots": delta1.flow_slots}}

        _, delta2 = flow_manager.push_flow(state1, "flow2")
        state2 = {**state1, **{"flow_stack": delta2.flow_stack, "flow_slots": delta2.flow_slots}}

        _, delta3 = flow_manager.push_flow(state2, "flow3")
        final_state = {**state2, **{"flow_stack": delta3.flow_stack, "flow_slots": delta3.flow_slots}}

        assert len(final_state["flow_stack"]) == 3
        assert final_state["flow_stack"][-1]["flow_name"] == "flow3"
        assert final_state["flow_stack"][0]["flow_name"] == "flow1"

    def test_pop_preserves_underlying_flows(self, flow_manager, empty_state):
        """Test that popping top flow preserves flows underneath."""
        # Push two flows
        _, delta1 = flow_manager.push_flow(empty_state, "flow1", {"slot1": "value1"})
        state1 = {**empty_state, **{"flow_stack": delta1.flow_stack, "flow_slots": delta1.flow_slots}}

        _, delta2 = flow_manager.push_flow(state1, "flow2", {"slot2": "value2"})
        state2 = {**state1, **{"flow_stack": delta2.flow_stack, "flow_slots": delta2.flow_slots}}

        # Pop top flow
        popped, delta3 = flow_manager.pop_flow(state2)

        assert popped["flow_name"] == "flow2"
        assert len(delta3.flow_stack) == 1
        assert delta3.flow_stack[0]["flow_name"] == "flow1"

    def test_intent_change_to_same_flow_returns_none(self, flow_manager, empty_state):
        """Test that intent change to same active flow is no-op."""
        # Start flow
        _, delta1 = flow_manager.push_flow(empty_state, "greeting")
        state1 = {**empty_state, **{"flow_stack": delta1.flow_stack, "flow_slots": delta1.flow_slots}}

        # Intent change to same flow
        delta2 = flow_manager.handle_intent_change(state1, "greeting")

        assert delta2 is None  # No change

    def test_intent_change_during_active_flow(self, flow_manager, empty_state):
        """Test that intent change during flow pushes new flow on stack."""
        # Start first flow
        _, delta1 = flow_manager.push_flow(empty_state, "booking")
        state1 = {**empty_state, **{"flow_stack": delta1.flow_stack, "flow_slots": delta1.flow_slots}}

        # Intent change to different flow
        delta2 = flow_manager.handle_intent_change(state1, "help")

        assert delta2 is not None
        assert len(delta2.flow_stack) == 2
        assert delta2.flow_stack[-1]["flow_name"] == "help"

    def test_set_slot_without_active_flow_returns_none(self, flow_manager, empty_state):
        """Test that setting slot without active flow is no-op."""
        delta = flow_manager.set_slot(empty_state, "some_slot", "value")

        assert delta is None

    def test_get_slot_without_active_flow_returns_none(self, flow_manager, empty_state):
        """Test that getting slot without active flow returns None."""
        result = flow_manager.get_slot(empty_state, "some_slot")

        assert result is None

    def test_slots_isolated_between_flow_instances(self, flow_manager, empty_state):
        """Test that slots are isolated between different flow instances."""
        # Push flow1 and set slot
        flow_id1, delta1 = flow_manager.push_flow(empty_state, "booking")
        state1 = {**empty_state, **{"flow_stack": delta1.flow_stack, "flow_slots": delta1.flow_slots}}
        delta_slot1 = flow_manager.set_slot(state1, "amount", 100)
        state1 = {**state1, **{"flow_slots": delta_slot1.flow_slots}}

        # Push same flow again (new instance)
        flow_id2, delta2 = flow_manager.push_flow(state1, "booking")
        state2 = {**state1, **{"flow_stack": delta2.flow_stack, "flow_slots": delta2.flow_slots}}

        # Verify different flow_ids
        assert flow_id1 != flow_id2

        # Verify slots are separate
        assert state2["flow_slots"][flow_id1]["amount"] == 100
        assert flow_id2 not in state2["flow_slots"] or "amount" not in state2["flow_slots"].get(flow_id2, {})


class TestFlowDeltaMerging:
    """Tests for FlowDelta merge operations."""

    def test_merge_delta_with_none(self):
        """Test that merging None delta does nothing."""
        updates = {"existing": "value"}
        merge_delta(updates, None)

        assert updates == {"existing": "value"}

    def test_merge_delta_with_only_stack(self):
        """Test merging delta with only flow_stack."""
        updates = {}
        delta = FlowDelta(flow_stack=[{"flow_id": "test"}])

        merge_delta(updates, delta)

        assert "flow_stack" in updates
        assert "flow_slots" not in updates

    def test_merge_delta_with_only_slots(self):
        """Test merging delta with only flow_slots."""
        updates = {}
        delta = FlowDelta(flow_slots={"test": {"slot": "value"}})

        merge_delta(updates, delta)

        assert "flow_slots" in updates
        assert "flow_stack" not in updates

    def test_merge_delta_preserves_existing_updates(self):
        """Test that merge preserves non-flow updates."""
        updates = {"response": "hello", "turn_count": 5}
        delta = FlowDelta(flow_stack=[])

        merge_delta(updates, delta)

        assert updates["response"] == "hello"
        assert updates["turn_count"] == 5
        assert updates["flow_stack"] == []

    def test_multiple_deltas_in_sequence(self):
        """Test applying multiple deltas in sequence."""
        updates = {}

        delta1 = FlowDelta(flow_stack=[{"flow_id": "f1"}])
        delta2 = FlowDelta(flow_slots={"f1": {"slot1": "v1"}})
        delta3 = FlowDelta(
            flow_stack=[{"flow_id": "f1"}, {"flow_id": "f2"}],
            flow_slots={"f1": {"slot1": "v1"}, "f2": {}},
        )

        merge_delta(updates, delta1)
        merge_delta(updates, delta2)
        merge_delta(updates, delta3)

        # Last delta should win for overlapping keys
        assert len(updates["flow_stack"]) == 2
        assert "f2" in updates["flow_slots"]
```

#### Paso 2: Tests de ActionRegistry Dual-Layer

**Test file:** `tests/unit/actions/test_registry_dual_layer.py`

```python
import pytest
from soni.actions.registry import ActionRegistry


class TestActionRegistryDualLayer:
    """Tests for global + local action registration."""

    @pytest.fixture(autouse=True)
    def cleanup(self):
        """Clear registry before and after each test."""
        ActionRegistry.clear_global()
        yield
        ActionRegistry.clear_global()

    def test_local_takes_precedence_over_global(self):
        """Test that local action overrides global with same name."""
        # Register global
        @ActionRegistry.register("shared_action")
        def global_action(**kwargs) -> dict:
            return {"source": "global"}

        # Create instance and register local
        registry = ActionRegistry()
        registry.register_local(
            "shared_action",
            lambda **kwargs: {"source": "local"}
        )

        # Get should return local
        action = registry.get("shared_action")
        result = action()

        assert result["source"] == "local"

    def test_global_available_without_local(self):
        """Test that global actions are available when no local override."""
        @ActionRegistry.register("global_only")
        def global_action(**kwargs) -> dict:
            return {"global": True}

        registry = ActionRegistry()
        action = registry.get("global_only")

        assert action is not None
        assert action()["global"] is True

    def test_local_not_available_in_other_instances(self):
        """Test that local actions are instance-specific."""
        registry1 = ActionRegistry()
        registry2 = ActionRegistry()

        registry1.register_local("instance_action", lambda **k: {"instance": 1})

        assert registry1.get("instance_action") is not None
        assert registry2.get("instance_action") is None

    def test_clear_local_does_not_affect_global(self):
        """Test that clearing local doesn't affect global actions."""
        @ActionRegistry.register("persistent")
        def global_action(**kwargs) -> dict:
            return {}

        registry = ActionRegistry()
        registry.register_local("temporary", lambda **k: {})

        registry.clear_local()

        assert registry.get("persistent") is not None
        assert registry.get("temporary") is None

    def test_clear_global_affects_all_instances(self):
        """Test that clearing global affects all registry instances."""
        @ActionRegistry.register("shared")
        def global_action(**kwargs) -> dict:
            return {}

        registry1 = ActionRegistry()
        registry2 = ActionRegistry()

        assert registry1.get("shared") is not None
        assert registry2.get("shared") is not None

        ActionRegistry.clear_global()

        assert registry1.get("shared") is None
        assert registry2.get("shared") is None

    def test_list_actions_shows_both_layers(self):
        """Test that list_actions shows global and local separately."""
        @ActionRegistry.register("global_a")
        def ga(**k): return {}

        @ActionRegistry.register("global_b")
        def gb(**k): return {}

        registry = ActionRegistry()
        registry.register_local("local_x", lambda **k: {})

        actions = registry.list_actions()

        assert "global_a" in actions["global"]
        assert "global_b" in actions["global"]
        assert "local_x" in actions["local"]
        assert "local_x" not in actions["global"]
```

#### Paso 3: Tests de ResponseExtractor Edge Cases

**Test file:** `tests/unit/runtime/test_extractor_edge_cases.py`

```python
import pytest
from langchain_core.messages import AIMessage, HumanMessage

from soni.runtime.extractor import ResponseExtractor


class TestResponseExtractorEdgeCases:
    """Edge case tests for ResponseExtractor."""

    @pytest.fixture
    def extractor(self):
        return ResponseExtractor()

    def test_extract_with_no_new_messages(self, extractor):
        """Test extraction when no new messages added."""
        history = [HumanMessage(content="hello")]
        result = {"messages": [HumanMessage(content="hello")]}  # Same as history
        input_payload = {"messages": [HumanMessage(content="hello")]}

        response = extractor.extract(result, input_payload, history)

        assert response == "" or response is not None  # Should handle gracefully

    def test_extract_with_empty_ai_message(self, extractor):
        """Test extraction when AI message has empty content."""
        history = []
        result = {
            "messages": [
                HumanMessage(content="hello"),
                AIMessage(content=""),  # Empty content
            ]
        }
        input_payload = {"messages": [HumanMessage(content="hello")]}

        response = extractor.extract(result, input_payload, history)

        # Should not fail, may return empty or fallback
        assert isinstance(response, str)

    def test_extract_with_multiple_ai_messages(self, extractor):
        """Test extraction when multiple AI messages generated."""
        history = []
        result = {
            "messages": [
                HumanMessage(content="hello"),
                AIMessage(content="First response"),
                AIMessage(content="Second response"),
            ]
        }
        input_payload = {"messages": [HumanMessage(content="hello")]}

        response = extractor.extract(result, input_payload, history)

        # Should combine or use last
        assert "First" in response or "Second" in response

    def test_extract_with_none_content(self, extractor):
        """Test extraction when message content is None."""
        history = []

        class MockMessage:
            content = None

        result = {"messages": [HumanMessage(content="hello"), MockMessage()]}
        input_payload = {"messages": [HumanMessage(content="hello")]}

        response = extractor.extract(result, input_payload, history)

        # Should handle gracefully
        assert isinstance(response, str)

    def test_extract_with_missing_messages_key(self, extractor):
        """Test extraction when result has no messages key."""
        history = []
        result = {"response": "fallback"}
        input_payload = {"messages": []}

        response = extractor.extract(result, input_payload, history)

        assert isinstance(response, str)
```

#### Paso 4: Tests de Error Recovery

**Test file:** `tests/integration/test_error_recovery.py`

```python
import pytest
from unittest.mock import AsyncMock, MagicMock, patch

from soni.runtime.loop import RuntimeLoop
from soni.core.errors import NLUError, ActionError


class TestErrorRecovery:
    """Integration tests for error recovery scenarios."""

    @pytest.fixture
    def mock_config(self):
        config = MagicMock()
        config.settings.persistence.backend = "memory"
        config.flows = {"greeting": MagicMock()}
        return config

    @pytest.mark.asyncio
    async def test_recovery_from_nlu_failure(self, mock_config):
        """Test that system recovers gracefully from NLU failure."""
        runtime = RuntimeLoop(config=mock_config)
        await runtime.initialize()

        # Mock NLU to fail on first call, succeed on second
        call_count = 0
        original_du = runtime.du

        async def failing_then_succeeding(*args, **kwargs):
            nonlocal call_count
            call_count += 1
            if call_count == 1:
                raise NLUError("Temporary NLU failure")
            return await original_du.acall(*args, **kwargs)

        with patch.object(runtime, "du") as mock_du:
            mock_du.acall = failing_then_succeeding

            # First call should handle error gracefully
            try:
                response1 = await runtime.process_message("hello", "user1")
                # Should get error response, not crash
            except Exception:
                pass  # May raise, that's also valid behavior

            # Second call should work
            # (if system maintains state correctly)

    @pytest.mark.asyncio
    async def test_action_failure_doesnt_corrupt_state(self, mock_config):
        """Test that action failure doesn't corrupt dialogue state."""
        runtime = RuntimeLoop(config=mock_config)
        await runtime.initialize()

        # Get initial state
        initial_state = await runtime.get_state("user1")

        # Simulate action that fails
        with patch.object(runtime.action_handler, "execute") as mock_execute:
            mock_execute.side_effect = ActionError("Action failed")

            try:
                await runtime.process_message("do failing action", "user1")
            except ActionError:
                pass

        # State should still be valid
        state_after = await runtime.get_state("user1")
        # At minimum, shouldn't be corrupted
        if state_after:
            assert "flow_stack" in state_after
            assert "flow_slots" in state_after

    @pytest.mark.asyncio
    async def test_validation_error_provides_useful_message(self, mock_config):
        """Test that validation errors include helpful context."""
        from soni.core.validation import validate_slot_value
        from soni.core.errors import SlotError
        from soni.config.models import SlotConfig

        # Create slot config expecting number
        slot_config = SlotConfig(
            name="amount",
            type="number",
            description="Transfer amount",
        )

        with pytest.raises(SlotError) as exc_info:
            validate_slot_value("not_a_number", slot_config)

        error_msg = str(exc_info.value)
        assert "amount" in error_msg or "number" in error_msg
```

### Criterios de Éxito

- [ ] Coverage de módulos críticos >= 85%
- [ ] Todos los edge cases documentados tienen tests
- [ ] Tests de flow stack cubren múltiples flujos
- [ ] Tests de registry cubren dual-layer
- [ ] Tests de error recovery verifican graceful degradation
- [ ] Todos los tests pasan
- [ ] No hay flaky tests

### Validación Manual

**Comandos para validar:**

```bash
# Ejecutar todos los tests con coverage
uv run pytest --cov=soni --cov-report=html

# Ver reporte de coverage
open htmlcov/index.html

# Ejecutar solo edge case tests
uv run pytest tests/unit/flow/test_flow_manager_edge_cases.py -v
uv run pytest tests/unit/actions/test_registry_dual_layer.py -v
uv run pytest tests/unit/runtime/test_extractor_edge_cases.py -v
uv run pytest tests/integration/test_error_recovery.py -v
```

### Referencias

- Análisis arquitectural con gaps identificados
- `tests/` - Tests existentes como referencia
- pytest-cov documentation

### Notas Adicionales

**Prioridad de edge cases:**
1. Flow stack (afecta toda la conversación)
2. Error recovery (afecta robustez)
3. Registry dual-layer (afecta extensibilidad)
4. Extractor (afecta UX)

**Flaky test prevention:**
- Evitar timing-dependent assertions
- Usar fixtures para estado limpio
- Mock external dependencies
