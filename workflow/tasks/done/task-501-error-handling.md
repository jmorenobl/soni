## Task: 5.1 - Error Handling & Recovery

**ID de tarea:** 501
**Hito:** Phase 5 - Production Readiness
**Dependencias:** Ninguna
**Duración estimada:** 2-3 horas

### Objetivo

Implement error handling node that processes different error types (validation_error, nlu_error, action_error) and implements recovery strategies. This node enables graceful degradation and error recovery in the dialogue system.

### Contexto

The error handling node is a critical production feature that ensures the dialogue system can recover from various error conditions. It processes errors stored in state metadata and implements specific recovery strategies based on error type. This node uses the RuntimeContext pattern to access dependencies like IFlowManager.

**Reference:** [docs/implementation/05-phase-5-production.md](../../docs/implementation/05-phase-5-production.md) - Task 5.1

### Entregables

- [ ] `src/soni/dm/nodes/handle_error.py` created with `handle_error_node` function
- [ ] Node uses `Runtime[RuntimeContext]` pattern for dependency injection
- [ ] Handles validation_error, nlu_error, and action_error types
- [ ] Implements recovery strategies for each error type
- [ ] Uses structured logging for error tracking
- [ ] Tests passing in `tests/unit/test_nodes_handle_error.py`
- [ ] Mypy passes without errors

### Implementación Detallada

#### Paso 1: Create handle_error.py File

**Archivo(s) a crear/modificar:** `src/soni/dm/nodes/handle_error.py`

**Código específico:**

```python
"""Error handling node for dialogue recovery."""

import logging
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from langgraph.runtime import Runtime

from soni.core.types import DialogueState, RuntimeContext

logger = logging.getLogger(__name__)


async def handle_error_node(
    state: DialogueState,
    runtime: Runtime[RuntimeContext],
) -> dict:
    """
    Handle errors and attempt recovery.

    Pattern: With Dependencies (uses context_schema)

    Args:
        state: Current dialogue state
        runtime: Runtime context with dependencies

    Returns:
        Partial state updates with recovery strategy
    """
    # Access dependencies
    flow_manager = runtime.context["flow_manager"]

    # Extract error information from metadata
    metadata = state.get("metadata", {})
    error = metadata.get("error")
    error_type = metadata.get("error_type")

    # Log error with context
    logger.error(
        f"Error in dialogue flow: {error}",
        extra={
            "error_type": error_type,
            "conversation_state": state.get("conversation_state"),
            "turn_count": state.get("turn_count", 0),
        },
    )

    # Attempt recovery based on error type
    if error_type == "validation_error":
        # Clear invalid data and retry
        if state.get("flow_stack"):
            flow_manager.pop_flow(state, result="cancelled")

        return {
            "last_response": "Let's try that again. What would you like to do?",
            "conversation_state": "idle",
            "metadata": {**metadata, "error": None, "error_type": None},
        }

    elif error_type == "nlu_error":
        return {
            "last_response": "I didn't understand that. Could you rephrase?",
            "conversation_state": "understanding",
            "metadata": {**metadata, "error": None, "error_type": None},
        }

    elif error_type == "action_error":
        return {
            "last_response": "Something went wrong while processing your request. Please try again.",
            "conversation_state": "idle",
            "flow_stack": [],
            "flow_slots": {},
            "metadata": {**metadata, "error": None, "error_type": None},
        }

    # Generic error - clear stack and start over
    return {
        "last_response": "Something went wrong. Let's start fresh.",
        "conversation_state": "idle",
        "flow_stack": [],
        "flow_slots": {},
        "metadata": {**metadata, "error": None, "error_type": None},
    }
```

**Explicación:**
- Create new file `src/soni/dm/nodes/handle_error.py`
- Use `Runtime[RuntimeContext]` pattern from LangGraph 0.6+
- Access `flow_manager` from runtime context
- Extract error information from state metadata
- Implement recovery strategies for each error type
- Use structured logging with context
- Return partial state updates (dict with keys to update)

#### Paso 2: Update __init__.py for nodes package

**Archivo(s) a crear/modificar:** `src/soni/dm/nodes/__init__.py`

**Explicación:**
- Add `handle_error_node` to exports if needed

### Tests Requeridos

**Archivo de tests:** `tests/unit/test_nodes_handle_error.py`

**Tests específicos a implementar:**

```python
import pytest
from unittest.mock import MagicMock
from soni.dm.nodes.handle_error import handle_error_node
from soni.core.state import create_empty_state

@pytest.mark.asyncio
async def test_handle_error_validation_error():
    """Test error handling for validation errors."""
    # Arrange
    state = create_empty_state()
    state["metadata"] = {
        "error": "Invalid slot value",
        "error_type": "validation_error",
    }
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

    mock_flow_manager = MagicMock()
    mock_runtime = MagicMock()
    mock_runtime.context = {"flow_manager": mock_flow_manager}

    # Act
    result = await handle_error_node(state, mock_runtime)

    # Assert
    assert result["conversation_state"] == "idle"
    assert "try that again" in result["last_response"].lower()
    assert result["metadata"]["error"] is None
    assert result["metadata"]["error_type"] is None
    mock_flow_manager.pop_flow.assert_called_once()

@pytest.mark.asyncio
async def test_handle_error_nlu_error():
    """Test error handling for NLU errors."""
    # Arrange
    state = create_empty_state()
    state["metadata"] = {
        "error": "NLU processing failed",
        "error_type": "nlu_error",
    }

    mock_flow_manager = MagicMock()
    mock_runtime = MagicMock()
    mock_runtime.context = {"flow_manager": mock_flow_manager}

    # Act
    result = await handle_error_node(state, mock_runtime)

    # Assert
    assert result["conversation_state"] == "understanding"
    assert "rephrase" in result["last_response"].lower()
    assert result["metadata"]["error"] is None
    assert result["metadata"]["error_type"] is None

@pytest.mark.asyncio
async def test_handle_error_action_error():
    """Test error handling for action errors."""
    # Arrange
    state = create_empty_state()
    state["metadata"] = {
        "error": "Action execution failed",
        "error_type": "action_error",
    }
    state["flow_stack"] = [{"flow_id": "flow_1"}]
    state["flow_slots"] = {"flow_1": {"origin": "Madrid"}}

    mock_flow_manager = MagicMock()
    mock_runtime = MagicMock()
    mock_runtime.context = {"flow_manager": mock_flow_manager}

    # Act
    result = await handle_error_node(state, mock_runtime)

    # Assert
    assert result["conversation_state"] == "idle"
    assert "try again" in result["last_response"].lower()
    assert result["flow_stack"] == []
    assert result["flow_slots"] == {}
    assert result["metadata"]["error"] is None

@pytest.mark.asyncio
async def test_handle_error_generic_error():
    """Test error handling for generic errors."""
    # Arrange
    state = create_empty_state()
    state["metadata"] = {
        "error": "Unknown error",
        "error_type": "unknown",
    }
    state["flow_stack"] = [{"flow_id": "flow_1"}]
    state["flow_slots"] = {"flow_1": {"origin": "Madrid"}}

    mock_flow_manager = MagicMock()
    mock_runtime = MagicMock()
    mock_runtime.context = {"flow_manager": mock_flow_manager}

    # Act
    result = await handle_error_node(state, mock_runtime)

    # Assert
    assert result["conversation_state"] == "idle"
    assert "start fresh" in result["last_response"].lower()
    assert result["flow_stack"] == []
    assert result["flow_slots"] == {}
    assert result["metadata"]["error"] is None
```

### Criterios de Éxito

- [ ] `handle_error_node` function implemented
- [ ] Uses `Runtime[RuntimeContext]` pattern correctly
- [ ] Handles all three error types (validation_error, nlu_error, action_error)
- [ ] Implements recovery strategies correctly
- [ ] Tests passing (`uv run pytest tests/unit/test_nodes_handle_error.py -v`)
- [ ] Mypy passes (`uv run mypy src/soni/dm/nodes/handle_error.py`)
- [ ] Ruff passes (`uv run ruff check src/soni/dm/nodes/handle_error.py`)

### Validación Manual

**Comandos para validar:**

```bash
# Type checking
uv run mypy src/soni/dm/nodes/handle_error.py

# Tests
uv run pytest tests/unit/test_nodes_handle_error.py -v

# Linting
uv run ruff check src/soni/dm/nodes/handle_error.py
uv run ruff format src/soni/dm/nodes/handle_error.py
```

**Resultado esperado:**
- Mypy shows no errors
- All tests pass
- Ruff shows no linting errors
- Node can be imported and used in graph builder

### Referencias

- [docs/implementation/05-phase-5-production.md](../../docs/implementation/05-phase-5-production.md) - Task 5.1
- [docs/design/08-langgraph-integration.md](../../docs/design/08-langgraph-integration.md) - RuntimeContext pattern

### Notas Adicionales

- Node must use `Runtime[RuntimeContext]` pattern (LangGraph 0.6+)
- Access dependencies via `runtime.context["key"]` (type-safe)
- Error information is stored in state metadata
- Recovery strategies clear error state after handling
- Use mocks for IFlowManager in tests
- All async operations must be properly awaited
