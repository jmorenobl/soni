## Task: 4.2 - Routing Functions

**ID de tarea:** 402
**Hito:** Phase 4 - LangGraph Integration & Dialogue Management
**Dependencias:** Task 401 (Understand Node)
**Duración estimada:** 2-3 horas

### Objetivo

Implement routing functions for conditional edges in the LangGraph. These functions determine the next node to execute based on NLU results and dialogue state.

### Contexto

Routing functions are synchronous functions that take the current dialogue state and return the name of the next node to execute. They are used in `add_conditional_edges` to route the dialogue flow based on message type and state conditions.

**Reference:** [docs/implementation/04-phase-4-langgraph.md](../../docs/implementation/04-phase-4-langgraph.md) - Task 4.2

### Entregables

- [ ] `route_after_understand` function implemented in `src/soni/dm/routing.py`
- [ ] `route_after_validate` function implemented in `src/soni/dm/routing.py`
- [ ] All message types handled correctly
- [ ] Tests passing in `tests/unit/test_routing.py`
- [ ] Mypy passes without errors

### Implementación Detallada

#### Paso 1: Add Routing Functions to routing.py

**Archivo(s) a crear/modificar:** `src/soni/dm/routing.py`

**Código específico:**

```python
from soni.core.types import DialogueState

def route_after_understand(state: DialogueState) -> str:
    """
    Route based on NLU result.

    Pattern: Routing Function (synchronous, returns node name)

    Args:
        state: Current dialogue state

    Returns:
        Name of next node to execute
    """
    nlu_result = state.get("nlu_result")

    if not nlu_result:
        return "generate_response"

    message_type = nlu_result.get("message_type")

    # Route based on message type
    match message_type:
        case "slot_value":
            return "validate_slot"
        case "correction":
            return "handle_correction"
        case "modification":
            return "handle_modification"
        case "interruption":
            return "handle_intent_change"
        case "digression":
            return "handle_digression"
        case "clarification":
            return "handle_clarification"
        case "cancellation":
            return "handle_cancellation"
        case "confirmation":
            return "handle_confirmation"
        case "continuation":
            return "continue_flow"
        case _:
            return "generate_response"

def route_after_validate(state: DialogueState) -> str:
    """
    Route after slot validation.

    Args:
        state: Current dialogue state

    Returns:
        Next node name
    """
    # Check if all required slots filled
    flow_stack = state.get("flow_stack", [])
    active_flow = flow_stack[-1] if flow_stack else None

    if not active_flow:
        return "generate_response"

    # TODO: Check slot requirements from flow definition
    # For now, simple logic
    if state.get("all_slots_filled"):
        return "execute_action"
    else:
        return "collect_next_slot"
```

**Explicación:**
- Add routing functions to existing `routing.py` file
- Functions are synchronous (not async)
- Functions return string node names
- Use `match/case` for message type routing (Python 3.10+)
- Handle all message types from NLU output
- `route_after_validate` checks if slots are filled

### Tests Requeridos

**Archivo de tests:** `tests/unit/test_routing.py`

**Tests específicos a implementar:**

```python
import pytest
from soni.dm.routing import route_after_understand, route_after_validate
from soni.core.state import create_empty_state

def test_route_after_understand_slot_value():
    """Test routing with slot_value message type."""
    # Arrange
    state = create_empty_state()
    state["nlu_result"] = {
        "message_type": "slot_value",
        "command": "book_flight",
        "slots": [{"name": "origin", "value": "Madrid"}],
    }

    # Act
    next_node = route_after_understand(state)

    # Assert
    assert next_node == "validate_slot"

def test_route_after_understand_interruption():
    """Test routing with interruption message type."""
    # Arrange
    state = create_empty_state()
    state["nlu_result"] = {
        "message_type": "interruption",
        "command": "book_flight",
    }

    # Act
    next_node = route_after_understand(state)

    # Assert
    assert next_node == "handle_intent_change"

def test_route_after_understand_digression():
    """Test routing with digression message type."""
    # Arrange
    state = create_empty_state()
    state["nlu_result"] = {
        "message_type": "digression",
        "command": "what_time",
    }

    # Act
    next_node = route_after_understand(state)

    # Assert
    assert next_node == "handle_digression"

def test_route_after_understand_no_nlu_result():
    """Test routing when no NLU result exists."""
    # Arrange
    state = create_empty_state()
    state["nlu_result"] = None

    # Act
    next_node = route_after_understand(state)

    # Assert
    assert next_node == "generate_response"

def test_route_after_validate_all_slots_filled():
    """Test routing when all slots are filled."""
    # Arrange
    state = create_empty_state()
    state["flow_stack"] = [{
        "flow_id": "flow_1",
        "flow_name": "book_flight",
        "flow_state": "active",
        "current_step": None,
        "outputs": {},
        "started_at": 0.0,
        "paused_at": None,
        "completed_at": None,
        "context": None,
    }]
    state["all_slots_filled"] = True

    # Act
    next_node = route_after_validate(state)

    # Assert
    assert next_node == "execute_action"

def test_route_after_validate_slots_missing():
    """Test routing when slots are missing."""
    # Arrange
    state = create_empty_state()
    state["flow_stack"] = [{
        "flow_id": "flow_1",
        "flow_name": "book_flight",
        "flow_state": "active",
        "current_step": None,
        "outputs": {},
        "started_at": 0.0,
        "paused_at": None,
        "completed_at": None,
        "context": None,
    }]
    state["all_slots_filled"] = False

    # Act
    next_node = route_after_validate(state)

    # Assert
    assert next_node == "collect_next_slot"

def test_route_after_validate_no_active_flow():
    """Test routing when no active flow exists."""
    # Arrange
    state = create_empty_state()
    state["flow_stack"] = []

    # Act
    next_node = route_after_validate(state)

    # Assert
    assert next_node == "generate_response"
```

### Criterios de Éxito

- [ ] `route_after_understand` function implemented
- [ ] `route_after_validate` function implemented
- [ ] All message types handled correctly
- [ ] Tests passing (`uv run pytest tests/unit/test_routing.py -v`)
- [ ] Mypy passes (`uv run mypy src/soni/dm/routing.py`)
- [ ] Ruff passes (`uv run ruff check src/soni/dm/routing.py`)

### Validación Manual

**Comandos para validar:**

```bash
# Type checking
uv run mypy src/soni/dm/routing.py

# Tests
uv run pytest tests/unit/test_routing.py -v

# Linting
uv run ruff check src/soni/dm/routing.py
uv run ruff format src/soni/dm/routing.py
```

**Resultado esperado:**
- Mypy shows no errors
- All tests pass
- Ruff shows no linting errors
- Routing functions can be used in graph builder

### Referencias

- [docs/implementation/04-phase-4-langgraph.md](../../docs/implementation/04-phase-4-langgraph.md) - Task 4.2
- [docs/design/08-langgraph-integration.md](../../docs/design/08-langgraph-integration.md) - Conditional edges

### Notas Adicionales

- Routing functions must be synchronous (not async)
- Functions return string node names (not node objects)
- Use `match/case` for Python 3.10+ (or if/elif for older versions)
- Handle all message types from `MessageType` enum
- `route_after_validate` uses placeholder logic (TODO: get from flow definition)
- Functions should handle edge cases (no NLU result, no active flow, etc.)
