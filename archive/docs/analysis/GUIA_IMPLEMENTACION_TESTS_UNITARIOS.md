# Guía de Implementación de Tests Unitarios

**Fecha**: 2025-12-10
**Complementa**: `ANALISIS_TESTS_UNITARIOS_COBERTURA.md`
**Objetivo**: Proporcionar guías prácticas y ejemplos concretos para implementar tests unitarios deterministas

---

## 1. Guía de Referencia Rápida

### 1.1 Fixtures Comunes (conftest.py)

Estos fixtures deben estar disponibles en `tests/unit/conftest.py` para reutilización:

```python
"""Common fixtures for unit tests."""

import pytest
from unittest.mock import AsyncMock, MagicMock
from soni.core.state import create_empty_state
from soni.du.models import NLUOutput, MessageType, SlotValue


# === NLU MOCKING FIXTURES ===

@pytest.fixture
def create_nlu_mock():
    """
    Factory fixture to create NLU mocks with specific message_type.

    Usage:
        def test_something(create_nlu_mock):
            nlu = create_nlu_mock(MessageType.SLOT_VALUE, slots=[...])
    """
    def _create(message_type: MessageType, **kwargs):
        nlu = AsyncMock()
        nlu.predict.return_value = NLUOutput(
            message_type=message_type,
            command=kwargs.get("command", "continue"),
            slots=kwargs.get("slots", []),
            confidence=kwargs.get("confidence", 0.95),
            confirmation_value=kwargs.get("confirmation_value"),
            reasoning=kwargs.get("reasoning", "Mocked NLU response")
        )
        return nlu
    return _create


@pytest.fixture
def mock_nlu_slot_value():
    """Mock NLU returning SLOT_VALUE message type."""
    nlu = AsyncMock()
    nlu.predict.return_value = NLUOutput(
        message_type=MessageType.SLOT_VALUE,
        command="continue",
        slots=[SlotValue(name="origin", value="Madrid", confidence=0.95)],
        confidence=0.95,
        reasoning="User provided slot value"
    )
    return nlu


@pytest.fixture
def mock_nlu_correction():
    """Mock NLU returning CORRECTION message type."""
    nlu = AsyncMock()
    nlu.predict.return_value = NLUOutput(
        message_type=MessageType.CORRECTION,
        command="continue",
        slots=[SlotValue(name="destination", value="Barcelona", confidence=0.95)],
        confidence=0.95,
        reasoning="User is correcting a slot"
    )
    return nlu


@pytest.fixture
def mock_nlu_modification():
    """Mock NLU returning MODIFICATION message type."""
    nlu = AsyncMock()
    nlu.predict.return_value = NLUOutput(
        message_type=MessageType.MODIFICATION,
        command="continue",
        slots=[SlotValue(name="destination", value="Valencia", confidence=0.95)],
        confidence=0.95,
        reasoning="User is modifying a slot"
    )
    return nlu


@pytest.fixture
def mock_nlu_confirmation_yes():
    """Mock NLU returning YES confirmation."""
    nlu = AsyncMock()
    nlu.predict.return_value = NLUOutput(
        message_type=MessageType.CONFIRMATION,
        command="continue",
        confirmation_value=True,
        confidence=0.95,
        reasoning="User confirmed with yes"
    )
    return nlu


@pytest.fixture
def mock_nlu_confirmation_no():
    """Mock NLU returning NO confirmation."""
    nlu = AsyncMock()
    nlu.predict.return_value = NLUOutput(
        message_type=MessageType.CONFIRMATION,
        command="continue",
        confirmation_value=False,
        confidence=0.95,
        reasoning="User denied with no"
    )
    return nlu


@pytest.fixture
def mock_nlu_confirmation_unclear():
    """Mock NLU returning UNCLEAR confirmation."""
    nlu = AsyncMock()
    nlu.predict.return_value = NLUOutput(
        message_type=MessageType.CONFIRMATION,
        command="continue",
        confirmation_value=None,
        confidence=0.50,
        reasoning="Unclear confirmation response"
    )
    return nlu


@pytest.fixture
def mock_nlu_intent_change():
    """Mock NLU returning INTENT_CHANGE message type."""
    nlu = AsyncMock()
    nlu.predict.return_value = NLUOutput(
        message_type=MessageType.INTENT_CHANGE,
        command="book_hotel",
        slots=[],
        confidence=0.95,
        reasoning="User wants to change to a new flow"
    )
    return nlu


@pytest.fixture
def mock_nlu_digression():
    """Mock NLU returning QUESTION/HELP message type."""
    nlu = AsyncMock()
    nlu.predict.return_value = NLUOutput(
        message_type=MessageType.QUESTION,
        command="help",
        slots=[],
        confidence=0.90,
        reasoning="User asked a question"
    )
    return nlu


# === STATE CREATION FIXTURES ===

@pytest.fixture
def create_state_with_flow():
    """
    Factory fixture to create a state with an active flow.

    Usage:
        def test_something(create_state_with_flow):
            state = create_state_with_flow("book_flight", current_step="collect_origin")
    """
    def _create(flow_name: str, flow_id: str = "flow_1", **kwargs):
        state = create_empty_state()
        state["flow_stack"] = [{
            "flow_id": flow_id,
            "flow_name": flow_name,
            "current_step": kwargs.get("current_step", "collect_slot"),
            "flow_state": kwargs.get("flow_state", "active"),
            "started_at": "2025-12-10T10:00:00Z",
        }]
        state["flow_slots"] = {flow_id: kwargs.get("slots", {})}
        state["conversation_state"] = kwargs.get("conversation_state", "waiting_for_slot")
        state["metadata"] = kwargs.get("metadata", {})
        return state
    return _create


@pytest.fixture
def create_state_with_slots():
    """
    Factory fixture to create a state with pre-filled slots.

    Usage:
        def test_something(create_state_with_slots):
            state = create_state_with_slots(
                "book_flight",
                slots={"origin": "Madrid", "destination": "Barcelona"}
            )
    """
    def _create(flow_name: str, slots: dict, flow_id: str = "flow_1", **kwargs):
        state = create_empty_state()
        state["flow_stack"] = [{
            "flow_id": flow_id,
            "flow_name": flow_name,
            "current_step": kwargs.get("current_step", "collect_slot"),
            "flow_state": "active",
            "started_at": "2025-12-10T10:00:00Z",
        }]
        state["flow_slots"] = {flow_id: slots.copy()}
        state["conversation_state"] = kwargs.get("conversation_state", "waiting_for_slot")
        state["metadata"] = kwargs.get("metadata", {})
        return state
    return _create


# === RUNTIME/CONTEXT MOCKING FIXTURES ===

@pytest.fixture
def mock_runtime():
    """
    Mock NodeRuntime with all dependencies.

    Usage:
        async def test_something(mock_runtime):
            result = await some_node(state, mock_runtime)
    """
    runtime = MagicMock()

    # Mock flow_manager
    mock_flow_manager = MagicMock()
    mock_flow_manager.get_active_context.return_value = {
        "flow_id": "flow_1",
        "flow_name": "book_flight",
        "current_step": "collect_origin",
        "flow_state": "active",
    }

    # Mock step_manager
    mock_step_manager = MagicMock()
    mock_step_manager.advance_to_next_step.return_value = {
        "flow_stack": [],
        "conversation_state": "waiting_for_slot",
    }

    # Mock normalizer
    mock_normalizer = AsyncMock()
    mock_normalizer.normalize_slot.return_value = "normalized_value"

    # Mock config
    mock_config = MagicMock()
    mock_config.flows = {}
    mock_config.responses = {}

    # Assemble context
    runtime.context = {
        "flow_manager": mock_flow_manager,
        "step_manager": mock_step_manager,
        "normalizer": mock_normalizer,
        "config": mock_config,
    }

    return runtime


@pytest.fixture
def mock_normalizer_success():
    """Mock normalizer that always succeeds."""
    normalizer = AsyncMock()
    normalizer.normalize_slot.side_effect = lambda slot_name, value: value
    return normalizer


@pytest.fixture
def mock_normalizer_failure():
    """Mock normalizer that always fails."""
    normalizer = AsyncMock()
    normalizer.normalize_slot.side_effect = ValueError("Normalization failed")
    return normalizer


# === CONFIGURATION MOCKING FIXTURES ===

@pytest.fixture
def mock_flow_config():
    """
    Factory fixture to create mock flow configurations.

    Usage:
        def test_something(mock_flow_config):
            config = mock_flow_config("book_flight", steps=[...])
    """
    def _create(flow_name: str, steps: list):
        from soni.core.types import FlowConfig, StepConfig

        step_configs = []
        for step_data in steps:
            step_configs.append(StepConfig(
                step=step_data.get("step", "step_1"),
                type=step_data.get("type", "collect"),
                slot=step_data.get("slot"),
                prompt=step_data.get("prompt"),
                action=step_data.get("action"),
            ))

        return FlowConfig(
            name=flow_name,
            steps=step_configs
        )
    return _create
```

---

## 2. Patrones de Mocking por Patrón Conversacional

### 2.1 Patrón: Corrección de Slots

**Escenario**: Usuario corrige un slot previamente proporcionado.

```python
@pytest.mark.asyncio
async def test_correction_during_collection(
    create_state_with_slots,
    mock_nlu_correction,
    mock_runtime
):
    """
    Test que el usuario puede corregir un slot durante la colección.

    Flujo:
    1. Usuario ya proporcionó origin="Madrid"
    2. Usuario dice "Actually, I meant Barcelona" (NLU detecta CORRECTION)
    3. Sistema actualiza origin="Barcelona"
    4. Sistema vuelve al paso donde estaba
    """
    # Arrange - Estado con slot ya lleno
    state = create_state_with_slots(
        "book_flight",
        slots={"origin": "Madrid"},
        current_step="collect_destination",
        conversation_state="waiting_for_slot"
    )

    # Mock NLU result (ya viene del fixture en format dict)
    state["nlu_result"] = mock_nlu_correction.predict.return_value.model_dump()

    # Mock normalizer para retornar valor determinista
    mock_runtime.context["normalizer"].normalize_slot.return_value = "Barcelona"

    # Act
    from soni.dm.nodes.handle_correction import handle_correction_node
    result = await handle_correction_node(state, mock_runtime)

    # Assert - Verificar corrección
    assert result["flow_slots"]["flow_1"]["destination"] == "Barcelona"
    assert result["metadata"]["_correction_slot"] == "destination"
    assert result["metadata"]["_correction_value"] == "Barcelona"
    assert "correction_acknowledged" in result.get("last_response", "").lower() or "updated" in result.get("last_response", "").lower()
```

### 2.2 Patrón: Modificación de Slots

**Escenario**: Usuario modifica intencionalmente un slot.

```python
@pytest.mark.asyncio
async def test_modification_after_denial(
    create_state_with_slots,
    mock_nlu_modification,
    mock_runtime
):
    """
    Test modificación después de negar confirmación.

    Flujo:
    1. Usuario tiene slots llenos: origin="Madrid", destination="Barcelona"
    2. Sistema pregunta confirmación
    3. Usuario dice "No" (niega confirmación)
    4. Sistema pregunta "What would you like to change?"
    5. Usuario dice "Valencia" (NLU detecta MODIFICATION de destination)
    6. Sistema actualiza destination="Valencia" y vuelve a confirmación
    """
    # Arrange
    state = create_state_with_slots(
        "book_flight",
        slots={"origin": "Madrid", "destination": "Barcelona"},
        current_step="confirm_booking",
        conversation_state="understanding"  # Después de negar
    )
    state["nlu_result"] = mock_nlu_modification.predict.return_value.model_dump()

    # Mock normalizer
    mock_runtime.context["normalizer"].normalize_slot.return_value = "Valencia"

    # Act
    from soni.dm.nodes.handle_modification import handle_modification_node
    result = await handle_modification_node(state, mock_runtime)

    # Assert
    assert result["flow_slots"]["flow_1"]["destination"] == "Valencia"
    assert result["metadata"]["_modification_slot"] == "destination"
    assert "_correction_slot" not in result["metadata"]  # No debe tener correction flags
```

### 2.3 Patrón: Confirmación (Yes/No/Unclear)

**Escenario**: Sistema pide confirmación y usuario responde.

```python
@pytest.mark.asyncio
async def test_confirmation_yes_proceeds_to_action(
    create_state_with_slots,
    mock_nlu_confirmation_yes,
    mock_runtime
):
    """Test que confirmación positiva procede a ejecutar acción."""
    # Arrange
    state = create_state_with_slots(
        "book_flight",
        slots={"origin": "Madrid", "destination": "Barcelona"},
        current_step="confirm_booking",
        conversation_state="confirming"
    )
    state["nlu_result"] = mock_nlu_confirmation_yes.predict.return_value.model_dump()

    # Act
    from soni.dm.nodes.handle_confirmation import handle_confirmation_node
    result = await handle_confirmation_node(state, mock_runtime)

    # Assert
    assert result["conversation_state"] == "ready_for_action"
    assert "_confirmation_attempts" not in result.get("metadata", {})


@pytest.mark.asyncio
async def test_confirmation_unclear_increments_attempts(
    create_state_with_slots,
    mock_nlu_confirmation_unclear,
    mock_runtime
):
    """Test que respuesta unclear incrementa contador de intentos."""
    # Arrange
    state = create_state_with_slots(
        "book_flight",
        slots={"origin": "Madrid", "destination": "Barcelona"},
        current_step="confirm_booking",
        conversation_state="confirming",
        metadata={"_confirmation_attempts": 1}
    )
    state["nlu_result"] = mock_nlu_confirmation_unclear.predict.return_value.model_dump()

    # Act
    from soni.dm.nodes.handle_confirmation import handle_confirmation_node
    result = await handle_confirmation_node(state, mock_runtime)

    # Assert
    assert result["conversation_state"] == "confirming"
    assert result["metadata"]["_confirmation_attempts"] == 2
    assert "didn't understand" in result.get("last_response", "").lower()


@pytest.mark.asyncio
async def test_confirmation_max_retries_triggers_error(
    create_state_with_slots,
    mock_nlu_confirmation_unclear,
    mock_runtime
):
    """Test que exceder max retries dispara estado de error."""
    # Arrange
    state = create_state_with_slots(
        "book_flight",
        slots={"origin": "Madrid", "destination": "Barcelona"},
        current_step="confirm_booking",
        conversation_state="confirming",
        metadata={"_confirmation_attempts": 3}  # Ya en el máximo
    )
    state["nlu_result"] = mock_nlu_confirmation_unclear.predict.return_value.model_dump()

    # Act
    from soni.dm.nodes.handle_confirmation import handle_confirmation_node
    result = await handle_confirmation_node(state, mock_runtime)

    # Assert
    assert result["conversation_state"] == "error"
    assert "_confirmation_attempts" not in result.get("metadata", {})
    assert "trouble understanding" in result.get("last_response", "").lower()
```

### 2.4 Patrón: Corrección Durante Confirmación

**Escenario**: Usuario corrige un slot mientras se está confirmando.

```python
@pytest.mark.asyncio
async def test_correction_during_confirmation(
    create_state_with_slots,
    mock_nlu_correction,
    mock_runtime
):
    """
    Test corrección durante confirmación re-genera mensaje de confirmación.

    Flujo:
    1. Sistema: "You want to fly from Madrid to Barcelona, correct?"
    2. Usuario: "No, I meant Valencia" (CORRECTION durante CONFIRMING)
    3. Sistema: "Got it, I've updated destination to Valencia. [Nueva confirmación]"
    """
    # Arrange
    state = create_state_with_slots(
        "book_flight",
        slots={"origin": "Madrid", "destination": "Barcelona"},
        current_step="confirm_booking",
        conversation_state="confirming"
    )
    state["nlu_result"] = mock_nlu_correction.predict.return_value.model_dump()

    # Override NLU to correct destination
    state["nlu_result"]["slots"] = [{"name": "destination", "value": "Valencia"}]

    mock_runtime.context["normalizer"].normalize_slot.return_value = "Valencia"

    # Act
    from soni.dm.nodes.handle_correction import handle_correction_node
    result = await handle_correction_node(state, mock_runtime)

    # Assert
    assert result["flow_slots"]["flow_1"]["destination"] == "Valencia"
    assert result["conversation_state"] == "ready_for_confirmation"
    assert result["current_step"] == "confirm_booking"  # Vuelve a confirmación
```

### 2.5 Patrón: Routing Basado en NLU

**Escenario**: Routing decide siguiente nodo basado en message_type.

```python
def test_route_after_understand_slot_value(create_state_with_flow):
    """Test routing con SLOT_VALUE va a validate_slot."""
    # Arrange
    state = create_state_with_flow(
        "book_flight",
        current_step="collect_origin"
    )
    state["nlu_result"] = {
        "message_type": "slot_value",
        "command": "continue",
        "slots": [{"name": "origin", "value": "Madrid"}],
        "confidence": 0.95
    }

    # Act
    from soni.dm.routing import route_after_understand
    next_node = route_after_understand(state)

    # Assert
    assert next_node == "validate_slot"


def test_route_after_understand_correction(create_state_with_flow):
    """Test routing con CORRECTION va a handle_correction."""
    # Arrange
    state = create_state_with_flow("book_flight")
    state["nlu_result"] = {
        "message_type": "correction",
        "command": "continue",
        "slots": [{"name": "origin", "value": "Barcelona"}],
        "confidence": 0.95
    }

    # Act
    from soni.dm.routing import route_after_understand
    next_node = route_after_understand(state)

    # Assert
    assert next_node == "handle_correction"


def test_route_after_understand_slot_value_when_confirming_edge_case(
    create_state_with_slots
):
    """
    Test edge case: NLU detecta SLOT_VALUE pero estamos en confirming.

    Esto puede pasar cuando el usuario responde a confirmación con
    ambigüedad. El routing debe tratar esto como confirmación.
    """
    # Arrange
    state = create_state_with_slots(
        "book_flight",
        slots={"origin": "Madrid", "destination": "Barcelona"},
        current_step="confirm_booking",
        conversation_state="confirming"
    )
    state["nlu_result"] = {
        "message_type": "slot_value",  # NLU confundido
        "command": "continue",
        "slots": [{"name": "origin", "value": "Madrid"}],
        "confidence": 0.60
    }

    # Act
    from soni.dm.routing import route_after_understand
    next_node = route_after_understand(state)

    # Assert
    # Debe tratar como confirmación, no como slot_value
    assert next_node == "handle_confirmation"
```

---

## 3. Checklist de Validación por Módulo

### 3.1 Para `handle_correction.py`

**Antes de marcar como completo, verificar**:

- [ ] **Formatos de slots**
  - [ ] Test con SlotValue object
  - [ ] Test con dict format
  - [ ] Test con formato desconocido (error handling)

- [ ] **Edge cases**
  - [ ] Test sin NLU result
  - [ ] Test sin slots en NLU
  - [ ] Test sin active flow
  - [ ] Test normalization failure

- [ ] **Routing post-corrección**
  - [ ] Test vuelve a collect step correcto
  - [ ] Test vuelve a confirmation step
  - [ ] Test vuelve a action step
  - [ ] Test cuando todos los slots están llenos
  - [ ] Test cuando slots parciales

- [ ] **Estados previos**
  - [ ] Test desde ready_for_action
  - [ ] Test desde ready_for_confirmation
  - [ ] Test desde confirming
  - [ ] Test desde waiting_for_slot

- [ ] **Metadata y response**
  - [ ] Test setea _correction_slot y _correction_value
  - [ ] Test limpia _modification_slot si existe
  - [ ] Test mensaje de acknowledgment
  - [ ] Test template de config si existe
  - [ ] Test template default como fallback

### 3.2 Para `routing.py`

**Antes de marcar como completo, verificar**:

- [ ] **route_after_understand**
  - [ ] Test para cada MessageType (SLOT_VALUE, CORRECTION, MODIFICATION, CONFIRMATION, INTENT_CHANGE, QUESTION, HELP, CANCEL)
  - [ ] Test edge case: slot_value cuando confirming
  - [ ] Test edge case: slot_value cuando understanding post-denial
  - [ ] Test sin NLU result
  - [ ] Test message_type desconocido

- [ ] **route_after_validate**
  - [ ] Test slot válido -> siguiente paso
  - [ ] Test slot inválido -> re-colectar
  - [ ] Test todos los slots llenos -> confirmación o acción
  - [ ] Test necesita confirmación
  - [ ] Test ready for action

- [ ] **route_after_correction**
  - [ ] Test vuelve a collect
  - [ ] Test vuelve a confirmation
  - [ ] Test vuelve a action
  - [ ] Test error state

- [ ] **route_after_modification**
  - [ ] Test vuelve a collect
  - [ ] Test vuelve a confirmation
  - [ ] Test vuelve a action
  - [ ] Test error state

- [ ] **route_after_confirmation**
  - [ ] Test YES -> action
  - [ ] Test NO -> understanding
  - [ ] Test UNCLEAR -> confirming again
  - [ ] Test max retries

- [ ] **route_after_action**
  - [ ] Test success
  - [ ] Test failure
  - [ ] Test has next step
  - [ ] Test flow completed

### 3.3 Para `handle_confirmation.py`

**Antes de marcar como completo, verificar**:

- [ ] **Confirmación positiva**
  - [ ] Test YES procede a acción
  - [ ] Test limpia _confirmation_attempts

- [ ] **Confirmación negativa**
  - [ ] Test NO permite modificación
  - [ ] Test limpia _confirmation_attempts
  - [ ] Test mensaje apropiado

- [ ] **Respuesta unclear**
  - [ ] Test incrementa _confirmation_attempts
  - [ ] Test mensaje de re-prompt
  - [ ] Test conversation_state se mantiene en confirming

- [ ] **Max retries**
  - [ ] Test antes de max retries
  - [ ] Test al alcanzar max retries -> error
  - [ ] Test limpia _confirmation_attempts en error

- [ ] **Corrección durante confirmación**
  - [ ] Test actualiza slot
  - [ ] Test regenera confirmación
  - [ ] Test mensaje combinado (acknowledgment + confirmation)

### 3.4 Para `validate_slot.py`

**Antes de marcar como completo, verificar**:

- [ ] **Validación exitosa**
  - [ ] Test slot válido -> avanza
  - [ ] Test todos los slots llenos -> confirmation/action

- [ ] **Validación fallida**
  - [ ] Test slot inválido -> re-colecta
  - [ ] Test mensaje de error apropiado
  - [ ] Test no avanza paso

- [ ] **Normalización**
  - [ ] Test normalización exitosa
  - [ ] Test normalización fallida

- [ ] **Edge cases**
  - [ ] Test sin validator definido
  - [ ] Test validator returna None
  - [ ] Test validator lanza excepción

---

## 4. Métricas de Éxito

### 4.1 Métricas Primarias

| Métrica | Objetivo | Cómo Medir |
|---------|----------|------------|
| **Cobertura de líneas** | >85% | `pytest --cov=src/soni --cov-report=term-missing` |
| **Cobertura de branches** | >80% | `pytest --cov=src/soni --cov-branch` |
| **Tiempo de ejecución** | <10 min suite completa | `pytest tests/unit/ --durations=10` |
| **Tests pasando** | 100% | `pytest tests/unit/ -v` |

### 4.2 Métricas Secundarias

| Métrica | Objetivo | Cómo Medir | Herramienta |
|---------|----------|------------|-------------|
| **Complejidad ciclomática** | <10 por función | Radon | `radon cc src/soni -a` |
| **Mantenibilidad** | Índice >70 | Radon | `radon mi src/soni` |
| **Duplicación de código** | <5% | Code inspection | Manual / SonarQube |
| **Mutation score** | >70% | Mutmut | `mutmut run` |

### 4.3 Métricas de Calidad de Tests

| Métrica | Objetivo | Indicador |
|---------|----------|-----------|
| **Tiempo por test** | <1s por test unitario | Tests más lentos indican dependencias externas |
| **Flaky tests** | 0 tests flaky | Re-ejecutar suite 10 veces, debe pasar siempre |
| **Independencia** | 100% independientes | Ejecutar tests en orden aleatorio |
| **Determinismo** | 100% determinista | Ejecutar mismo test 100 veces, siempre mismo resultado |

### 4.4 Comandos de Validación

```bash
# Cobertura completa con branches
uv run pytest tests/unit/ --cov=src/soni --cov-branch --cov-report=term-missing --cov-report=html

# Tests más lentos (identificar problemas)
uv run pytest tests/unit/ --durations=20

# Ejecutar en orden aleatorio (verificar independencia)
uv run pytest tests/unit/ --random-order

# Verificar flaky tests (ejecutar múltiples veces)
for i in {1..10}; do uv run pytest tests/unit/ -q || break; done

# Complejidad ciclomática
uv run radon cc src/soni/dm -a -s

# Índice de mantenibilidad
uv run radon mi src/soni/dm
```

---

## 5. Tests Unitarios vs Tests de Integración

### 5.1 ¿Qué es un Test Unitario?

**Definición estricta para este proyecto**:

Un test unitario debe cumplir **TODOS** estos criterios:

1. **Aislamiento**: Prueba UNA función/método/clase en aislamiento
2. **Sin dependencias externas**: No usa LLM, DB, API, filesystem real
3. **Determinista**: Siempre mismo input → mismo output
4. **Rápido**: <1 segundo por test
5. **Independiente**: Puede ejecutarse solo, en cualquier orden
6. **Mocks para dependencias**: Todo lo externo está mockeado

**Ejemplos de tests UNITARIOS**:

```python
# ✅ Test unitario - Función pura con mock
def test_handle_correction_updates_slot(mock_runtime):
    """Test que handle_correction actualiza slot."""
    state = {"flow_slots": {"flow_1": {"origin": "Madrid"}}}
    state["nlu_result"] = {"slots": [{"name": "origin", "value": "Barcelona"}]}

    result = await handle_correction_node(state, mock_runtime)

    assert result["flow_slots"]["flow_1"]["origin"] == "Barcelona"

# ✅ Test unitario - Routing logic con estado mockeado
def test_route_after_understand_correction():
    """Test que routing con CORRECTION va a handle_correction."""
    state = {"nlu_result": {"message_type": "correction"}}

    next_node = route_after_understand(state)

    assert next_node == "handle_correction"

# ✅ Test unitario - Metadata manager
def test_metadata_manager_sets_correction_flags():
    """Test que metadata manager setea flags de corrección."""
    metadata = {}

    result = MetadataManager.set_correction_flags(metadata, "origin", "Barcelona")

    assert result["_correction_slot"] == "origin"
    assert result["_correction_value"] == "Barcelona"
```

### 5.2 ¿Qué es un Test de Integración?

**Definición para este proyecto**:

Un test de integración cumple **AL MENOS UNO** de estos criterios:

1. **Múltiples componentes**: Prueba interacción entre >2 componentes
2. **Dependencias reales**: Usa LLM real, DB real, filesystem real
3. **Flujo completo**: Prueba flujo end-to-end (ej: mensaje → respuesta)
4. **No determinista**: Puede fallar aleatoriamente (ej: timeout de API)
5. **Lento**: >1 segundo por test

**Ejemplos de tests de INTEGRACIÓN**:

```python
# ❌ NO es unitario - Usa LLM real
@pytest.mark.integration
async def test_nlu_understands_correction_real_llm():
    """Test que NLU real detecta correcciones."""
    nlu = SoniDU(lm=dspy.OpenAI(model="gpt-4"))  # LLM REAL

    result = await nlu.predict(
        user_message="No, I meant Barcelona",
        context={"previous_slot": {"origin": "Madrid"}}
    )

    assert result.message_type == MessageType.CORRECTION

# ❌ NO es unitario - Flujo completo E2E
@pytest.mark.integration
async def test_full_correction_flow():
    """Test flujo completo de corrección."""
    runtime = RuntimeLoop(config=load_config())  # Runtime REAL

    # Turn 1: Provide origin
    response1 = await runtime.process_turn("I want to fly from Madrid")
    assert "destination" in response1.lower()

    # Turn 2: Provide destination
    response2 = await runtime.process_turn("to Barcelona")
    assert "confirm" in response2.lower()

    # Turn 3: Correction
    response3 = await runtime.process_turn("Actually, I meant Valencia")
    assert "valencia" in response3.lower()

# ❌ NO es unitario - Usa múltiples componentes reales
@pytest.mark.integration
async def test_normalizer_with_real_llm():
    """Test normalizer con LLM real."""
    normalizer = Normalizer(lm=dspy.OpenAI(model="gpt-4"))

    result = await normalizer.normalize_slot("date", "tomorrow")

    assert isinstance(result, str)
```

### 5.3 Regla de Oro para Clasificación

**Si tu test necesita `@pytest.mark.asyncio` y usa `await` en LLM real → Es test de INTEGRACIÓN**

**Si tu test usa mocks para TODAS las dependencias → Es test UNITARIO**

### 5.4 Estructura de Directorios

```
tests/
├── unit/                           # Tests unitarios SOLAMENTE
│   ├── conftest.py                 # Fixtures para mocking
│   ├── test_dm_routing.py          # Routing con mocks
│   ├── test_handle_correction.py   # Correction node con mocks
│   └── ...
│
└── integration/                    # Tests de integración
    ├── conftest.py                 # Fixtures para LLM real
    ├── test_e2e.py                 # Flujos completos
    ├── test_nlu_two_stage.py       # NLU con LLM real
    └── ...
```

### 5.5 Decisión: ¿Unitario o Integración?

Usa este árbol de decisión:

```
¿Tu test necesita LLM real?
├─ SÍ → Test de INTEGRACIÓN
└─ NO
   └─ ¿Tu test prueba >1 componente real?
      ├─ SÍ → Test de INTEGRACIÓN
      └─ NO
         └─ ¿Tu test puede fallar por timeout/rate limit?
            ├─ SÍ → Test de INTEGRACIÓN
            └─ NO → Test UNITARIO ✅
```

---

## 6. Helpers para Crear Estados de Prueba

### 6.1 Helpers en conftest.py

```python
def create_state_with_correction_context(
    slot_to_correct: str,
    old_value: str,
    new_value: str
) -> dict:
    """
    Helper para crear estado preparado para corrección.

    Usage:
        state = create_state_with_correction_context(
            "destination", "Madrid", "Barcelona"
        )
    """
    state = create_empty_state()
    state["flow_stack"] = [{
        "flow_id": "flow_1",
        "flow_name": "book_flight",
        "current_step": "collect_slot",
        "flow_state": "active",
    }]
    state["flow_slots"] = {"flow_1": {slot_to_correct: old_value}}
    state["nlu_result"] = {
        "message_type": "correction",
        "command": "continue",
        "slots": [{"name": slot_to_correct, "value": new_value}],
        "confidence": 0.95
    }
    return state


def create_state_ready_for_confirmation(
    slots: dict,
    flow_name: str = "book_flight"
) -> dict:
    """
    Helper para crear estado listo para confirmación.

    Usage:
        state = create_state_ready_for_confirmation({
            "origin": "Madrid",
            "destination": "Barcelona"
        })
    """
    state = create_empty_state()
    state["flow_stack"] = [{
        "flow_id": "flow_1",
        "flow_name": flow_name,
        "current_step": "confirm_booking",
        "flow_state": "active",
    }]
    state["flow_slots"] = {"flow_1": slots.copy()}
    state["conversation_state"] = "ready_for_confirmation"
    return state


def create_state_with_metadata(
    metadata: dict,
    **state_kwargs
) -> dict:
    """
    Helper para crear estado con metadata específico.

    Usage:
        state = create_state_with_metadata(
            {"_confirmation_attempts": 2},
            flow_name="book_flight"
        )
    """
    state = create_empty_state()
    state["metadata"] = metadata.copy()
    # Apply other kwargs...
    return state
```

### 6.2 Builders Pattern

```python
class StateBuilder:
    """
    Builder pattern para crear estados complejos de forma fluida.

    Usage:
        state = (StateBuilder()
            .with_flow("book_flight")
            .with_slots({"origin": "Madrid"})
            .with_current_step("collect_destination")
            .with_metadata({"_confirmation_attempts": 1})
            .build())
    """

    def __init__(self):
        self.state = create_empty_state()

    def with_flow(self, flow_name: str, flow_id: str = "flow_1"):
        self.state["flow_stack"] = [{
            "flow_id": flow_id,
            "flow_name": flow_name,
            "current_step": "collect_slot",
            "flow_state": "active",
        }]
        self.state["flow_slots"] = {flow_id: {}}
        return self

    def with_slots(self, slots: dict, flow_id: str = "flow_1"):
        if flow_id not in self.state["flow_slots"]:
            self.state["flow_slots"][flow_id] = {}
        self.state["flow_slots"][flow_id].update(slots)
        return self

    def with_current_step(self, step: str):
        if self.state["flow_stack"]:
            self.state["flow_stack"][-1]["current_step"] = step
        return self

    def with_conversation_state(self, conv_state: str):
        self.state["conversation_state"] = conv_state
        return self

    def with_metadata(self, metadata: dict):
        self.state["metadata"] = metadata.copy()
        return self

    def with_nlu_result(self, nlu_result: dict):
        self.state["nlu_result"] = nlu_result
        return self

    def build(self):
        return self.state


# Ejemplo de uso
def test_with_builder():
    """Example using StateBuilder."""
    state = (StateBuilder()
        .with_flow("book_flight")
        .with_slots({"origin": "Madrid", "destination": "Barcelona"})
        .with_current_step("confirm_booking")
        .with_conversation_state("confirming")
        .with_metadata({"_confirmation_attempts": 1})
        .build())

    assert state["flow_slots"]["flow_1"]["origin"] == "Madrid"
    assert state["conversation_state"] == "confirming"
```

---

## 7. Próximos Pasos Prácticos

### Paso 1: Actualizar conftest.py

1. Abrir `tests/unit/conftest.py`
2. Agregar todos los fixtures de la sección 1.1
3. Agregar helpers de la sección 6.1
4. Agregar StateBuilder de la sección 6.2

### Paso 2: Crear Test Template

Crear `tests/unit/test_template.py` con estructura base:

```python
"""
Template para tests unitarios.

Copiar este archivo y renombrar para cada módulo a testear.
"""

import pytest
from unittest.mock import AsyncMock, MagicMock


# === TESTS DE FUNCIONALIDAD PRINCIPAL ===

@pytest.mark.asyncio
async def test_happy_path():
    """Test del camino feliz (caso más común)."""
    # Arrange

    # Act

    # Assert
    pass


# === TESTS DE EDGE CASES ===

@pytest.mark.asyncio
async def test_edge_case_empty_input():
    """Test con input vacío."""
    pass


@pytest.mark.asyncio
async def test_edge_case_none_input():
    """Test con input None."""
    pass


# === TESTS DE ERROR HANDLING ===

@pytest.mark.asyncio
async def test_error_handling_exception():
    """Test manejo de excepciones."""
    pass
```

### Paso 3: Implementar Fase CRÍTICA

Orden sugerido:

1. **Día 1-2**: `handle_correction.py`
   - Copiar template
   - Implementar tests usando fixtures
   - Validar con checklist 3.1
   - Ejecutar cobertura: `pytest tests/unit/test_handle_correction.py --cov=src/soni/dm/nodes/handle_correction --cov-report=term-missing`

2. **Día 3-4**: `handle_modification.py`
   - Copiar tests de correction (muy similar)
   - Ajustar para modification flags
   - Validar cobertura

3. **Día 5-7**: `routing.py`
   - Implementar tests de route_after_understand
   - Implementar tests de route_after_validate
   - Implementar tests de route_after_correction/modification
   - Validar cobertura

4. **Día 8-9**: `handle_confirmation.py`
   - Completar tests existentes
   - Agregar tests de corrección durante confirmación
   - Validar cobertura

5. **Día 10**: Validación de Fase CRÍTICA
   - Ejecutar suite completa
   - Verificar cobertura >78%
   - Revisar tests flaky

### Paso 4: Validación Continua

Después de cada módulo:

```bash
# 1. Ejecutar tests del módulo
uv run pytest tests/unit/test_MODULE.py -v

# 2. Verificar cobertura del módulo
uv run pytest tests/unit/test_MODULE.py --cov=src/soni/PATH/MODULE --cov-report=term-missing

# 3. Ejecutar suite completa
uv run pytest tests/unit/ -q

# 4. Verificar cobertura total
uv run pytest tests/unit/ --cov=src/soni --cov-report=term-missing

# 5. Verificar independencia (ejecutar en orden aleatorio)
uv run pytest tests/unit/ --random-order

# 6. Verificar velocidad
uv run pytest tests/unit/ --durations=10
```

---

**Documento generado**: 2025-12-10
**Complementa**: `ANALISIS_TESTS_UNITARIOS_COBERTURA.md`
**Versión**: 1.0
**Estado**: Listo para uso
