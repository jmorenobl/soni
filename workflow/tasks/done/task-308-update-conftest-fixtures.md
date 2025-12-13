## Task: 308 - Actualizar conftest.py con Fixtures para Tests Unitarios

**ID de tarea:** 308
**Hito:** Tests Unitarios - Cobertura >85%
**Dependencias:** Ninguna
**Duración estimada:** 2-3 horas

### Objetivo

Actualizar `tests/unit/conftest.py` con todos los fixtures necesarios para tests unitarios deterministas, incluyendo mocks de NLU, helpers de estado, y builders según la guía de implementación.

### Contexto

Según `docs/analysis/GUIA_IMPLEMENTACION_TESTS_UNITARIOS.md`, todos los tests unitarios deben usar fixtures comunes para:
- Mockear NLU de forma determinista (sin LLM real)
- Crear estados de prueba de forma consistente
- Mockear runtime context y dependencias

Esta tarea es prerrequisito para todas las demás tareas de tests unitarios.

### Entregables

- [ ] Fixtures de mocking de NLU (create_nlu_mock, mock_nlu_slot_value, mock_nlu_correction, etc.)
- [ ] Fixtures de creación de estado (create_state_with_flow, create_state_with_slots)
- [ ] Fixtures de runtime mocking (mock_runtime, mock_normalizer_success, mock_normalizer_failure)
- [ ] Fixtures de configuración (mock_flow_config)
- [ ] Helpers adicionales (create_state_with_correction_context, create_state_ready_for_confirmation)
- [ ] StateBuilder pattern implementado
- [ ] Documentación inline en cada fixture

### Implementación Detallada

#### Paso 1: Agregar Fixtures de NLU Mocking

**Archivo(s) a crear/modificar:** `tests/unit/conftest.py`

**Código específico:**

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
```

**Explicación:**
- Crear fixtures para todos los MessageType posibles
- Usar AsyncMock para métodos async
- Retornar NLUOutput con valores deterministas
- Incluir docstrings descriptivos

#### Paso 2: Agregar Fixtures de Estado

**Archivo(s) a crear/modificar:** `tests/unit/conftest.py`

**Código específico:**

```python
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
```

**Explicación:**
- Usar factory pattern para flexibilidad
- Permitir kwargs para personalización
- Copiar slots para evitar mutaciones

#### Paso 3: Agregar Fixtures de Runtime

**Archivo(s) a crear/modificar:** `tests/unit/conftest.py`

**Código específico:**

```python
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
```

**Explicación:**
- Mockear todas las dependencias del runtime
- Usar AsyncMock para métodos async
- Configurar valores de retorno por defecto

#### Paso 4: Agregar Helpers y StateBuilder

**Archivo(s) a crear/modificar:** `tests/unit/conftest.py`

**Código específico:**

```python
# === HELPER FUNCTIONS ===

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


# === STATE BUILDER PATTERN ===

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
```

**Explicación:**
- Helpers para casos comunes
- StateBuilder para casos complejos
- Métodos fluidos para legibilidad

#### Paso 5: Agregar Fixture de Flow Config Completo

**Archivo(s) a crear/modificar:** `tests/unit/conftest.py`

**Código específico:**

```python
# === CONFIGURATION MOCKING FIXTURES ===

@pytest.fixture
def mock_flow_config_complete():
    """
    Mock flow config con steps completos para testing.

    Útil para tests que necesitan verificar routing entre steps.

    Usage:
        def test_something(mock_flow_config_complete):
            config = mock_flow_config_complete
            assert len(config.steps) == 4
    """
    from soni.core.types import FlowConfig, StepConfig

    return FlowConfig(
        name="book_flight",
        steps=[
            StepConfig(step="collect_origin", type="collect", slot="origin", prompt="Where are you flying from?"),
            StepConfig(step="collect_destination", type="collect", slot="destination", prompt="Where to?"),
            StepConfig(step="collect_date", type="collect", slot="date", prompt="When?"),
            StepConfig(step="confirm_booking", type="confirm", prompt="Confirm: {origin} to {destination} on {date}?"),
            StepConfig(step="execute_booking", type="action", action="book_flight_action"),
        ]
    )


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

**Explicación:**
- Fixture predefinido con flow completo para casos comunes
- Factory fixture para crear flows customizados
- Incluye todos los tipos de steps (collect, confirm, action)

### Tests Requeridos

**Archivo de tests:** `tests/unit/test_conftest_fixtures.py` (opcional, para validar fixtures)

**Tests específicos a implementar:**

```python
# Tests opcionales para validar que fixtures funcionan
def test_create_nlu_mock_returns_correct_type(create_nlu_mock):
    """Test que create_nlu_mock retorna AsyncMock."""
    nlu = create_nlu_mock(MessageType.SLOT_VALUE)
    assert isinstance(nlu, AsyncMock)


def test_create_state_with_flow_creates_valid_state(create_state_with_flow):
    """Test que create_state_with_flow crea estado válido."""
    state = create_state_with_flow("book_flight")
    assert state["flow_stack"][0]["flow_name"] == "book_flight"
    assert "flow_1" in state["flow_slots"]


def test_state_builder_fluent_api():
    """Test que StateBuilder permite API fluida."""
    state = (StateBuilder()
        .with_flow("book_flight")
        .with_slots({"origin": "Madrid"})
        .build())
    assert state["flow_slots"]["flow_1"]["origin"] == "Madrid"
```

### Criterios de Éxito

- [ ] Todos los fixtures están implementados según la guía
- [ ] Fixtures tienen docstrings descriptivos
- [ ] StateBuilder implementa patrón fluido
- [ ] Helpers funcionan correctamente
- [ ] Tests opcionales pasan (si se implementan)
- [ ] Linting pasa sin errores
- [ ] Type checking pasa sin errores

### Validación Manual

**Comandos para validar:**

```bash
# Verificar que conftest.py no tiene errores de sintaxis
uv run python -m py_compile tests/unit/conftest.py

# Verificar imports
uv run python -c "from tests.unit.conftest import *; print('OK')"

# Ejecutar tests opcionales (si se crean)
uv run pytest tests/unit/test_conftest_fixtures.py -v
```

**Resultado esperado:**
- Conftest.py compila sin errores
- Todos los fixtures están disponibles
- Imports funcionan correctamente

### Referencias

- `docs/analysis/GUIA_IMPLEMENTACION_TESTS_UNITARIOS.md` - Sección 1.1 y 6
- `docs/analysis/ANALISIS_TESTS_UNITARIOS_COBERTURA.md` - Sección 6.2

### Notas Adicionales

- Esta tarea debe completarse ANTES de implementar tests unitarios
- Los fixtures deben seguir exactamente el formato de la guía
- Considerar agregar más fixtures según necesidad durante implementación
