## Task: 4.1 - Understand Node

**ID de tarea:** 401
**Hito:** Phase 4 - LangGraph Integration & Dialogue Management
**Dependencias:** Ninguna
**Duración estimada:** 2-3 horas

### Objetivo

Implement the understand node that calls NLU to process user messages. This is the entry point for all user messages in the dialogue flow.

### Contexto

The understand node is the first node in the dialogue graph. It receives user messages, calls the NLU provider to extract intents and slots, and updates the dialogue state with NLU results. This node uses the RuntimeContext pattern to access dependencies (INLUProvider, IFlowManager, IScopeManager).

**Reference:** [docs/implementation/04-phase-4-langgraph.md](../../docs/implementation/04-phase-4-langgraph.md) - Task 4.1

### Entregables

- [ ] `src/soni/dm/nodes/understand.py` created with `understand_node` function
- [ ] Node uses `Runtime[RuntimeContext]` pattern for dependency injection
- [ ] Node calls NLU provider with proper dialogue context
- [ ] Node updates state with NLU result
- [ ] Tests passing in `tests/unit/test_nodes_understand.py`
- [ ] Mypy passes without errors

### Implementación Detallada

#### Paso 1: Create understand.py File

**Archivo(s) a crear/modificar:** `src/soni/dm/nodes/understand.py`

**Código específico:**

```python
"""Understand node for NLU processing."""

import logging
import time
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from langgraph.runtime import Runtime

from soni.core.types import DialogueState, RuntimeContext

logger = logging.getLogger(__name__)


async def understand_node(
    state: DialogueState,
    runtime: Runtime[RuntimeContext],
) -> dict:
    """
    Understand user message via NLU.

    Pattern: With Dependencies (uses context_schema)

    Args:
        state: Current dialogue state
        runtime: Runtime context with dependencies

    Returns:
        Partial state updates with NLU result
    """
    # Access dependencies (type-safe)
    nlu_provider = runtime.context["nlu_provider"]
    flow_manager = runtime.context["flow_manager"]
    scope_manager = runtime.context["scope_manager"]

    # Build NLU context
    active_ctx = flow_manager.get_active_context(state)
    current_flow_name = active_ctx["flow_name"] if active_ctx else "none"

    dialogue_context = {
        "current_slots": state["flow_slots"].get(active_ctx["flow_id"], {}) if active_ctx else {},
        "available_actions": scope_manager.get_available_actions(state),
        "available_flows": scope_manager.get_available_flows(state),
        "current_flow": current_flow_name,
        "expected_slots": [],  # TODO: Get from flow definition
        "history": state["messages"][-5:] if state["messages"] else [],  # Last 5 messages
    }

    # Call NLU
    nlu_result = await nlu_provider.understand(
        state["user_message"],
        dialogue_context,
    )

    return {
        "nlu_result": nlu_result,
        "conversation_state": "understanding",
        "last_nlu_call": time.time(),
    }
```

**Explicación:**
- Create new file `src/soni/dm/nodes/understand.py`
- Use `Runtime[RuntimeContext]` pattern from LangGraph 0.6+
- Access dependencies via `runtime.context["key"]`
- Build dialogue context from state and dependencies
- Call NLU provider's `understand` method
- Return partial state updates (dict with keys to update)

#### Paso 2: Create __init__.py for nodes package

**Archivo(s) a crear/modificar:** `src/soni/dm/nodes/__init__.py`

**Código específico:**

```python
"""Dialogue management nodes."""

from soni.dm.nodes.understand import understand_node

__all__ = ["understand_node"]
```

**Explicación:**
- Create `__init__.py` to make `nodes` a package
- Export `understand_node` for use in graph builder

### Tests Requeridos

**Archivo de tests:** `tests/unit/test_nodes_understand.py`

**Tests específicos a implementar:**

```python
import pytest
from unittest.mock import AsyncMock, MagicMock
from soni.dm.nodes.understand import understand_node
from soni.core.state import create_initial_state
from langgraph.runtime import Runtime

@pytest.mark.asyncio
async def test_understand_node_calls_nlu():
    """Test understand node calls NLU provider."""
    # Arrange
    state = create_initial_state("Hello")

    # Mock runtime context
    mock_nlu = AsyncMock()
    mock_nlu.understand.return_value = {
        "message_type": "interruption",
        "command": "greet",
        "slots": [],
        "confidence": 0.9,
        "reasoning": "greeting",
    }

    mock_flow_manager = MagicMock()
    mock_flow_manager.get_active_context.return_value = None

    mock_scope_manager = MagicMock()
    mock_scope_manager.get_available_actions.return_value = ["greet"]
    mock_scope_manager.get_available_flows.return_value = []

    mock_runtime = MagicMock()
    mock_runtime.context = {
        "nlu_provider": mock_nlu,
        "flow_manager": mock_flow_manager,
        "scope_manager": mock_scope_manager,
    }

    # Act
    result = await understand_node(state, mock_runtime)

    # Assert
    assert result["conversation_state"] == "understanding"
    assert result["nlu_result"]["command"] == "greet"
    mock_nlu.understand.assert_called_once()
    assert "last_nlu_call" in result

@pytest.mark.asyncio
async def test_understand_node_with_active_flow():
    """Test understand node with active flow context."""
    # Arrange
    state = create_initial_state("I want to book a flight")
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
    state["flow_slots"] = {"flow_1": {"origin": "Madrid"}}

    mock_nlu = AsyncMock()
    mock_nlu.understand.return_value = {
        "message_type": "slot_value",
        "command": "book_flight",
        "slots": [{"name": "destination", "value": "Barcelona"}],
        "confidence": 0.95,
        "reasoning": "destination provided",
    }

    mock_flow_manager = MagicMock()
    mock_flow_manager.get_active_context.return_value = {
        "flow_id": "flow_1",
        "flow_name": "book_flight",
    }

    mock_scope_manager = MagicMock()
    mock_scope_manager.get_available_actions.return_value = ["book_flight"]
    mock_scope_manager.get_available_flows.return_value = ["book_flight"]

    mock_runtime = MagicMock()
    mock_runtime.context = {
        "nlu_provider": mock_nlu,
        "flow_manager": mock_flow_manager,
        "scope_manager": mock_scope_manager,
    }

    # Act
    result = await understand_node(state, mock_runtime)

    # Assert
    assert result["nlu_result"]["message_type"] == "slot_value"
    # Verify dialogue context includes current slots
    call_args = mock_nlu.understand.call_args
    assert call_args[0][0] == "I want to book a flight"
    dialogue_context = call_args[0][1]
    assert dialogue_context["current_flow"] == "book_flight"
    assert "origin" in dialogue_context["current_slots"]
```

### Criterios de Éxito

- [ ] `understand_node` function implemented
- [ ] Uses `Runtime[RuntimeContext]` pattern correctly
- [ ] NLU integration working
- [ ] Tests passing (`uv run pytest tests/unit/test_nodes_understand.py -v`)
- [ ] Mypy passes (`uv run mypy src/soni/dm/nodes/understand.py`)
- [ ] Ruff passes (`uv run ruff check src/soni/dm/nodes/understand.py`)

### Validación Manual

**Comandos para validar:**

```bash
# Type checking
uv run mypy src/soni/dm/nodes/understand.py

# Tests
uv run pytest tests/unit/test_nodes_understand.py -v

# Linting
uv run ruff check src/soni/dm/nodes/understand.py
uv run ruff format src/soni/dm/nodes/understand.py
```

**Resultado esperado:**
- Mypy shows no errors
- All tests pass
- Ruff shows no linting errors
- Node can be imported and used in graph builder

### Referencias

- [docs/implementation/04-phase-4-langgraph.md](../../docs/implementation/04-phase-4-langgraph.md) - Task 4.1
- [docs/design/08-langgraph-integration.md](../../docs/design/08-langgraph-integration.md) - RuntimeContext pattern
- [LangGraph documentation](https://langchain-ai.github.io/langgraph/) - Runtime context

### Notas Adicionales

- Node must use `Runtime[RuntimeContext]` pattern (LangGraph 0.6+)
- Access dependencies via `runtime.context["key"]` (type-safe)
- Dialogue context should include last 5 messages for history
- `expected_slots` is TODO for now (will be implemented in later tasks)
- Node returns partial state updates (dict), not full state
- All async operations must be properly awaited
