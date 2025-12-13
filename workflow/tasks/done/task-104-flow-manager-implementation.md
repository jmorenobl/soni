## Task: 1.4 - FlowManager Implementation

**ID de tarea:** 104
**Hito:** Phase 1 - Core Foundation
**Dependencias:** Task 101 (Core Type Definitions)
**Duración estimada:** 4-6 horas

### Objetivo

Implement FlowManager class with stack operations for managing flow instances. This is a core component that handles flow stack management following the Single Responsibility Principle.

### Contexto

FlowManager encapsulates all flow stack operations, enabling flow interruptions, resumption, concurrent flow instances, and context-aware digression handling. It uses a Pure Data approach compatible with LangGraph's persistence model.

**Reference:**
- [docs/implementation/01-phase-1-foundation.md](../../docs/implementation/01-phase-1-foundation.md) - Task 1.4
- [docs/design/07-flow-management.md](../../docs/design/07-flow-management.md) - Complete FlowManager specification

### Entregables

- [ ] FlowManager class implemented in `src/soni/flow/manager.py`
- [ ] push_flow() method implemented
- [ ] pop_flow() method implemented
- [ ] get_active_context() method implemented
- [ ] get_slot() / set_slot() methods implemented
- [ ] prune_state() method implemented for memory management
- [ ] Stack operations working correctly (LIFO)
- [ ] Pause/resume working for nested flows
- [ ] Data heap working (flow_slots)
- [ ] Memory pruning working
- [ ] Tests passing in `tests/unit/test_flow_manager.py` (>80% coverage)
- [ ] Mypy passes without errors

### Implementación Detallada

#### Paso 1: Create FlowManager Class Structure

**Archivo(s) a crear/modificar:** `src/soni/flow/manager.py`

**Código específico:**

```python
from typing import Any
import time
import uuid
from soni.core.types import DialogueState, FlowContext, FlowState
from soni.core.errors import FlowStackLimitError

class FlowManager:
    """Manages flow stack operations and flow instance data."""

    def __init__(self, max_stack_depth: int = 10) -> None:
        """Initialize FlowManager with optional stack depth limit."""
        self.max_stack_depth = max_stack_depth

    def push_flow(
        self,
        state: DialogueState,
        flow_name: str,
        inputs: dict[str, Any] | None = None,
        reason: str | None = None
    ) -> str:
        """Start a new flow instance."""
        # Check stack depth limit
        if len(state["flow_stack"]) >= self.max_stack_depth:
            raise FlowStackLimitError(
                f"Flow stack depth limit ({self.max_stack_depth}) exceeded",
                current_depth=len(state["flow_stack"]),
                flow_name=flow_name
            )

        # Pause current flow if exists
        if state["flow_stack"]:
            current = state["flow_stack"][-1]
            current["flow_state"] = "paused"
            current["paused_at"] = time.time()
            current["context"] = reason

        # Create new flow context
        flow_id = f"{flow_name}_{uuid.uuid4().hex[:8]}"
        new_context: FlowContext = {
            "flow_id": flow_id,
            "flow_name": flow_name,
            "flow_state": "active",
            "current_step": None,
            "outputs": {},
            "started_at": time.time(),
            "paused_at": None,
            "completed_at": None,
            "context": None
        }

        # Add to stack
        state["flow_stack"].append(new_context)

        # Initialize flow_slots with inputs
        state["flow_slots"][flow_id] = inputs.copy() if inputs else {}

        return flow_id

    def pop_flow(
        self,
        state: DialogueState,
        outputs: dict[str, Any] | None = None,
        result: str = "completed"
    ) -> None:
        """Finish current flow instance."""
        if not state["flow_stack"]:
            return

        # Get current flow
        current = state["flow_stack"].pop()

        # Update flow state
        current["flow_state"] = result
        current["completed_at"] = time.time()
        current["outputs"] = outputs or {}

        # Archive completed flow
        if "completed_flows" not in state["metadata"]:
            state["metadata"]["completed_flows"] = []
        state["metadata"]["completed_flows"].append(current)

        # Prune flow_slots (remove data for completed flow)
        flow_id = current["flow_id"]
        if flow_id in state["flow_slots"]:
            del state["flow_slots"][flow_id]

        # Resume previous flow if exists
        if state["flow_stack"]:
            previous = state["flow_stack"][-1]
            previous["flow_state"] = "active"
            previous["paused_at"] = None
            previous["context"] = None

    def get_active_context(
        self,
        state: DialogueState
    ) -> FlowContext | None:
        """Get the currently active flow context."""
        if not state["flow_stack"]:
            return None
        return state["flow_stack"][-1]

    def get_slot(
        self,
        state: DialogueState,
        slot_name: str
    ) -> Any:
        """Get slot value from active flow."""
        context = self.get_active_context(state)
        if not context:
            return None

        flow_id = context["flow_id"]
        if flow_id not in state["flow_slots"]:
            return None

        return state["flow_slots"][flow_id].get(slot_name)

    def set_slot(
        self,
        state: DialogueState,
        slot_name: str,
        value: Any
    ) -> None:
        """Set slot value in active flow."""
        context = self.get_active_context(state)
        if not context:
            raise ValueError("No active flow to set slot in")

        flow_id = context["flow_id"]
        if flow_id not in state["flow_slots"]:
            state["flow_slots"][flow_id] = {}

        state["flow_slots"][flow_id][slot_name] = value

    def prune_state(
        self,
        state: DialogueState,
        max_completed_flows: int = 50
    ) -> None:
        """Prune old completed flows from metadata to manage memory."""
        if "completed_flows" not in state["metadata"]:
            return

        completed = state["metadata"]["completed_flows"]
        if len(completed) > max_completed_flows:
            # Keep most recent flows
            state["metadata"]["completed_flows"] = completed[-max_completed_flows:]
```

**Explicación:**
- Implement FlowManager class with all required methods
- Use uuid for generating unique flow_id
- Handle stack depth limit with FlowStackLimitError
- Pause/resume flows correctly when pushing/popping
- Archive completed flows in metadata
- Prune flow_slots when flow completes
- Implement memory management with prune_state

#### Paso 2: Create Unit Tests

**Archivo(s) a crear/modificar:** `tests/unit/test_flow_manager.py`

**Código específico:**

```python
import pytest
from soni.flow.manager import FlowManager
from soni.core.types import DialogueState
from soni.core.errors import FlowStackLimitError

@pytest.fixture
def empty_state() -> DialogueState:
    """Create empty dialogue state."""
    return {
        "user_message": "",
        "last_response": "",
        "messages": [],
        "flow_stack": [],
        "flow_slots": {},
        "conversation_state": "idle",
        "current_step": None,
        "waiting_for_slot": None,
        "nlu_result": None,
        "last_nlu_call": None,
        "digression_depth": 0,
        "last_digression_type": None,
        "turn_count": 0,
        "trace": [],
        "metadata": {}
    }

def test_push_flow_creates_instance(empty_state):
    """Test push_flow creates new flow instance."""
    # Arrange
    manager = FlowManager()

    # Act
    flow_id = manager.push_flow(empty_state, "book_flight")

    # Assert
    assert len(empty_state["flow_stack"]) == 1
    assert empty_state["flow_stack"][0]["flow_name"] == "book_flight"
    assert empty_state["flow_stack"][0]["flow_state"] == "active"
    assert flow_id in empty_state["flow_slots"]

def test_pop_flow_archives_completed(empty_state):
    """Test pop_flow archives completed flow."""
    # Arrange
    manager = FlowManager()
    manager.push_flow(empty_state, "book_flight")

    # Act
    manager.pop_flow(empty_state, outputs={"booking_ref": "BK-123"})

    # Assert
    assert len(empty_state["flow_stack"]) == 0
    assert len(empty_state["metadata"]["completed_flows"]) == 1
    assert empty_state["metadata"]["completed_flows"][0]["outputs"]["booking_ref"] == "BK-123"

def test_nested_flows_pause_resume(empty_state):
    """Test nested flows pause and resume correctly."""
    # Arrange
    manager = FlowManager()

    # Act
    flow_1_id = manager.push_flow(empty_state, "flow_1")
    assert empty_state["flow_stack"][0]["flow_state"] == "active"

    flow_2_id = manager.push_flow(empty_state, "flow_2")

    # Assert
    assert empty_state["flow_stack"][0]["flow_state"] == "paused"
    assert empty_state["flow_stack"][1]["flow_state"] == "active"

    # Act - Pop flow_2
    manager.pop_flow(empty_state)

    # Assert - flow_1 resumed
    assert empty_state["flow_stack"][0]["flow_state"] == "active"
```

**Explicación:**
- Create comprehensive tests for all FlowManager methods
- Test stack operations (push, pop)
- Test pause/resume behavior
- Test slot get/set operations
- Test stack depth limit
- Test memory pruning
- Use AAA pattern with clear comments

### Tests Requeridos

**Archivo de tests:** `tests/unit/test_flow_manager.py`

**Tests específicos a implementar:**

```python
import pytest
from soni.flow.manager import FlowManager
from soni.core.types import DialogueState
from soni.core.errors import FlowStackLimitError

@pytest.fixture
def empty_state() -> DialogueState:
    """Create empty dialogue state."""
    return {
        "user_message": "",
        "last_response": "",
        "messages": [],
        "flow_stack": [],
        "flow_slots": {},
        "conversation_state": "idle",
        "current_step": None,
        "waiting_for_slot": None,
        "nlu_result": None,
        "last_nlu_call": None,
        "digression_depth": 0,
        "last_digression_type": None,
        "turn_count": 0,
        "trace": [],
        "metadata": {}
    }

def test_push_flow_creates_instance(empty_state):
    """Test push_flow creates new flow instance."""
    # Arrange
    manager = FlowManager()

    # Act
    flow_id = manager.push_flow(empty_state, "book_flight")

    # Assert
    assert len(empty_state["flow_stack"]) == 1
    assert empty_state["flow_stack"][0]["flow_name"] == "book_flight"
    assert empty_state["flow_stack"][0]["flow_state"] == "active"
    assert flow_id in empty_state["flow_slots"]

def test_pop_flow_archives_completed(empty_state):
    """Test pop_flow archives completed flow."""
    # Arrange
    manager = FlowManager()
    manager.push_flow(empty_state, "book_flight")

    # Act
    manager.pop_flow(empty_state, outputs={"booking_ref": "BK-123"})

    # Assert
    assert len(empty_state["flow_stack"]) == 0
    assert len(empty_state["metadata"]["completed_flows"]) == 1
    assert empty_state["metadata"]["completed_flows"][0]["outputs"]["booking_ref"] == "BK-123"

def test_nested_flows_pause_resume(empty_state):
    """Test nested flows pause and resume correctly."""
    # Arrange
    manager = FlowManager()

    # Act
    flow_1_id = manager.push_flow(empty_state, "flow_1")
    assert empty_state["flow_stack"][0]["flow_state"] == "active"

    flow_2_id = manager.push_flow(empty_state, "flow_2")

    # Assert
    assert empty_state["flow_stack"][0]["flow_state"] == "paused"
    assert empty_state["flow_stack"][1]["flow_state"] == "active"

    # Act - Pop flow_2
    manager.pop_flow(empty_state)

    # Assert - flow_1 resumed
    assert empty_state["flow_stack"][0]["flow_state"] == "active"

def test_get_set_slot(empty_state):
    """Test get_slot and set_slot operations."""
    # Arrange
    manager = FlowManager()
    manager.push_flow(empty_state, "book_flight")

    # Act
    manager.set_slot(empty_state, "origin", "NYC")
    value = manager.get_slot(empty_state, "origin")

    # Assert
    assert value == "NYC"

def test_stack_depth_limit(empty_state):
    """Test stack depth limit enforcement."""
    # Arrange
    manager = FlowManager(max_stack_depth=2)

    # Act
    manager.push_flow(empty_state, "flow_1")
    manager.push_flow(empty_state, "flow_2")

    # Assert
    with pytest.raises(FlowStackLimitError):
        manager.push_flow(empty_state, "flow_3")
```

### Criterios de Éxito

- [ ] All methods implemented
- [ ] Stack operations working correctly
- [ ] Pause/resume working for nested flows
- [ ] Data heap working (flow_slots)
- [ ] Memory pruning working
- [ ] Tests passing (`uv run pytest tests/unit/test_flow_manager.py -v`)
- [ ] Coverage > 80% (`uv run pytest tests/unit/test_flow_manager.py --cov=soni.flow --cov-report=term-missing`)
- [ ] Mypy passes (`uv run mypy src/soni/flow/manager.py`)

### Validación Manual

**Comandos para validar:**

```bash
# Type checking
uv run mypy src/soni/flow/manager.py

# Tests
uv run pytest tests/unit/test_flow_manager.py -v

# Coverage
uv run pytest tests/unit/test_flow_manager.py --cov=soni.flow --cov-report=term-missing

# Linting
uv run ruff check src/soni/flow/manager.py
uv run ruff format src/soni/flow/manager.py
```

**Resultado esperado:**
- Mypy shows no errors
- All tests pass
- Coverage > 80%
- Ruff shows no linting errors
- Stack operations work correctly
- Pause/resume works for nested flows

### Referencias

- [docs/implementation/01-phase-1-foundation.md](../../docs/implementation/01-phase-1-foundation.md) - Task 1.4
- [docs/design/07-flow-management.md](../../docs/design/07-flow-management.md) - Complete FlowManager specification

### Notas Adicionales

- FlowManager uses Pure Data approach (no side effects, operates on state)
- Flow IDs are generated using uuid for uniqueness
- Stack depth limit is configurable (default 10)
- Completed flows are archived in metadata for history
- flow_slots are pruned when flow completes to manage memory
- prune_state() can be called periodically to limit completed_flows history
