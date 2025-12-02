# State Transition Validation Approach

**Document Version**: 1.0
**Last Updated**: 2025-12-02
**Status**: Recommendation

## Context

The question arose: Should we use `pytransitions/transitions` library or implement our own state machine?

## Analysis

### Why NOT Use `transitions`

**Reason 1: LangGraph Already Manages State**

In Soni's architecture:
```python
graph = StateGraph(DialogueState)  # LangGraph owns the state
result = await graph.ainvoke(state.to_dict())  # State is a dict
```

`transitions` assumes it controls the state object, but:
- LangGraph serializes DialogueState to dict
- Nodes update state by returning dicts
- LangGraph merges updates automatically

**Problem**: You can't wrap DialogueState with `transitions.Machine` because LangGraph needs a dict, not an object with methods.

**Reason 2: Transitions Already Defined Implicitly**

State transitions happen in nodes:
```python
# In understand_node
return {"conversation_state": ConversationState.UNDERSTANDING}

# In collect_slot_node
return {"conversation_state": ConversationState.WAITING_FOR_SLOT}
```

With `transitions`, you'd need:
```python
await machine.trigger('need_slot')  # Where do you call this?
# State is in LangGraph, not in the machine object
```

**Reason 3: No Real Benefit**

Benefits of `transitions`:
- ✅ Transition validation → Can do with simple function
- ✅ Structured callbacks → Already have (code in nodes)
- ✅ Debugging → LangGraph has excellent tracing
- ✅ Async support → Everything already async

**Conclusion**: Adds complexity without real benefit in this specific architecture.

---

## Recommended Approach: Lightweight Validation

Instead of `transitions`, implement **simple transition validation**:

### Implementation

```python
# File: src/soni/core/state_validation.py

from enum import Enum
from typing import Any

from soni.core.state import ConversationState


class StateTransitionValidator:
    """
    Validates conversation state transitions.

    This provides the main benefit of a state machine library
    (transition validation) without the complexity of integrating
    with LangGraph's state management.
    """

    # Define valid transitions
    VALID_TRANSITIONS: dict[ConversationState, list[ConversationState]] = {
        ConversationState.IDLE: [
            ConversationState.UNDERSTANDING,
            ConversationState.ERROR,
        ],
        ConversationState.UNDERSTANDING: [
            ConversationState.WAITING_FOR_SLOT,
            ConversationState.EXECUTING_ACTION,
            ConversationState.IDLE,
            ConversationState.ERROR,
        ],
        ConversationState.WAITING_FOR_SLOT: [
            ConversationState.VALIDATING_SLOT,
            ConversationState.UNDERSTANDING,  # Intent change
            ConversationState.ERROR,
        ],
        ConversationState.VALIDATING_SLOT: [
            ConversationState.WAITING_FOR_SLOT,  # Validation failed
            ConversationState.UNDERSTANDING,  # Check next step
            ConversationState.EXECUTING_ACTION,  # All slots ready
            ConversationState.ERROR,
        ],
        ConversationState.EXECUTING_ACTION: [
            ConversationState.COMPLETED,
            ConversationState.WAITING_FOR_SLOT,  # Need more data
            ConversationState.CONFIRMING,  # Need confirmation
            ConversationState.ERROR,
        ],
        ConversationState.CONFIRMING: [
            ConversationState.EXECUTING_ACTION,  # Confirmed
            ConversationState.COMPLETED,  # Cancelled
            ConversationState.UNDERSTANDING,  # Changed mind
            ConversationState.ERROR,
        ],
        ConversationState.COMPLETED: [
            ConversationState.IDLE,  # Start new task
        ],
        ConversationState.ERROR: [
            ConversationState.UNDERSTANDING,  # Retry
            ConversationState.IDLE,  # Give up
        ],
    }

    @classmethod
    def is_valid_transition(
        cls,
        from_state: ConversationState,
        to_state: ConversationState,
    ) -> bool:
        """
        Check if transition is valid.

        Args:
            from_state: Current state
            to_state: Target state

        Returns:
            True if transition is allowed, False otherwise
        """
        valid_targets = cls.VALID_TRANSITIONS.get(from_state, [])
        return to_state in valid_targets

    @classmethod
    def validate_transition(
        cls,
        from_state: ConversationState,
        to_state: ConversationState,
    ) -> None:
        """
        Validate transition and raise error if invalid.

        Args:
            from_state: Current state
            to_state: Target state

        Raises:
            ValueError: If transition is invalid
        """
        if not cls.is_valid_transition(from_state, to_state):
            valid_targets = cls.VALID_TRANSITIONS.get(from_state, [])
            raise ValueError(
                f"Invalid state transition: {from_state.value} → {to_state.value}. "
                f"Valid targets from {from_state.value}: "
                f"{[s.value for s in valid_targets]}"
            )

    @classmethod
    def get_valid_transitions(
        cls,
        from_state: ConversationState,
    ) -> list[ConversationState]:
        """
        Get list of valid target states from current state.

        Args:
            from_state: Current state

        Returns:
            List of valid target states
        """
        return cls.VALID_TRANSITIONS.get(from_state, [])


def validate_state_update(
    current_state: dict[str, Any],
    updates: dict[str, Any],
) -> None:
    """
    Validate state updates from node execution.

    This function is called after a node returns updates to ensure
    that any conversation_state changes are valid.

    Args:
        current_state: Current dialogue state (dict)
        updates: Updates returned by node (dict)

    Raises:
        ValueError: If state transition is invalid
    """
    # Check if conversation_state is being updated
    if "conversation_state" not in updates:
        return  # No state change, nothing to validate

    # Get current and target states
    current_conv_state = ConversationState(
        current_state.get("conversation_state", ConversationState.IDLE)
    )
    target_conv_state = ConversationState(updates["conversation_state"])

    # Validate transition
    StateTransitionValidator.validate_transition(
        current_conv_state,
        target_conv_state,
    )
```

### Usage in Nodes

```python
# In node wrapper (src/soni/dm/nodes.py)

async def wrapped_node(state: DialogueState | dict[str, Any]) -> dict[str, Any]:
    # Convert to dict for validation
    current_state_dict = state.to_dict() if hasattr(state, 'to_dict') else state

    # Execute node
    updates = await node_fn(state)

    # Validate state transition (if any)
    try:
        validate_state_update(current_state_dict, updates)
    except ValueError as e:
        logger.error(f"Invalid state transition in node '{node_name}': {e}")
        # Return error state
        return {
            "conversation_state": ConversationState.ERROR,
            "last_response": "An internal error occurred. Please try again.",
            "metadata": {
                "error": {
                    "type": "invalid_state_transition",
                    "message": str(e),
                    "node": node_name,
                }
            }
        }

    return updates
```

### Testing

```python
# tests/unit/test_state_validation.py

import pytest
from soni.core.state import ConversationState
from soni.core.state_validation import StateTransitionValidator


def test_valid_transition():
    """Test that valid transitions are allowed"""
    # IDLE → UNDERSTANDING is valid
    assert StateTransitionValidator.is_valid_transition(
        ConversationState.IDLE,
        ConversationState.UNDERSTANDING,
    )


def test_invalid_transition():
    """Test that invalid transitions are rejected"""
    # IDLE → COMPLETED is invalid (can't complete without doing anything)
    assert not StateTransitionValidator.is_valid_transition(
        ConversationState.IDLE,
        ConversationState.COMPLETED,
    )


def test_validate_transition_raises():
    """Test that validate_transition raises on invalid transition"""
    with pytest.raises(ValueError, match="Invalid state transition"):
        StateTransitionValidator.validate_transition(
            ConversationState.IDLE,
            ConversationState.COMPLETED,
        )


def test_get_valid_transitions():
    """Test getting list of valid transitions"""
    valid = StateTransitionValidator.get_valid_transitions(
        ConversationState.IDLE
    )

    assert ConversationState.UNDERSTANDING in valid
    assert ConversationState.ERROR in valid
    assert ConversationState.COMPLETED not in valid
```

---

## Benefits of This Approach

### 1. **Simple and Lightweight**
- No external dependency
- ~100 lines of code
- Easy to understand and modify

### 2. **Integrates Perfectly with LangGraph**
- Validates state dict updates
- No conflict with LangGraph's state management
- Works with checkpointing

### 3. **Provides Core Benefit**
- Transition validation (main benefit of `transitions`)
- Catches invalid transitions early
- Clear error messages

### 4. **Easy to Test**
- Simple functions, easy to unit test
- No complex setup required

### 5. **No Learning Curve**
- Team doesn't need to learn `transitions` API
- Obvious what's happening

---

## What You Lose (vs `transitions`)

### 1. **No Visual State Machine Diagram**
- `transitions` can generate diagrams
- **Mitigation**: Your design docs already have diagrams

### 2. **No Automatic Callbacks**
- `transitions` has `on_enter_state()`, `on_exit_state()`
- **Mitigation**: You have explicit code in nodes (clearer anyway)

### 3. **No State Machine Introspection**
- `transitions` has `machine.get_triggers()`, etc.
- **Mitigation**: You have `get_valid_transitions()` for this

### 4. **No Queued Transitions**
- `transitions.AsyncMachine(queued=True)` prevents race conditions
- **Mitigation**: LangGraph handles this via checkpointing

---

## Alternative: Minimal State Machine Class

If you want slightly more structure, create a minimal state machine class:

```python
class ConversationStateMachine:
    """
    Minimal state machine for conversation states.

    This wraps DialogueState to provide state machine semantics
    without conflicting with LangGraph.
    """

    def __init__(self, state: DialogueState):
        self.state = state
        self.validator = StateTransitionValidator

    def transition_to(self, new_state: ConversationState) -> dict[str, Any]:
        """
        Transition to new state with validation.

        Returns:
            Dict of updates to apply to DialogueState
        """
        # Validate
        self.validator.validate_transition(
            self.state.conversation_state,
            new_state,
        )

        # Return updates (for LangGraph)
        return {"conversation_state": new_state}

    def can_transition_to(self, new_state: ConversationState) -> bool:
        """Check if transition is valid"""
        return self.validator.is_valid_transition(
            self.state.conversation_state,
            new_state,
        )

    def get_valid_transitions(self) -> list[ConversationState]:
        """Get valid target states"""
        return self.validator.get_valid_transitions(
            self.state.conversation_state
        )
```

**Usage**:
```python
# In a node
machine = ConversationStateMachine(state)

if machine.can_transition_to(ConversationState.WAITING_FOR_SLOT):
    updates = machine.transition_to(ConversationState.WAITING_FOR_SLOT)
    updates["waiting_for_slot"] = slot_name
    return updates
```

---

## Recommendation

**Use the lightweight validation approach** (Option 1):

1. ✅ **Simple**: ~100 lines, no dependencies
2. ✅ **Effective**: Provides transition validation
3. ✅ **Compatible**: Works perfectly with LangGraph
4. ✅ **Maintainable**: Easy to understand and modify
5. ✅ **Testable**: Simple unit tests

**Don't use `transitions`** because:
1. ❌ Conflicts with LangGraph's state management
2. ❌ Adds complexity without proportional benefit
3. ❌ Requires adapters to integrate
4. ❌ Learning curve for the team

---

## Implementation Plan

### Phase 1: Add Validation (30 minutes)
1. Create `src/soni/core/state_validation.py`
2. Define `VALID_TRANSITIONS` dict
3. Implement `StateTransitionValidator` class

### Phase 2: Integrate with Nodes (1 hour)
1. Add `validate_state_update()` to node wrapper
2. Handle validation errors gracefully
3. Log invalid transitions

### Phase 3: Add Tests (1 hour)
1. Unit tests for validator
2. Integration tests for node transitions
3. E2E tests for complete flows

**Total**: ~2.5 hours

---

## Conclusion

**Recommendation**: Implement lightweight validation without `transitions`.

**Rationale**:
- Your architecture (LangGraph + DialogueState) doesn't fit `transitions`' assumptions
- Lightweight validation provides the core benefit (transition validation)
- Simpler, easier to maintain, no external dependencies
- Works perfectly with LangGraph's state management

This approach gives you the safety of state machine validation without the complexity of integrating a full state machine library that wasn't designed for your use case.

---

**Next**: Implement `StateTransitionValidator` as part of Phase 1 (State Machine Foundation)
