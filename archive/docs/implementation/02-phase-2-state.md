# Phase 2: State Management & Validation

**Goal**: Implement state machine with validation, transitions, and memory management.

**Duration**: 2-3 days

**Dependencies**: Phase 1 (Core Foundation)

## Overview

This phase builds on Phase 1 to create a robust state management system:
- State transition validation
- Conversation state machine
- Memory management
- State serialization

## Tasks

### Task 2.1: State Transition Validator

**Status**: 📋 Backlog

**File**: `src/soni/core/validators.py`

**What**: Implement state transition validation based on state machine.

**Why**: Ensure state transitions follow the designed state machine (see `docs/design/04-state-machine.md`).

**Implementation**:

```python
from soni.core.types import ConversationState, DialogueState
from soni.core.errors import ValidationError

# Valid state transitions (see state machine diagram)
VALID_TRANSITIONS: dict[str, list[str]] = {
    "idle": ["understanding"],
    "understanding": ["waiting_for_slot", "validating_slot", "executing_action", "error", "idle"],
    "waiting_for_slot": ["understanding"],
    "validating_slot": ["collecting", "waiting_for_slot", "error"],
    "collecting": ["understanding", "validating_slot", "executing_action"],
    "executing_action": ["generating_response", "error"],
    "generating_response": ["idle", "understanding"],
    "error": ["idle", "understanding"]
}

def validate_transition(
    current_state: str,
    next_state: str
) -> None:
    """
    Validate state transition is allowed.

    Args:
        current_state: Current conversation state
        next_state: Target conversation state

    Raises:
        ValidationError: If transition is not valid
    """
    valid_next_states = VALID_TRANSITIONS.get(current_state, [])

    if next_state not in valid_next_states:
        raise ValidationError(
            f"Invalid state transition: {current_state} → {next_state}",
            current=current_state,
            next=next_state,
            valid_transitions=valid_next_states
        )

def validate_state_consistency(state: DialogueState) -> None:
    """
    Validate state internal consistency.

    Args:
        state: Dialogue state to validate

    Raises:
        ValidationError: If state is inconsistent
    """
    # Check flow_stack consistency
    active_flow_ids = {ctx["flow_id"] for ctx in state["flow_stack"]}
    slot_flow_ids = set(state["flow_slots"].keys())

    # All active flows must have slots
    missing_slots = active_flow_ids - slot_flow_ids
    if missing_slots:
        raise ValidationError(
            "Active flows missing slot storage",
            missing=list(missing_slots)
        )

    # Check waiting_for_slot requires active flow
    if state["waiting_for_slot"] and not state["flow_stack"]:
        raise ValidationError(
            "Cannot wait for slot without active flow",
            slot=state["waiting_for_slot"]
        )

    # Check conversation_state consistency
    if state["conversation_state"] == "waiting_for_slot":
        if not state["waiting_for_slot"]:
            raise ValidationError(
                "State is waiting_for_slot but waiting_for_slot is None"
            )
```

**Tests**:

`tests/unit/test_validators.py`:
```python
import pytest
from soni.core.validators import validate_transition, validate_state_consistency
from soni.core.errors import ValidationError
from soni.core.state import create_empty_state

def test_valid_transition_allowed():
    """Test valid transition doesn't raise error."""
    # Arrange & Act & Assert
    validate_transition("idle", "understanding")  # Should not raise

def test_invalid_transition_raises():
    """Test invalid transition raises ValidationError."""
    # Arrange & Act & Assert
    with pytest.raises(ValidationError) as exc_info:
        validate_transition("idle", "executing_action")

    assert "Invalid state transition" in str(exc_info.value)

def test_state_consistency_valid():
    """Test consistent state passes validation."""
    # Arrange
    state = create_empty_state()

    # Act & Assert
    validate_state_consistency(state)  # Should not raise

def test_state_consistency_missing_slots():
    """Test validation fails when flow has no slots."""
    # Arrange
    state = create_empty_state()
    state["flow_stack"].append({
        "flow_id": "test_123",
        "flow_name": "test",
        "flow_state": "active",
        "current_step": None,
        "outputs": {},
        "started_at": 1234567890.0,
        "paused_at": None,
        "completed_at": None,
        "context": None
    })
    # Note: flow_slots is empty

    # Act & Assert
    with pytest.raises(ValidationError) as exc_info:
        validate_state_consistency(state)

    assert "missing slot storage" in str(exc_info.value)
```

**Completion Criteria**:
- [ ] Transition validation implemented
- [ ] State consistency validation implemented
- [ ] Tests passing
- [ ] Mypy passes

---

### Task 2.2: State Update Wrapper

**Status**: 📋 Backlog

**File**: `src/soni/core/state.py` (add to existing)

**What**: Create safe state update function with validation.

**Why**: Ensure all state updates are validated before applying.

**Implementation**:

```python
from soni.core.validators import validate_transition, validate_state_consistency

def update_state(
    state: DialogueState,
    updates: dict[str, Any],
    validate: bool = True
) -> None:
    """
    Update dialogue state with validation.

    Args:
        state: Current dialogue state (modified in place)
        updates: Partial updates to apply
        validate: Whether to validate transition (default True)

    Raises:
        ValidationError: If update would create invalid state
    """
    # Validate conversation_state transition if changing
    if validate and "conversation_state" in updates:
        validate_transition(
            state["conversation_state"],
            updates["conversation_state"]
        )

    # Apply updates
    for key, value in updates.items():
        if key in state:
            state[key] = value  # type: ignore

    # Validate final state consistency
    if validate:
        validate_state_consistency(state)
```

**Tests**:

`tests/unit/test_state.py` (add to existing):
```python
def test_update_state_valid_transition():
    """Test update_state with valid transition."""
    # Arrange
    state = create_empty_state()
    state["conversation_state"] = "idle"

    # Act
    update_state(state, {"conversation_state": "understanding"})

    # Assert
    assert state["conversation_state"] == "understanding"

def test_update_state_invalid_transition_raises():
    """Test update_state with invalid transition raises."""
    # Arrange
    state = create_empty_state()
    state["conversation_state"] = "idle"

    # Act & Assert
    with pytest.raises(ValidationError):
        update_state(state, {"conversation_state": "executing_action"})
```

**Completion Criteria**:
- [ ] Update wrapper implemented
- [ ] Validation integration working
- [ ] Tests passing

---

### Task 2.3: Memory Management

**Status**: 📋 Backlog

**File**: `src/soni/flow/manager.py` (add to existing)

**What**: Implement state pruning to prevent unbounded growth.

**Why**: State persists across sessions - must limit memory usage.

**Implementation**:

Add to FlowManager class:

```python
def prune_state(self, state: DialogueState) -> None:
    """
    Prune state to prevent unbounded memory growth.

    Removes:
    - Orphaned flow_slots (flows no longer in stack)
    - Excess completed flows beyond limit
    - Old trace entries beyond limit
    """
    # 1. Prune orphan flow slots
    active_ids = {ctx["flow_id"] for ctx in state["flow_stack"]}
    orphan_ids = [fid for fid in state["flow_slots"] if fid not in active_ids]

    for fid in orphan_ids:
        del state["flow_slots"][fid]

    # 2. Prune completed flows (keep last N)
    max_completed = 10  # TODO: Make configurable
    completed = state["metadata"].get("completed_flows", [])

    if len(completed) > max_completed:
        state["metadata"]["completed_flows"] = completed[-max_completed:]

    # 3. Prune trace (keep last N turns)
    max_trace = 50  # TODO: Make configurable
    if len(state["trace"]) > max_trace:
        state["trace"] = state["trace"][-max_trace:]
```

**Tests**:

`tests/unit/test_flow_manager.py` (add to existing):
```python
def test_prune_state_removes_orphan_slots(empty_state):
    """Test prune_state removes orphaned flow_slots."""
    # Arrange
    manager = FlowManager()

    # Create and complete a flow (should leave orphan slot)
    flow_id = manager.push_flow(empty_state, "test_flow")
    manager.pop_flow(empty_state)

    # Manually add orphan slot
    empty_state["flow_slots"]["orphan_123"] = {"data": "test"}

    # Act
    manager.prune_state(empty_state)

    # Assert
    assert "orphan_123" not in empty_state["flow_slots"]

def test_prune_state_limits_completed_flows(empty_state):
    """Test prune_state limits completed flows."""
    # Arrange
    manager = FlowManager()

    # Create many completed flows
    for i in range(15):
        manager.push_flow(empty_state, f"flow_{i}")
        manager.pop_flow(empty_state)

    # Act
    manager.prune_state(empty_state)

    # Assert
    assert len(empty_state["metadata"]["completed_flows"]) == 10
```

**Completion Criteria**:
- [ ] Pruning logic implemented
- [ ] Orphan slots removed
- [ ] Completed flows limited
- [ ] Trace limited
- [ ] Tests passing

---

### Task 2.4: State Serialization

**Status**: 📋 Backlog

**File**: `src/soni/core/state.py` (add to existing)

**What**: Implement state serialization/deserialization helpers.

**Why**: Testing and debugging require state snapshots.

**Implementation**:

```python
import json
from typing import Any

def state_to_dict(state: DialogueState) -> dict[str, Any]:
    """
    Serialize DialogueState to JSON-compatible dict.

    Args:
        state: Dialogue state

    Returns:
        JSON-serializable dictionary
    """
    # DialogueState is already a dict (TypedDict), but ensure deep copy
    import copy
    return copy.deepcopy(state)

def state_from_dict(data: dict[str, Any]) -> DialogueState:
    """
    Deserialize DialogueState from dict.

    Args:
        data: Dictionary with state data

    Returns:
        DialogueState

    Raises:
        ValidationError: If data is invalid
    """
    # Validate required fields
    required_fields = [
        "user_message", "last_response", "messages",
        "flow_stack", "flow_slots", "conversation_state",
        "turn_count", "trace", "metadata"
    ]

    for field in required_fields:
        if field not in data:
            raise ValidationError(
                f"Missing required field: {field}",
                field=field
            )

    state: DialogueState = data  # type: ignore

    # Validate consistency
    validate_state_consistency(state)

    return state

def state_to_json(state: DialogueState) -> str:
    """Serialize state to JSON string."""
    return json.dumps(state_to_dict(state), indent=2)

def state_from_json(json_str: str) -> DialogueState:
    """Deserialize state from JSON string."""
    data = json.loads(json_str)
    return state_from_dict(data)
```

**Tests**:

`tests/unit/test_state.py` (add to existing):
```python
def test_state_serialization_roundtrip():
    """Test state can be serialized and deserialized."""
    # Arrange
    original = create_initial_state("Hello")

    # Act
    json_str = state_to_json(original)
    restored = state_from_json(json_str)

    # Assert
    assert restored["user_message"] == original["user_message"]
    assert restored["turn_count"] == original["turn_count"]

def test_state_from_dict_validates():
    """Test state_from_dict validates consistency."""
    # Arrange
    invalid_data = {
        "user_message": "test",
        # Missing required fields
    }

    # Act & Assert
    with pytest.raises(ValidationError):
        state_from_dict(invalid_data)
```

**Completion Criteria**:
- [ ] Serialization implemented
- [ ] Deserialization implemented
- [ ] Validation integrated
- [ ] Roundtrip tests passing

---

## Phase 2 Completion Checklist

Before proceeding to Phase 3, verify:

- [ ] All Task 2.x completed
- [ ] All tests passing
- [ ] Mypy passes: `uv run mypy src/soni`
- [ ] Ruff passes: `uv run ruff check .`
- [ ] State machine working correctly
- [ ] Memory management working
- [ ] Code committed

## Phase 2 Validation

Run this command to validate Phase 2:

```bash
# Type checking
uv run mypy src/soni

# Tests
uv run pytest tests/unit/test_validators.py -v
uv run pytest tests/unit/test_state.py -v
uv run pytest tests/unit/test_flow_manager.py -v

# Coverage
uv run pytest tests/unit/ --cov=soni --cov-report=term-missing

# Minimum coverage: 80%
```

**Expected Output**:
- All tests passing
- Coverage > 80%
- Zero mypy errors

## Integration Test

Create a simple integration test to verify state management:

`tests/integration/test_state_management.py`:
```python
import pytest
from soni.core.state import create_empty_state, update_state
from soni.flow.manager import FlowManager

def test_complete_flow_lifecycle():
    """Test complete flow lifecycle with state management."""
    # Arrange
    state = create_empty_state()
    manager = FlowManager()

    # Act - Start conversation
    update_state(state, {"conversation_state": "understanding"})

    # Start flow
    flow_id = manager.push_flow(state, "book_flight")
    update_state(state, {"conversation_state": "waiting_for_slot"})

    # Collect slot
    manager.set_slot(state, "origin", "Madrid")
    update_state(state, {"conversation_state": "validating_slot"})

    # Complete flow
    manager.pop_flow(state, outputs={"booking_ref": "BK-123"})
    update_state(state, {"conversation_state": "idle"})

    # Prune
    manager.prune_state(state)

    # Assert
    assert state["conversation_state"] == "idle"
    assert len(state["flow_stack"]) == 0
    assert len(state["metadata"]["completed_flows"]) == 1
    assert state["metadata"]["completed_flows"][0]["outputs"]["booking_ref"] == "BK-123"
```

## Next Steps

Once Phase 2 is complete:

1. Commit all changes
2. Review state machine behavior
3. Proceed to **[03-phase-3-nlu.md](03-phase-3-nlu.md)**

---

**Phase**: 2 of 5
**Status**: 📋 Backlog
**Estimated Duration**: 2-3 days
