# Phase 1: Core Foundation

**Goal**: Establish type-safe foundation with interfaces, core types, and flow management.

**Duration**: 2-3 days

**Dependencies**: None (starting point)

## Overview

This phase creates the foundational layer that all other components depend on:
- TypedDict state structures
- Protocol interfaces
- Core error classes
- FlowManager implementation

## Tasks

### Task 1.1: Core Type Definitions

**Status**: 📋 Backlog

**File**: `src/soni/core/types.py`

**What**: Define all TypedDict structures for state management.

**Why**: TypedDict is required by LangGraph and provides runtime type safety.

**Implementation**:

```python
from typing import TypedDict, Literal, Any

# Flow states
FlowState = Literal["active", "paused", "completed", "cancelled", "abandoned", "error"]

class FlowContext(TypedDict):
    """Context for a specific instance of a flow."""
    flow_id: str
    flow_name: str
    flow_state: FlowState
    current_step: str | None
    outputs: dict[str, Any]
    started_at: float
    paused_at: float | None
    completed_at: float | None
    context: str | None

class DialogueState(TypedDict):
    """Complete dialogue state for LangGraph."""
    # User communication
    user_message: str
    last_response: str
    messages: list[dict[str, Any]]  # Will use Annotated with add_messages in Phase 4

    # Flow management
    flow_stack: list[FlowContext]
    flow_slots: dict[str, dict[str, Any]]

    # State tracking
    conversation_state: str
    current_step: str | None
    waiting_for_slot: str | None

    # NLU results
    nlu_result: dict[str, Any] | None
    last_nlu_call: float | None

    # Digression tracking
    digression_depth: int
    last_digression_type: str | None

    # Metadata
    turn_count: int
    trace: list[dict[str, Any]]
    metadata: dict[str, Any]

# Conversation states
ConversationState = Literal[
    "idle",
    "understanding",
    "waiting_for_slot",
    "validating_slot",
    "collecting",
    "executing_action",
    "generating_response",
    "error"
]

class RuntimeContext(TypedDict):
    """Runtime context with injected dependencies (for LangGraph context_schema)."""
    flow_manager: Any  # Will be typed properly with interfaces
    nlu_provider: Any
    action_handler: Any
    scope_manager: Any
    normalizer: Any
```

**Tests**:

`tests/unit/test_types.py`:
```python
import pytest
from soni.core.types import FlowContext, DialogueState, ConversationState

def test_flow_context_structure():
    """Test FlowContext has all required fields."""
    # Arrange & Act
    context: FlowContext = {
        "flow_id": "test_123",
        "flow_name": "test_flow",
        "flow_state": "active",
        "current_step": None,
        "outputs": {},
        "started_at": 1234567890.0,
        "paused_at": None,
        "completed_at": None,
        "context": None
    }

    # Assert
    assert context["flow_id"] == "test_123"
    assert context["flow_state"] == "active"

def test_dialogue_state_initialization():
    """Test DialogueState can be initialized with defaults."""
    # Arrange & Act
    state: DialogueState = {
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

    # Assert
    assert state["conversation_state"] == "idle"
    assert state["turn_count"] == 0
    assert len(state["flow_stack"]) == 0
```

**Completion Criteria**:
- [ ] All TypedDict classes defined
- [ ] Literal types for enums
- [ ] Imports working (no circular dependencies)
- [ ] Tests passing
- [ ] Mypy passes

---

### Task 1.2: Protocol Interfaces

**Status**: 📋 Backlog

**File**: `src/soni/core/interfaces.py`

**What**: Define Protocol interfaces for all major components.

**Why**: Dependency Inversion Principle - depend on abstractions, not implementations.

**Implementation**:

```python
from typing import Protocol, Any
from soni.core.types import DialogueState, FlowContext

class INLUProvider(Protocol):
    """Interface for NLU providers."""

    async def understand(
        self,
        user_message: str,
        dialogue_context: dict[str, Any]
    ) -> dict[str, Any]:
        """Understand user message and return NLU result."""
        ...

class IActionHandler(Protocol):
    """Interface for action execution."""

    async def execute(
        self,
        action_name: str,
        inputs: dict[str, Any]
    ) -> dict[str, Any]:
        """Execute an action and return results."""
        ...

class IScopeManager(Protocol):
    """Interface for scope management (dynamic action filtering)."""

    def get_available_actions(
        self,
        state: DialogueState
    ) -> list[str]:
        """Get available actions based on current state."""
        ...

    def get_available_flows(
        self,
        state: DialogueState
    ) -> list[str]:
        """Get available flows based on current state."""
        ...

class INormalizer(Protocol):
    """Interface for value normalization."""

    async def normalize(
        self,
        slot_name: str,
        raw_value: Any
    ) -> Any:
        """Normalize and validate slot value."""
        ...

class IFlowManager(Protocol):
    """Interface for flow stack management."""

    def push_flow(
        self,
        state: DialogueState,
        flow_name: str,
        inputs: dict[str, Any] | None = None,
        reason: str | None = None
    ) -> str:
        """Start a new flow instance."""
        ...

    def pop_flow(
        self,
        state: DialogueState,
        outputs: dict[str, Any] | None = None,
        result: str = "completed"
    ) -> None:
        """Finish current flow instance."""
        ...

    def get_active_context(
        self,
        state: DialogueState
    ) -> FlowContext | None:
        """Get the currently active flow context."""
        ...

    def get_slot(
        self,
        state: DialogueState,
        slot_name: str
    ) -> Any:
        """Get slot value from active flow."""
        ...

    def set_slot(
        self,
        state: DialogueState,
        slot_name: str,
        value: Any
    ) -> None:
        """Set slot value in active flow."""
        ...
```

**Tests**:

`tests/unit/test_interfaces.py`:
```python
import pytest
from soni.core.interfaces import INLUProvider, IFlowManager
from soni.core.types import DialogueState

def test_protocol_type_checking():
    """Test that protocols can be used for type hints."""
    # Arrange
    def process_with_nlu(nlu: INLUProvider) -> None:
        """Function accepting INLUProvider."""
        pass

    # Act & Assert - This should not raise type errors
    # (actual implementation test will be in integration)
    assert INLUProvider is not None
```

**Completion Criteria**:
- [ ] All Protocol interfaces defined
- [ ] Methods have type hints
- [ ] Docstrings present
- [ ] No circular imports
- [ ] Mypy passes

---

### Task 1.3: Core Errors

**Status**: 📋 Backlog

**File**: `src/soni/core/errors.py`

**What**: Define exception hierarchy for the framework.

**Why**: Proper error handling with specific exception types.

**Implementation**:

```python
class SoniError(Exception):
    """Base exception for all Soni errors."""

    def __init__(self, message: str, **context: Any) -> None:
        super().__init__(message)
        self.message = message
        self.context = context

    def __str__(self) -> str:
        if self.context:
            ctx_str = ", ".join(f"{k}={v}" for k, v in self.context.items())
            return f"{self.message} ({ctx_str})"
        return self.message

class NLUError(SoniError):
    """Error during NLU processing."""
    pass

class ValidationError(SoniError):
    """Error during validation."""
    pass

class ActionNotFoundError(SoniError):
    """Action not found in registry."""
    pass

class FlowStackLimitError(SoniError):
    """Flow stack depth limit exceeded."""
    pass

class ConfigurationError(SoniError):
    """Configuration error."""
    pass

class PersistenceError(SoniError):
    """Error during state persistence."""
    pass

class CompilationError(SoniError):
    """Error during YAML compilation."""
    pass
```

**Tests**:

`tests/unit/test_errors.py`:
```python
import pytest
from soni.core.errors import (
    SoniError,
    ValidationError,
    FlowStackLimitError
)

def test_base_error_with_context():
    """Test SoniError includes context in message."""
    # Arrange & Act
    error = SoniError(
        "Something failed",
        user_id="123",
        flow="book_flight"
    )

    # Assert
    assert "Something failed" in str(error)
    assert "user_id=123" in str(error)
    assert "flow=book_flight" in str(error)

def test_validation_error_inheritance():
    """Test ValidationError is a SoniError."""
    # Arrange & Act
    error = ValidationError("Invalid slot", slot="origin", value="invalid")

    # Assert
    assert isinstance(error, SoniError)
    assert "Invalid slot" in str(error)
```

**Completion Criteria**:
- [ ] All error classes defined
- [ ] Context support working
- [ ] Tests passing
- [ ] Docstrings present

---

### Task 1.4: FlowManager Implementation

**Status**: 📋 Backlog

**File**: `src/soni/flow/manager.py`

**What**: Implement FlowManager class with stack operations.

**Why**: Core component for flow stack management (SRP).

**Implementation**:

See `docs/design/07-flow-management.md` for complete specification.

Key methods:
- `push_flow()`: Start new flow
- `pop_flow()`: Finish current flow
- `get_active_context()`: Get current flow
- `get_slot()` / `set_slot()`: Data access
- `prune_state()`: Memory management

**Tests**:

`tests/unit/test_flow_manager.py`:
```python
import pytest
from soni.flow.manager import FlowManager
from soni.core.types import DialogueState

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

**Completion Criteria**:
- [ ] All methods implemented
- [ ] Stack operations working
- [ ] Pause/resume working
- [ ] Data heap working (flow_slots)
- [ ] Memory pruning working
- [ ] Tests passing (>80% coverage)
- [ ] Mypy passes

---

### Task 1.5: State Initialization Helpers

**Status**: 📋 Backlog

**File**: `src/soni/core/state.py`

**What**: Create helper functions for DialogueState initialization.

**Why**: Reduce boilerplate and ensure consistent initialization.

**Implementation**:

```python
from soni.core.types import DialogueState
import time

def create_empty_state() -> DialogueState:
    """Create an empty DialogueState with defaults."""
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

def create_initial_state(user_message: str) -> DialogueState:
    """Create initial state for new conversation."""
    state = create_empty_state()
    state["user_message"] = user_message
    state["conversation_state"] = "understanding"
    state["turn_count"] = 1
    state["trace"] = [{
        "turn": 1,
        "user_message": user_message,
        "timestamp": time.time()
    }]
    return state
```

**Tests**:

`tests/unit/test_state.py`:
```python
def test_create_empty_state():
    """Test create_empty_state returns valid state."""
    # Arrange & Act
    state = create_empty_state()

    # Assert
    assert state["conversation_state"] == "idle"
    assert state["turn_count"] == 0
    assert len(state["flow_stack"]) == 0

def test_create_initial_state():
    """Test create_initial_state with message."""
    # Arrange & Act
    state = create_initial_state("Hello")

    # Assert
    assert state["user_message"] == "Hello"
    assert state["conversation_state"] == "understanding"
    assert state["turn_count"] == 1
    assert len(state["trace"]) == 1
```

**Completion Criteria**:
- [ ] Helper functions implemented
- [ ] Tests passing
- [ ] Docstrings present

---

## Phase 1 Completion Checklist

Before proceeding to Phase 2, verify:

- [ ] All Task 1.x completed
- [ ] All tests passing
- [ ] Mypy passes: `uv run mypy src/soni/core src/soni/flow`
- [ ] Ruff passes: `uv run ruff check .`
- [ ] Code committed to feature branch
- [ ] Phase 1 review complete

## Phase 1 Validation

Run this command to validate Phase 1:

```bash
# Type checking
uv run mypy src/soni/core src/soni/flow

# Tests
uv run pytest tests/unit/test_types.py -v
uv run pytest tests/unit/test_interfaces.py -v
uv run pytest tests/unit/test_errors.py -v
uv run pytest tests/unit/test_flow_manager.py -v
uv run pytest tests/unit/test_state.py -v

# Coverage
uv run pytest tests/unit/ --cov=soni.core --cov=soni.flow --cov-report=term-missing
```

**Expected Output**:
- All tests passing
- Coverage > 80%
- Zero mypy errors

## Next Steps

Once Phase 1 is complete:

1. Commit all changes
2. Merge feature branch if desired
3. Proceed to **[02-phase-2-state.md](02-phase-2-state.md)**

---

**Phase**: 1 of 5
**Status**: 📋 Backlog
**Estimated Duration**: 2-3 days
