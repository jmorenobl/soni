## Task: 304 - Split generate_response_node to Follow SRP

**ID de tarea:** 304
**Hito:** Technical Debt Repayment - MEDIUM
**Dependencias:** Task 301 (Domain-specific code removed)
**Duración estimada:** 3-4 horas
**Prioridad:** 🟡 MEDIUM - Improves testability
**Related DEBT:** DEBT-004

### Objetivo

Refactorizar `generate_response_node` que actualmente tiene múltiples responsabilidades (generar respuesta + gestión de estado + limpieza de flows) en componentes separados que sigan el Single Responsibility Principle.

### Contexto

**Responsabilidades mezcladas en generate_response_node:**
1. Generate response to user (primary)
2. Manage conversation_state transitions
3. Clean up completed flows from stack
4. Archive flows in metadata

**Violaciones:**
- ❌ SRP: 4 responsabilidades en una función
- ❌ Testability: Difícil testear cada parte independientemente
- ❌ Reusability: No se puede reusar generación sin state management

**Referencias:**
- Technical Debt: `docs/technical-debt.md` (DEBT-004)
- Clean Architecture: Robert C. Martin
- File: `src/soni/dm/nodes/generate_response.py`

### Entregables

- [ ] Clase `ResponseGenerator` creada en `src/soni/utils/response_generator.py`
- [ ] Clase `FlowCleanupManager` creada en `src/soni/utils/flow_cleanup.py`
- [ ] `generate_response_node` refactorizado con single responsibility
- [ ] Optional: Nuevo nodo `cleanup_completed_flow_node`
- [ ] Tests unitarios para cada clase
- [ ] Todos los tests existentes pasan

### Implementación Detallada

#### Paso 1: Crear ResponseGenerator class

**Archivo a crear:** `src/soni/utils/response_generator.py`

```python
"""Response generation utilities following SRP."""

from typing import Any
from soni.core.types import DialogueState
from soni.core.state import get_all_slots


class ResponseGenerator:
    """Generate responses from state (single responsibility).

    This class is responsible ONLY for generating the response text.
    It does NOT manage state transitions or flow cleanup.
    """

    @staticmethod
    def generate_from_priority(state: DialogueState) -> str:
        """Generate response based on priority order.

        Priority:
        1. confirmation slot (from action outputs)
        2. action_result.message
        3. existing last_response
        4. default fallback

        Args:
            state: Current dialogue state

        Returns:
            Response string to display to user
        """
        slots = get_all_slots(state)

        # Priority 1: Confirmation slot (generic)
        if "confirmation" in slots and slots["confirmation"]:
            return str(slots["confirmation"])

        # Priority 2: Action result message
        action_result = state.get("action_result")
        if action_result:
            if isinstance(action_result, dict):
                message = (
                    action_result.get("message")
                    or action_result.get("confirmation")
                    or f"Action completed successfully. Result: {action_result}"
                )
                return str(message)
            else:
                return f"Action completed successfully. Result: {action_result}"

        # Priority 3: Existing response from previous nodes
        existing_response = state.get("last_response", "")
        if existing_response and existing_response.strip():
            return existing_response

        # Priority 4: Default fallback
        return "How can I help you?"
```

#### Paso 2: Crear FlowCleanupManager class

**Archivo a crear:** `src/soni/utils/flow_cleanup.py`

```python
"""Flow cleanup utilities following SRP."""

from typing import Any
from soni.core.types import DialogueState


class FlowCleanupManager:
    """Manage flow cleanup and archiving (single responsibility)."""

    @staticmethod
    def cleanup_completed_flow(state: DialogueState) -> dict[str, Any]:
        """Clean up completed flow from stack and archive.

        Only cleans up if:
        1. Flow stack is not empty
        2. Top flow has flow_state="completed"

        Args:
            state: Current dialogue state

        Returns:
            Partial state updates with cleaned flow_stack and updated metadata,
            or empty dict if no cleanup needed
        """
        flow_stack = state.get("flow_stack", [])
        if not flow_stack:
            return {}

        top_flow = flow_stack[-1]
        if top_flow.get("flow_state") != "completed":
            return {}

        # Pop completed flow
        flow_stack_copy = flow_stack.copy()
        completed_flow = flow_stack_copy.pop()

        # Archive in metadata
        metadata = state.get("metadata", {}).copy()
        if "completed_flows" not in metadata:
            metadata["completed_flows"] = []
        metadata["completed_flows"].append(completed_flow)

        return {
            "flow_stack": flow_stack_copy,
            "metadata": metadata,
        }

    @staticmethod
    def should_cleanup(state: DialogueState) -> bool:
        """Check if flow cleanup is needed.

        Args:
            state: Current dialogue state

        Returns:
            True if top flow is completed and needs cleanup
        """
        flow_stack = state.get("flow_stack", [])
        if not flow_stack:
            return False
        return flow_stack[-1].get("flow_state") == "completed"
```

#### Paso 3: Refactorizar generate_response_node

**Archivo a modificar:** `src/soni/dm/nodes/generate_response.py`

```python
"""Generate response node with single responsibility."""

import logging
from typing import Any

from soni.core.types import DialogueState
from soni.utils.response_generator import ResponseGenerator
from soni.utils.flow_cleanup import FlowCleanupManager

logger = logging.getLogger(__name__)


async def generate_response_node(
    state: DialogueState,
    runtime: Any,
) -> dict:
    """Generate final response to user (single responsibility).

    This node is responsible ONLY for generating the response text.
    Flow cleanup is handled separately.

    Args:
        state: Current dialogue state
        runtime: Runtime context

    Returns:
        Partial state updates with last_response and conversation_state
    """
    # Generate response using priority-based logic
    response = ResponseGenerator.generate_from_priority(state)
    logger.info(f"generate_response_node returning: {response[:50]}...")

    # Determine conversation_state based on current state
    current_conv_state = state.get("conversation_state")

    if current_conv_state == "completed":
        # Flow cleanup is now handled by routing or separate node
        # This node only sets conversation_state
        conversation_state = "completed"
    elif current_conv_state == "confirming":
        # Preserve confirming state
        conversation_state = "confirming"
    else:
        conversation_state = "idle"

    return {
        "last_response": response,
        "conversation_state": conversation_state,
    }
```

#### Paso 4: Optional - Crear nodo de cleanup separado

**Archivo a crear:** `src/soni/dm/nodes/cleanup_flow.py`

```python
"""Flow cleanup node (optional - can be done in routing)."""

import logging
from typing import Any

from soni.core.types import DialogueState
from soni.utils.flow_cleanup import FlowCleanupManager

logger = logging.getLogger(__name__)


async def cleanup_completed_flow_node(
    state: DialogueState,
    runtime: Any,
) -> dict:
    """Clean up completed flow from stack.

    This is a separate node following SRP.
    Called after generate_response when flow is completed.

    Args:
        state: Current dialogue state
        runtime: Runtime context

    Returns:
        Partial state updates with cleaned flow_stack
    """
    cleanup_updates = FlowCleanupManager.cleanup_completed_flow(state)

    if cleanup_updates:
        flow_id = state["flow_stack"][-1]["flow_id"] if state.get("flow_stack") else "unknown"
        logger.info(f"Completed flow removed from stack: {flow_id}")

    return cleanup_updates
```

### Tests Requeridos

**Archivo:** `tests/unit/utils/test_response_generator.py`

```python
import pytest
from soni.utils.response_generator import ResponseGenerator


def test_uses_confirmation_slot_priority_1():
    """Test confirmation slot has highest priority."""
    state = {
        "flow_stack": [{"flow_id": "test"}],
        "flow_slots": {
            "test": {"confirmation": "Confirmed!"}
        },
        "action_result": {"message": "Should not use this"},
        "last_response": "Should not use this",
    }

    result = ResponseGenerator.generate_from_priority(state)

    assert result == "Confirmed!"


def test_uses_action_result_priority_2():
    """Test action_result.message when no confirmation slot."""
    state = {
        "flow_stack": [],
        "flow_slots": {},
        "action_result": {"message": "Action done!"},
        "last_response": "Should not use this",
    }

    result = ResponseGenerator.generate_from_priority(state)

    assert result == "Action done!"


# ... more tests ...
```

**Archivo:** `tests/unit/utils/test_flow_cleanup.py`

```python
import pytest
from soni.utils.flow_cleanup import FlowCleanupManager


def test_cleanup_completed_flow():
    """Test cleanup removes completed flow from stack."""
    state = {
        "flow_stack": [
            {"flow_id": "flow1", "flow_state": "completed"}
        ],
        "metadata": {},
    }

    result = FlowCleanupManager.cleanup_completed_flow(state)

    assert result["flow_stack"] == []
    assert len(result["metadata"]["completed_flows"]) == 1


def test_no_cleanup_when_not_completed():
    """Test no cleanup when flow not completed."""
    state = {
        "flow_stack": [
            {"flow_id": "flow1", "flow_state": "active"}
        ],
        "metadata": {},
    }

    result = FlowCleanupManager.cleanup_completed_flow(state)

    assert result == {}


# ... more tests ...
```

### Criterios de Éxito

- [ ] `ResponseGenerator` class created and tested
- [ ] `FlowCleanupManager` class created and tested
- [ ] `generate_response_node` has single responsibility (generate response only)
- [ ] Each class can be tested independently
- [ ] All existing tests pass
- [ ] Code coverage >= 90% for new classes
- [ ] Mypy passes
- [ ] Ruff passes

### Validación Manual

```bash
uv run pytest tests/unit/utils/test_response_generator.py -v
uv run pytest tests/unit/utils/test_flow_cleanup.py -v
uv run pytest tests/unit/dm/nodes/test_generate_response.py -v
uv run pytest tests/integration/ -v
uv run mypy src/soni
uv run ruff check src/
```

### Referencias

- **Technical Debt:** `docs/technical-debt.md` (DEBT-004)
- **SRP:** Robert C. Martin's "Clean Architecture"
- **Related:** DEBT-006 (Response Generation Duplication)

### Notas Adicionales

**Design Decision: Separate Node vs Routing:**
- Flow cleanup puede hacerse en nodo separado O en routing
- Si se hace en routing, no necesitas `cleanup_completed_flow_node`
- Recomendación: Hacer en routing para simplicidad

**Benefits of Refactor:**
- Response generation testeable independientemente
- Flow cleanup testeable independientemente
- Cada clase tiene una única razón para cambiar
- Más fácil añadir nuevas fuentes de respuesta
- Más fácil cambiar lógica de cleanup sin tocar response
