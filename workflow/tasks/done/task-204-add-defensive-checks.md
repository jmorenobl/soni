## Task: 204 - Add Defensive Checks to Prevent Infinite Loops

**ID de tarea:** 204
**Hito:** Confirmation Flow Fix
**Dependencias:** Task 201, Task 202, Task 203
**Duración estimada:** 2-3 horas

### Objetivo

Add defensive programming checks to prevent infinite loops in confirmation handling and other potentially cyclic flows, even if bugs are introduced in the future.

### Contexto

The infinite loop in Task 201-202 occurred because `confirmation_value` was always `None`, causing the handler to continuously return `conversation_state="confirming"` and routing back to `understand`.

While fixing the root cause is essential, defensive checks add a safety net:
1. Track attempts/retries for specific operations
2. Limit maximum retries before aborting or escalating
3. Detect repeated state transitions (A → B → A → B → ...)
4. Add circuit breakers for known problematic patterns

This prevents similar issues in the future and provides better error messages when things go wrong.

**References:**
- Analysis: `docs/analysis/ANALISIS_ERROR_CONFIRMACION.md` (section "Prevent Infinite Loop")
- handle_confirmation_node: `src/soni/dm/nodes/handle_confirmation.py`
- LangGraph recursion limit error

### Entregables

- [ ] Add retry counter to handle_confirmation_node (max 3 attempts)
- [ ] Add metadata tracking for confirmation attempts
- [ ] Implement state transition cycle detection
- [ ] Add error state handling when max retries exceeded
- [ ] Add logging for retry attempts and circuit breaker triggers
- [ ] Unit tests for defensive checks
- [ ] Integration test verifying circuit breakers work

### Implementación Detallada

#### Paso 1: Add retry counter to handle_confirmation_node

**Archivo(s) a modificar:** `src/soni/dm/nodes/handle_confirmation.py`

**Código específico:**

```python
async def handle_confirmation_node(
    state: DialogueState,
    runtime: Any,
) -> dict:
    """
    Handle user's confirmation response, including automatic correction detection.

    This node processes the user's yes/no response to a confirmation request.
    Includes defensive checks to prevent infinite loops.

    Args:
        state: Current dialogue state
        runtime: Runtime context

    Returns:
        Partial state updates based on confirmation result
    """
    # ✅ ADD retry counter check
    metadata = state.get("metadata", {})
    confirmation_attempts = metadata.get("_confirmation_attempts", 0)

    # Safety check: prevent infinite loop
    MAX_CONFIRMATION_ATTEMPTS = 3
    if confirmation_attempts >= MAX_CONFIRMATION_ATTEMPTS:
        logger.error(
            f"Maximum confirmation attempts ({MAX_CONFIRMATION_ATTEMPTS}) exceeded. "
            f"Aborting confirmation flow."
        )
        # Clear confirmation attempts and return error state
        metadata_cleared = metadata.copy()
        metadata_cleared.pop("_confirmation_attempts", None)

        return {
            "conversation_state": "error",
            "last_response": (
                "I'm having trouble understanding your confirmation. "
                "Let's start over. What would you like to do?"
            ),
            "metadata": metadata_cleared,
        }

    nlu_result = state.get("nlu_result") or {}
    message_type = nlu_result.get("message_type") if nlu_result else None

    # [... rest of existing code ...]

    # User confirmed
    if confirmation_value is True:
        logger.info("User confirmed, proceeding to action")
        # ✅ Clear confirmation attempts on success
        metadata_cleared = metadata.copy()
        metadata_cleared.pop("_confirmation_attempts", None)
        return {
            "conversation_state": "ready_for_action",
            "last_response": "Great! Processing your request...",
            "metadata": metadata_cleared,
        }

    # User denied - wants to change something
    elif confirmation_value is False:
        logger.info("User denied confirmation, allowing modification")
        # ✅ Clear confirmation attempts on explicit denial
        metadata_cleared = metadata.copy()
        metadata_cleared.pop("_confirmation_attempts", None)
        return {
            "conversation_state": "understanding",
            "last_response": "What would you like to change?",
            "metadata": metadata_cleared,
        }

    # Confirmation value not extracted or unclear
    else:
        logger.warning(
            f"Confirmation value unclear: {confirmation_value}, asking again "
            f"(attempt {confirmation_attempts + 1}/{MAX_CONFIRMATION_ATTEMPTS})"
        )
        # ✅ Increment retry counter
        metadata_updated = metadata.copy()
        metadata_updated["_confirmation_attempts"] = confirmation_attempts + 1

        return {
            "conversation_state": "confirming",
            "last_response": "I didn't understand. Is this information correct? (yes/no)",
            "metadata": metadata_updated,
        }
```

**Explicación:**
- Track confirmation attempts in `metadata["_confirmation_attempts"]`
- Limit to 3 attempts before aborting
- Clear counter on success or explicit denial
- Increment counter when response is unclear
- Set conversation_state to "error" when limit exceeded
- Provide helpful error message to user

#### Paso 2: Add state transition cycle detector

**Archivo(s) a crear:** `src/soni/utils/cycle_detector.py`

**Código específico:**

```python
"""Cycle detector for preventing infinite state transition loops."""

import logging
from collections import deque
from typing import Any

logger = logging.getLogger(__name__)


class StateTransitionCycleDetector:
    """Detects cycles in state transitions to prevent infinite loops.

    Tracks recent state transitions and detects when the same cycle repeats.
    Example: understand → handle_confirmation → understand → handle_confirmation → ...
    """

    def __init__(self, max_history: int = 10, cycle_threshold: int = 3):
        """Initialize cycle detector.

        Args:
            max_history: Maximum number of transitions to track
            cycle_threshold: Number of times a cycle must repeat to trigger detection
        """
        self.max_history = max_history
        self.cycle_threshold = cycle_threshold
        self.transition_history: deque[tuple[str, str]] = deque(maxlen=max_history)

    def add_transition(self, from_node: str, to_node: str) -> bool:
        """Add a state transition and check for cycles.

        Args:
            from_node: Source node name
            to_node: Target node name

        Returns:
            True if a cycle is detected, False otherwise
        """
        transition = (from_node, to_node)
        self.transition_history.append(transition)

        # Check for cycles
        if len(self.transition_history) < 4:  # Need at least 2 transitions repeated
            return False

        # Look for repeating pattern
        # Example: [(A,B), (B,A), (A,B), (B,A)] is a cycle
        cycle_detected = self._detect_cycle()

        if cycle_detected:
            logger.error(
                f"State transition cycle detected: {list(self.transition_history)[-6:]}"
            )

        return cycle_detected

    def _detect_cycle(self) -> bool:
        """Detect if recent transitions form a cycle."""
        history = list(self.transition_history)

        # Check for simple 2-step cycle: A→B→A→B→A→B
        if len(history) >= 6:
            # Get last 6 transitions
            last_6 = history[-6:]
            # Check if they form pattern: [A,B] * 3
            if (last_6[0] == last_6[2] == last_6[4] and
                last_6[1] == last_6[3] == last_6[5] and
                last_6[0] != last_6[1]):
                return True

        # Check for 3-step cycle: A→B→C→A→B→C
        if len(history) >= 9:
            last_9 = history[-9:]
            if (last_9[0] == last_9[3] == last_9[6] and
                last_9[1] == last_9[4] == last_9[7] and
                last_9[2] == last_9[5] == last_9[8]):
                return True

        return False

    def reset(self) -> None:
        """Reset the transition history."""
        self.transition_history.clear()
```

**Explicación:**
- Tracks recent node transitions
- Detects repeating patterns (cycles)
- Currently detects 2-step and 3-step cycles
- Can be extended to detect longer cycles
- Provides clear error logging when cycle detected

#### Paso 3: Integrate cycle detector in graph execution

**Archivo(s) a modificar:** `src/soni/runtime/runtime.py`

**Código específico:**

```python
from soni.utils.cycle_detector import StateTransitionCycleDetector


class RuntimeLoop:
    """Main runtime loop for Soni dialogue system."""

    def __init__(self, config_path: Path | str):
        # ... existing initialization ...

        # ✅ ADD cycle detector
        self.cycle_detector = StateTransitionCycleDetector(
            max_history=10,
            cycle_threshold=3
        )

    async def _execute_graph(
        self,
        state: dict[str, Any],
        user_id: str,
    ) -> dict[str, Any]:
        """Execute LangGraph with the given state.

        Includes cycle detection to prevent infinite loops.
        """
        # ✅ Reset cycle detector at start of each message
        self.cycle_detector.reset()

        # ... existing graph execution code ...

        # ✅ ADD transition tracking (if possible with LangGraph callbacks)
        # This may require LangGraph callback hooks or custom middleware
        # For now, add logging to track transitions

        try:
            result_raw = await self.graph.ainvoke(
                state,
                config=config,
                stream_mode="values",
            )
        except Exception as e:
            # ✅ Check if it's a recursion error
            if "recursion limit" in str(e).lower():
                logger.error(
                    f"LangGraph recursion limit exceeded. "
                    f"Recent transitions: {list(self.cycle_detector.transition_history)}"
                )
            raise

        return result_raw
```

**Explicación:**
- Add cycle detector instance to RuntimeLoop
- Reset at start of each message
- Track transitions (may need LangGraph callbacks)
- Log transition history when recursion limit is hit
- Helps debug future infinite loop issues

#### Paso 4: Add max retries to other potentially cyclic nodes

**Archivos a modificar:**
- `src/soni/dm/nodes/handle_correction.py`
- `src/soni/dm/nodes/handle_modification.py`
- `src/soni/dm/nodes/collect_next_slot.py`

**Pattern to apply:**

```python
async def handle_[operation]_node(state, runtime) -> dict:
    # ✅ ADD at start of node
    metadata = state.get("metadata", {})
    retry_count = metadata.get("_[operation]_retries", 0)

    MAX_RETRIES = 3
    if retry_count >= MAX_RETRIES:
        logger.error(f"Max retries for [operation] exceeded")
        metadata_cleared = metadata.copy()
        metadata_cleared.pop("_[operation]_retries", None)
        return {
            "conversation_state": "error",
            "last_response": "I'm having trouble processing this. Let's start over.",
            "metadata": metadata_cleared,
        }

    # ... existing node logic ...

    # ✅ Clear counter on success
    if success:
        metadata_cleared = metadata.copy()
        metadata_cleared.pop("_[operation]_retries", None)
        return {..., "metadata": metadata_cleared}

    # ✅ Increment counter on retry
    else:
        metadata_updated = metadata.copy()
        metadata_updated["_[operation]_retries"] = retry_count + 1
        return {..., "metadata": metadata_updated}
```

**Nodes to protect:**
- `handle_confirmation` (already done in Step 1)
- `handle_correction` - in case correction extraction fails repeatedly
- `handle_modification` - in case modification handling loops
- `collect_next_slot` - in case slot collection gets stuck

### Tests Requeridos

**Archivo de tests:** `tests/unit/test_defensive_checks.py`

**Tests específicos a implementar:**

```python
import pytest
from soni.dm.nodes.handle_confirmation import handle_confirmation_node
from soni.core.types import DialogueState
from soni.utils.cycle_detector import StateTransitionCycleDetector


# Test 1: Confirmation retries are counted
@pytest.mark.asyncio
async def test_confirmation_retry_counter():
    """Test that confirmation attempts are tracked"""
    # Arrange
    state = {
        "nlu_result": {
            "message_type": "confirmation",
            "confirmation_value": None,  # Unclear
        },
        "metadata": {},
    }
    runtime = MockRuntime()

    # Act
    result = await handle_confirmation_node(state, runtime)

    # Assert
    assert result["metadata"]["_confirmation_attempts"] == 1
    assert result["conversation_state"] == "confirming"


# Test 2: Max confirmation attempts triggers error state
@pytest.mark.asyncio
async def test_confirmation_max_retries():
    """Test that exceeding max attempts returns error state"""
    # Arrange
    state = {
        "nlu_result": {
            "message_type": "confirmation",
            "confirmation_value": None,
        },
        "metadata": {"_confirmation_attempts": 3},  # Already at max
    }
    runtime = MockRuntime()

    # Act
    result = await handle_confirmation_node(state, runtime)

    # Assert
    assert result["conversation_state"] == "error"
    assert "_confirmation_attempts" not in result["metadata"]
    assert "trouble understanding" in result["last_response"].lower()


# Test 3: Successful confirmation clears retry counter
@pytest.mark.asyncio
async def test_confirmation_success_clears_counter():
    """Test that successful confirmation clears the retry counter"""
    # Arrange
    state = {
        "nlu_result": {
            "message_type": "confirmation",
            "confirmation_value": True,  # Confirmed
        },
        "metadata": {"_confirmation_attempts": 2},  # Had previous attempts
    }
    runtime = MockRuntime()

    # Act
    result = await handle_confirmation_node(state, runtime)

    # Assert
    assert result["conversation_state"] == "ready_for_action"
    assert "_confirmation_attempts" not in result["metadata"]


# Test 4: Cycle detector detects 2-step cycle
def test_cycle_detector_2_step():
    """Test that cycle detector identifies A→B→A→B pattern"""
    detector = StateTransitionCycleDetector()

    # Add transitions
    assert not detector.add_transition("understand", "handle_confirmation")
    assert not detector.add_transition("handle_confirmation", "understand")
    assert not detector.add_transition("understand", "handle_confirmation")
    assert not detector.add_transition("handle_confirmation", "understand")
    assert not detector.add_transition("understand", "handle_confirmation")
    # 6th transition completes the cycle detection
    assert detector.add_transition("handle_confirmation", "understand")


# Test 5: Cycle detector ignores non-cycles
def test_cycle_detector_no_false_positives():
    """Test that cycle detector doesn't trigger on normal flow"""
    detector = StateTransitionCycleDetector()

    # Normal flow: understand → validate → collect → understand
    assert not detector.add_transition("understand", "validate_slot")
    assert not detector.add_transition("validate_slot", "collect_next_slot")
    assert not detector.add_transition("collect_next_slot", "understand")
    assert not detector.add_transition("understand", "validate_slot")


# Test 6: Cycle detector can be reset
def test_cycle_detector_reset():
    """Test that resetting clears history"""
    detector = StateTransitionCycleDetector()

    # Add some transitions
    detector.add_transition("A", "B")
    detector.add_transition("B", "A")
    assert len(detector.transition_history) == 2

    # Reset
    detector.reset()
    assert len(detector.transition_history) == 0
```

### Criterios de Éxito

- [ ] handle_confirmation_node limits retries to 3 attempts
- [ ] Max retries trigger error state with helpful message
- [ ] Retry counter is cleared on success or explicit denial
- [ ] Retry counter is incremented when response is unclear
- [ ] StateTransitionCycleDetector class implemented and tested
- [ ] Cycle detector integrated in RuntimeLoop
- [ ] Defensive checks added to other potentially cyclic nodes
- [ ] All unit tests pass (6+ test cases)
- [ ] Integration test confirms circuit breakers work
- [ ] No regressions in existing tests

### Validación Manual

**Comandos para validar:**

```bash
# Run defensive checks tests
uv run pytest tests/unit/test_defensive_checks.py -v

# Run scenario that would previously infinite loop
# With defensive checks, should error gracefully after 3 attempts
uv run python scripts/debug_scenarios.py 1

# Run all tests
uv run pytest tests/ -v

# Check type hints and linting
uv run mypy src/soni/dm/nodes/handle_confirmation.py
uv run mypy src/soni/utils/cycle_detector.py
uv run ruff check src/soni/
```

**Resultado esperado:**
- If confirmation_value extraction fails, max 3 retry attempts before error
- Error message is user-friendly: "I'm having trouble understanding..."
- Cycle detector logs warning when patterns detected
- System doesn't hit LangGraph recursion limit (25 iterations)

### Referencias

- Analysis: `docs/analysis/ANALISIS_ERROR_CONFIRMACION.md`
- handle_confirmation_node: `src/soni/dm/nodes/handle_confirmation.py`
- RuntimeLoop: `src/soni/runtime/runtime.py`
- LangGraph recursion limit: https://python.langchain.com/docs/langgraph/troubleshooting/errors/GRAPH_RECURSION_LIMIT

### Notas Adicionales

**Why defensive checks are important:**

Even with correct implementation, bugs can be introduced:
- New features may inadvertently create cycles
- Edge cases may not be covered in tests
- Third-party dependencies (LLM, DSPy) may behave unexpectedly

Defensive checks provide:
1. **Safety net**: Prevent infinite loops from crashing the system
2. **Better UX**: Graceful error messages instead of timeouts
3. **Debugging aid**: Log transition history for diagnosis
4. **Fail-safe**: System recovers instead of hanging

**Circuit breaker pattern:**

The retry counter implements a circuit breaker:
- **Closed**: Normal operation, retries allowed
- **Open**: Max retries exceeded, operation fails fast
- **Reset**: Success clears counter, returns to closed state

This prevents cascading failures and resource exhaustion.

**Metadata convention:**

Use `_<operation>_retries` or `_<operation>_attempts` for internal counters:
- `_confirmation_attempts`
- `_correction_retries`
- `_validation_attempts`

Prefix with `_` to indicate internal/temporary metadata.

**Future enhancements:**

- Configurable max retries per node type
- Exponential backoff between retries
- Detect and break longer cycles (4+ steps)
- Global recursion counter across all nodes
- Telemetry/metrics for retry rates
