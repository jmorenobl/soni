## Task: 4.3 - Additional Nodes

**ID de tarea:** 403
**Hito:** Phase 4 - LangGraph Integration & Dialogue Management
**Dependencias:** Task 401 (Understand Node), Task 402 (Routing Functions)
**Duración estimada:** 4-5 horas

### Objetivo

Implement the remaining core dialogue management nodes: validate_slot, collect_next_slot, handle_intent_change, handle_digression, execute_action, and generate_response.

### Contexto

These nodes complete the dialogue management pipeline. Each node handles a specific aspect of the dialogue flow. Some nodes use `interrupt()` to pause execution and wait for user input.

**Reference:** [docs/implementation/04-phase-4-langgraph.md](../../docs/implementation/04-phase-4-langgraph.md) - Task 4.3

### Entregables

- [ ] `src/soni/dm/nodes/validate_slot.py` created
- [ ] `src/soni/dm/nodes/collect_next_slot.py` created (uses `interrupt()`)
- [ ] `src/soni/dm/nodes/handle_intent_change.py` created
- [ ] `src/soni/dm/nodes/handle_digression.py` created
- [ ] `src/soni/dm/nodes/execute_action.py` created
- [ ] `src/soni/dm/nodes/generate_response.py` created
- [ ] All nodes use `Runtime[RuntimeContext]` pattern
- [ ] Tests for each node in `tests/unit/test_nodes_*.py`
- [ ] Mypy passes without errors

### Implementación Detallada

#### Paso 1: Create validate_slot.py

**Archivo(s) a crear/modificar:** `src/soni/dm/nodes/validate_slot.py`

**Código específico:**

```python
"""Validate slot node for slot validation and normalization."""

import logging
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from langgraph.runtime import Runtime

from soni.core.types import DialogueState, RuntimeContext

logger = logging.getLogger(__name__)


async def validate_slot_node(
    state: DialogueState,
    runtime: Runtime[RuntimeContext],
) -> dict:
    """
    Validate and normalize slot value.

    Args:
        state: Current dialogue state
        runtime: Runtime context with dependencies

    Returns:
        Partial state updates
    """
    normalizer = runtime.context["normalizer"]
    nlu_result = state.get("nlu_result", {})

    if not nlu_result or not nlu_result.get("slots"):
        return {"conversation_state": "error"}

    # Get first slot from NLU result
    slots = nlu_result.get("slots", [])
    if not slots:
        return {"conversation_state": "error"}

    slot = slots[0]
    slot_name = slot.get("name")
    raw_value = slot.get("value")

    # Normalize slot value
    try:
        normalized_value = await normalizer.normalize(slot_name, raw_value)

        # Update flow slots
        flow_manager = runtime.context["flow_manager"]
        active_ctx = flow_manager.get_active_context(state)

        if active_ctx:
            flow_id = active_ctx["flow_id"]
            flow_slots = state.get("flow_slots", {}).copy()
            if flow_id not in flow_slots:
                flow_slots[flow_id] = {}
            flow_slots[flow_id][slot_name] = normalized_value

            return {
                "flow_slots": flow_slots,
                "conversation_state": "validating_slot",
            }
        else:
            return {"conversation_state": "error"}
    except Exception as e:
        logger.error(f"Validation failed for slot {slot_name}: {e}")
        return {
            "conversation_state": "error",
            "validation_error": str(e),
        }
```

#### Paso 2: Create collect_next_slot.py

**Archivo(s) a crear/modificar:** `src/soni/dm/nodes/collect_next_slot.py`

**Código específico:**

```python
"""Collect next slot node with interrupt pattern."""

import logging
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from langgraph.runtime import Runtime
    from langgraph.types import interrupt

from soni.core.types import DialogueState, RuntimeContext

logger = logging.getLogger(__name__)


async def collect_next_slot_node(
    state: DialogueState,
    runtime: Runtime[RuntimeContext],
) -> dict:
    """
    Ask for next required slot and pause execution.

    Uses interrupt() to wait for user response.

    Args:
        state: Current dialogue state
        runtime: Runtime context

    Returns:
        Partial state updates
    """
    # Import interrupt at runtime (not at module level)
    from langgraph.types import interrupt

    # Get active flow (idempotent operation - safe before interrupt)
    flow_manager = runtime.context["flow_manager"]
    active_ctx = flow_manager.get_active_context(state)

    if not active_ctx:
        return {"conversation_state": "idle"}

    # Determine next slot to collect
    # TODO: Get from flow definition
    next_slot = "origin"  # Placeholder

    # Generate prompt
    prompt = f"Please provide your {next_slot}."

    # Pause here - wait for user response
    user_response = interrupt({
        "type": "slot_request",
        "slot": next_slot,
        "prompt": prompt,
    })

    # Code after interrupt() executes when user responds
    return {
        "user_message": user_response,
        "waiting_for_slot": next_slot,
        "conversation_state": "waiting_for_slot",
        "last_response": prompt,
    }
```

#### Paso 3: Create handle_intent_change.py

**Archivo(s) a crear/modificar:** `src/soni/dm/nodes/handle_intent_change.py`

**Código específico:**

```python
"""Handle intent change node for starting new flows."""

import logging
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from langgraph.runtime import Runtime

from soni.core.types import DialogueState, RuntimeContext

logger = logging.getLogger(__name__)


async def handle_intent_change_node(
    state: DialogueState,
    runtime: Runtime[RuntimeContext],
) -> dict:
    """
    Start new flow based on intent change.

    Args:
        state: Current dialogue state
        runtime: Runtime context

    Returns:
        Partial state updates
    """
    flow_manager = runtime.context["flow_manager"]
    nlu_result = state.get("nlu_result", {})

    if not nlu_result:
        return {"conversation_state": "error"}

    command = nlu_result.get("command")
    if not command:
        return {"conversation_state": "error"}

    # Start new flow
    flow_id = flow_manager.push_flow(
        state,
        flow_name=command,
        inputs={},
        reason="intent_change",
    )

    return {
        "conversation_state": "collecting",
        "current_step": None,
    }
```

#### Paso 4: Create handle_digression.py

**Archivo(s) a crear/modificar:** `src/soni/dm/nodes/handle_digression.py`

**Código específico:**

```python
"""Handle digression node for questions without flow changes."""

import logging
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from langgraph.runtime import Runtime

from soni.core.types import DialogueState, RuntimeContext

logger = logging.getLogger(__name__)


async def handle_digression_node(
    state: DialogueState,
    runtime: Runtime[RuntimeContext],
) -> dict:
    """
    Handle digression (question without flow change).

    Args:
        state: Current dialogue state
        runtime: Runtime context

    Returns:
        Partial state updates
    """
    nlu_result = state.get("nlu_result", {})
    command = nlu_result.get("command", "")

    # For now, generate simple response
    # TODO: Integrate with knowledge base or help system
    response = f"I understand you're asking about {command}. Let me help you with that."

    return {
        "last_response": response,
        "conversation_state": "generating_response",
        "digression_depth": state.get("digression_depth", 0) + 1,
        "last_digression_type": command,
    }
```

#### Paso 5: Create execute_action.py

**Archivo(s) a crear/modificar:** `src/soni/dm/nodes/execute_action.py`

**Código específico:**

```python
"""Execute action node for running actions."""

import logging
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from langgraph.runtime import Runtime

from soni.core.types import DialogueState, RuntimeContext

logger = logging.getLogger(__name__)


async def execute_action_node(
    state: DialogueState,
    runtime: Runtime[RuntimeContext],
) -> dict:
    """
    Execute action via ActionHandler.

    Args:
        state: Current dialogue state
        runtime: Runtime context

    Returns:
        Partial state updates
    """
    action_handler = runtime.context["action_handler"]
    flow_manager = runtime.context["flow_manager"]

    active_ctx = flow_manager.get_active_context(state)
    if not active_ctx:
        return {"conversation_state": "error"}

    # Get action name from flow
    flow_name = active_ctx["flow_name"]

    # Get slots for action inputs
    flow_slots = state.get("flow_slots", {}).get(active_ctx["flow_id"], {})

    # Execute action
    try:
        action_result = await action_handler.execute(
            action_name=flow_name,
            inputs=flow_slots,
        )

        return {
            "conversation_state": "executing_action",
            "action_result": action_result,
        }
    except Exception as e:
        logger.error(f"Action execution failed: {e}")
        return {
            "conversation_state": "error",
            "action_error": str(e),
        }
```

#### Paso 6: Create generate_response.py

**Archivo(s) a crear/modificar:** `src/soni/dm/nodes/generate_response.py`

**Código específico:**

```python
"""Generate response node for final response generation."""

import logging
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from langgraph.runtime import Runtime

from soni.core.types import DialogueState, RuntimeContext

logger = logging.getLogger(__name__)


async def generate_response_node(
    state: DialogueState,
    runtime: Runtime[RuntimeContext],
) -> dict:
    """
    Generate final response to user.

    Args:
        state: Current dialogue state
        runtime: Runtime context

    Returns:
        Partial state updates
    """
    # For now, simple response generation
    # TODO: Integrate with LLM for natural response generation

    action_result = state.get("action_result")
    if action_result:
        response = f"Action completed successfully. Result: {action_result}"
    else:
        response = "How can I help you?"

    return {
        "last_response": response,
        "conversation_state": "idle",
    }
```

#### Paso 7: Update nodes/__init__.py

**Archivo(s) a crear/modificar:** `src/soni/dm/nodes/__init__.py`

**Código específico:**

```python
"""Dialogue management nodes."""

from soni.dm.nodes.understand import understand_node
from soni.dm.nodes.validate_slot import validate_slot_node
from soni.dm.nodes.collect_next_slot import collect_next_slot_node
from soni.dm.nodes.handle_intent_change import handle_intent_change_node
from soni.dm.nodes.handle_digression import handle_digression_node
from soni.dm.nodes.execute_action import execute_action_node
from soni.dm.nodes.generate_response import generate_response_node

__all__ = [
    "understand_node",
    "validate_slot_node",
    "collect_next_slot_node",
    "handle_intent_change_node",
    "handle_digression_node",
    "execute_action_node",
    "generate_response_node",
]
```

### Tests Requeridos

**Archivos de tests:**
- `tests/unit/test_nodes_validate_slot.py`
- `tests/unit/test_nodes_collect.py`
- `tests/unit/test_nodes_intent_change.py`
- `tests/unit/test_nodes_digression.py`
- `tests/unit/test_nodes_action.py`
- `tests/unit/test_nodes_response.py`

**Tests específicos a implementar (ejemplo para validate_slot):**

```python
import pytest
from unittest.mock import AsyncMock, MagicMock
from soni.dm.nodes.validate_slot import validate_slot_node
from soni.core.state import create_empty_state
from langgraph.runtime import Runtime

@pytest.mark.asyncio
async def test_validate_slot_success():
    """Test validate slot with successful normalization."""
    # Arrange
    state = create_empty_state()
    state["nlu_result"] = {
        "slots": [{"name": "origin", "value": "Madrid"}],
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

    mock_normalizer = AsyncMock()
    mock_normalizer.normalize.return_value = "MAD"

    mock_flow_manager = MagicMock()
    mock_flow_manager.get_active_context.return_value = {
        "flow_id": "flow_1",
        "flow_name": "book_flight",
    }

    mock_runtime = MagicMock()
    mock_runtime.context = {
        "normalizer": mock_normalizer,
        "flow_manager": mock_flow_manager,
    }

    # Act
    result = await validate_slot_node(state, mock_runtime)

    # Assert
    assert result["conversation_state"] == "validating_slot"
    assert "flow_slots" in result
    mock_normalizer.normalize.assert_called_once()
```

### Criterios de Éxito

- [ ] All 6 nodes implemented
- [ ] All nodes use `Runtime[RuntimeContext]` pattern
- [ ] `collect_next_slot` uses `interrupt()` correctly
- [ ] Tests passing for all nodes
- [ ] Mypy passes for all node files
- [ ] Ruff passes for all node files

### Validación Manual

**Comandos para validar:**

```bash
# Type checking
uv run mypy src/soni/dm/nodes/

# Tests
uv run pytest tests/unit/test_nodes_*.py -v

# Linting
uv run ruff check src/soni/dm/nodes/
uv run ruff format src/soni/dm/nodes/
```

**Resultado esperado:**
- Mypy shows no errors
- All tests pass
- Ruff shows no linting errors
- All nodes can be imported and used in graph builder

### Referencias

- [docs/implementation/04-phase-4-langgraph.md](../../docs/implementation/04-phase-4-langgraph.md) - Task 4.3
- [docs/design/08-langgraph-integration.md](../../docs/design/08-langgraph-integration.md) - interrupt() pattern

### Notas Adicionales

- All nodes must use `Runtime[RuntimeContext]` pattern
- `collect_next_slot` must use `interrupt()` to pause execution
- Code before `interrupt()` must be idempotent (safe to re-execute)
- Some nodes have TODO comments for future enhancements
- Nodes return partial state updates (dict), not full state
- All async operations must be properly awaited
- Error handling should log errors and return error state
