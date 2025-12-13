## Task: DM-002 - Eliminate Magic Strings with Enums

**ID de tarea:** DM-002
**Hito:** Dialog Manager Enterprise Hardening
**Dependencias:** Ninguna (puede ejecutarse en paralelo con DM-001)
**Duración estimada:** 3 horas

### Objetivo

Reemplazar todos los strings literales ("confirming", "execute_action", "generate_response", etc.) con `StrEnum` para prevenir bugs silenciosos por typos y mejorar autocompletado en IDEs.

### Contexto

El código actual usa strings mágicos en ~50+ lugares:
- `conversation_state` values: "confirming", "waiting_for_slot", "ready_for_action", etc.
- Node names: "execute_action", "generate_response", "validate_slot", etc.
- Message types: "slot_value", "correction", "modification", etc.

Un typo como `"confirmng"` pasaría silenciosamente y causaría bugs difíciles de detectar. Enums proporcionan:
- Validación en tiempo de compilación (con mypy)
- Autocompletado en IDEs
- Refactoring seguro
- Documentación implícita de valores válidos

### Entregables

- [ ] Crear `ConversationState` enum en `src/soni/core/constants.py`
- [ ] Crear `NodeName` enum para nombres de nodos
- [ ] Crear `MessageType` enum (si no existe o extender existente)
- [ ] Migrar `routing.py` a usar enums
- [ ] Migrar `graph.py` y `builder.py` a usar enums
- [ ] Actualizar todos los tests afectados

### Implementación Detallada

#### Paso 1: Crear enums en core/constants.py

**Archivo(s) a crear/modificar:** `src/soni/core/constants.py`

**Código específico:**

```python
from enum import StrEnum


class ConversationState(StrEnum):
    """Valid conversation states for the dialogue manager."""

    IDLE = "idle"
    UNDERSTANDING = "understanding"
    WAITING_FOR_SLOT = "waiting_for_slot"
    READY_FOR_CONFIRMATION = "ready_for_confirmation"
    CONFIRMING = "confirming"
    READY_FOR_ACTION = "ready_for_action"
    GENERATING_RESPONSE = "generating_response"
    COMPLETED = "completed"
    ERROR = "error"


class NodeName(StrEnum):
    """Valid node names in the dialogue graph."""

    UNDERSTAND = "understand"
    VALIDATE_SLOT = "validate_slot"
    COLLECT_NEXT_SLOT = "collect_next_slot"
    CONFIRM_ACTION = "confirm_action"
    EXECUTE_ACTION = "execute_action"
    GENERATE_RESPONSE = "generate_response"
    HANDLE_DIGRESSION = "handle_digression"
    HANDLE_CORRECTION = "handle_correction"
    HANDLE_MODIFICATION = "handle_modification"
    HANDLE_CONFIRMATION = "handle_confirmation"
    HANDLE_INTENT_CHANGE = "handle_intent_change"
    HANDLE_CLARIFICATION = "handle_clarification"
    HANDLE_CANCELLATION = "handle_cancellation"


class MessageType(StrEnum):
    """NLU message type classifications."""

    SLOT_VALUE = "slot_value"
    CORRECTION = "correction"
    MODIFICATION = "modification"
    INTERRUPTION = "interruption"
    INTENT_CHANGE = "intent_change"
    CLARIFICATION = "clarification"
    DIGRESSION = "digression"
    QUESTION = "question"
    CANCELLATION = "cancellation"
    CONFIRMATION = "confirmation"
    CONTINUATION = "continuation"
```

#### Paso 2: Migrar routing.py

**Archivo(s) a modificar:** `src/soni/dm/routing.py`

**Antes:**
```python
if conv_state == "confirming":
    return "handle_confirmation"
```

**Después:**
```python
from soni.core.constants import ConversationState, NodeName

if conv_state == ConversationState.CONFIRMING:
    return NodeName.HANDLE_CONFIRMATION
```

#### Paso 3: Actualizar type hints en DialogueState

**Archivo(s) a modificar:** `src/soni/core/state.py`

```python
from soni.core.constants import ConversationState

class DialogueState(TypedDict, total=False):
    conversation_state: ConversationState | str  # Allow both during migration
    # ... rest of fields
```

### TDD Cycle (MANDATORY for new features)

#### Red Phase: Write Failing Tests

**Test file:** `tests/unit/core/test_constants.py`

```python
import pytest
from soni.core.constants import ConversationState, NodeName, MessageType


class TestConversationState:
    """Test ConversationState enum."""

    def test_all_states_are_strings(self):
        """Verify all states can be used as strings."""
        for state in ConversationState:
            assert isinstance(state.value, str)
            assert state == state.value  # StrEnum comparison

    def test_confirming_value(self):
        """Test specific state value."""
        assert ConversationState.CONFIRMING == "confirming"

    def test_invalid_state_raises(self):
        """Test that invalid string doesn't match any state."""
        invalid = "confirmng"  # typo
        assert invalid not in [s.value for s in ConversationState]


class TestNodeName:
    """Test NodeName enum."""

    def test_all_routing_targets_exist(self):
        """Verify all routing targets are valid node names."""
        required_nodes = {
            "execute_action", "confirm_action", "collect_next_slot",
            "generate_response", "validate_slot", "handle_confirmation",
        }
        node_values = {n.value for n in NodeName}
        assert required_nodes <= node_values
```

### Criterios de Éxito

- [ ] Todos los strings mágicos reemplazados con enums
- [ ] mypy pasa sin errores
- [ ] IDE muestra autocompletado para estados y nodos
- [ ] Todos los tests existentes siguen pasando
- [ ] Nuevos tests validan completitud de enums
- [ ] No hay regresiones en comportamiento

### Validación Manual

**Comandos para validar:**

```bash
uv run pytest tests/ -v
uv run mypy src/soni/core/constants.py src/soni/dm/routing.py
uv run ruff check src/soni/
```

### Referencias

- [Python StrEnum](https://docs.python.org/3/library/enum.html#enum.StrEnum)
- [routing.py](file:///Users/jorge/Projects/Playground/soni/src/soni/dm/routing.py)

### Notas Adicionales

- StrEnum permite comparación directa con strings: `state == "confirming"` sigue funcionando
- Migración puede ser gradual: type hints aceptan `State | str` durante transición
- Considerar añadir `@verify` decorator para validar estados en runtime
