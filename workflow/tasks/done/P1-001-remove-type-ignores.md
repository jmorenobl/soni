## Task: P1-001 - Remove type: ignore Comments

**Task ID:** P1-001
**Milestone:** 1.1 - Type Safety Restoration (Phase 2)
**Dependencies:** None
**Estimated Duration:** 3 hours

### Objective

Remove all `# type: ignore` comments from source code by fixing the underlying type issues properly, following SOLID principles.

### Context

**Current `type: ignore` locations:**

1. **`runtime/hydrator.py:45`** - Partial TypedDict
   ```python
   input_payload: DialogueState = {  # type: ignore[typeddict-item]
       "user_message": message,
       ...
   }
   ```

2. **`runtime/loop.py:73`** - Setter with incorrect type
   ```python
   self._components.flow_manager = value  # type: ignore
   ```

3. **`runtime/loop.py:85`** - Setter with incorrect type
   ```python
   self._components.du = value  # type: ignore
   ```

**Root cause of setter issues:**
- Setters accept `| None` but `RuntimeComponents` fields don't accept `None`
- These setters are used in **25+ test files** to inject mocks

**Best solution (SOLID-compliant):**
- **Remove setters entirely** - they violate DIP (Dependency Inversion Principle)
- **Use constructor injection** - `RuntimeLoop` already accepts `du` in constructor
- **Refactor tests** to use constructor injection

### Deliverables

- [ ] Zero `# type: ignore` in source code
- [ ] Setters removed from `RuntimeLoop`
- [ ] All tests refactored to use constructor injection
- [ ] Mypy passes in strict mode
- [ ] All tests pass

---

### Implementation Details

#### Part 1: Fix hydrator.py - Partial TypedDict

**File:** `src/soni/runtime/hydrator.py`

**Problem:** Creating partial `DialogueState` but TypedDict requires all fields.

**Current code (lines 42-50):**
```python
else:
    # Incremental update for existing conversation
    input_payload: DialogueState = {  # type: ignore[typeddict-item]
        "user_message": message,
        "messages": [HumanMessage(content=message)],
        "turn_count": int(current_state.get("turn_count", 0)) + 1,
    }
    return input_payload
```

**Fixed code:**
```python
else:
    # Incremental update for existing conversation
    # LangGraph merges partial updates with existing state via reducers
    input_payload: dict[str, Any] = {
        "user_message": message,
        "messages": [HumanMessage(content=message)],
        "turn_count": int(current_state.get("turn_count", 0)) + 1,
    }
    # Cast is safe: LangGraph will merge with existing DialogueState
    return cast(DialogueState, input_payload)
```

**Add imports:**
```python
from typing import Any, cast
```

---

#### Part 2: Remove Setters from RuntimeLoop

**File:** `src/soni/runtime/loop.py`

**Remove entirely (lines 70-74):**
```python
@flow_manager.setter
def flow_manager(self, value: FlowManager | None) -> None:
    if self._components:
        self._components.flow_manager = value  # type: ignore
```

**Remove entirely (lines 82-86):**
```python
@du.setter
def du(self, value: DUProtocol | None) -> None:
    if self._components:
        self._components.du = value  # type: ignore
```

**Why remove instead of fix:**
- Setters violate DIP - allow changing dependencies after construction
- Constructor already supports `du` injection
- Tests should use constructor injection (cleaner pattern)

---

#### Part 3: Refactor Tests to Use Constructor Injection

**Pattern to find:**
```python
runtime = RuntimeLoop(config)
runtime.du = mock_du  # ❌ Old pattern
```

**Replace with:**
```python
runtime = RuntimeLoop(config, du=mock_du)  # ✅ Constructor injection
```

**Files to update (found via grep):**

| File | Lines |
|------|-------|
| `examples/banking/scripts/base.py` | 604, 609 |
| `tests/e2e/test_e2e.py` | 70 |
| `tests/integration/test_runtime_flow_execution.py` | 42, 100, 110 |
| `tests/integration/test_scenarios.py` | 43 |
| `tests/unit/runtime/test_loop.py` | 43, 67 |
| `tests/unit/dm/nodes/test_understand_node_patterns.py` | 32 |
| `tests/unit/dm/test_understand_node_immutability.py` | 85 |

**For `flow_manager` assignments in tests:**
These are on `RuntimeContext`, not `RuntimeLoop`. They should be fixed similarly by using the context constructor instead of post-construction assignment.

**Search command:**
```bash
# Find all du setter usage
grep -rn "\.du\s*=" tests/ examples/

# Find all flow_manager setter usage on RuntimeLoop
grep -rn "runtime.*\.flow_manager\s*=" tests/ examples/
```

---

#### Part 4: Handle banking/scripts/base.py Special Case

**File:** `examples/banking/scripts/base.py`

This file has a context manager pattern:
```python
self._runtime.du = mock_du
try:
    ...
finally:
    self._runtime.du = original_du
```

**Solution:** Create a new `RuntimeLoop` with the mock instead of mutating:
```python
# Store original runtime
original_runtime = self._runtime

# Create new runtime with mock
self._runtime = RuntimeLoop(
    self._runtime.config,
    du=mock_du,
    checkpointer=...,  # Copy relevant settings
)
try:
    ...
finally:
    self._runtime = original_runtime
```

Or better: Create a helper method `with_mock_du()` that handles this.

---

### TDD Cycle

#### Red Phase: Write Failing Tests

**Test file:** `tests/unit/runtime/test_type_safety.py`

```python
"""Tests for type safety in runtime components."""

import inspect
import subprocess
import sys
from typing import Any, cast
from unittest.mock import MagicMock

import pytest


class TestNoTypeIgnore:
    """Verify no type: ignore comments in source."""

    def test_no_type_ignore_in_hydrator(self) -> None:
        """Verify hydrator.py has no type: ignore."""
        import soni.runtime.hydrator as module
        source = inspect.getsource(module)
        assert "type: ignore" not in source

    def test_no_type_ignore_in_loop(self) -> None:
        """Verify loop.py has no type: ignore."""
        import soni.runtime.loop as module
        source = inspect.getsource(module)
        assert "type: ignore" not in source


class TestSettersRemoved:
    """Verify setters have been removed."""

    def test_runtime_loop_has_no_du_setter(self) -> None:
        """Verify RuntimeLoop.du is read-only."""
        from soni.runtime.loop import RuntimeLoop

        config = MagicMock()
        runtime = RuntimeLoop(config)

        with pytest.raises(AttributeError):
            runtime.du = MagicMock()  # type: ignore[misc]

    def test_runtime_loop_has_no_flow_manager_setter(self) -> None:
        """Verify RuntimeLoop.flow_manager is read-only."""
        from soni.runtime.loop import RuntimeLoop

        config = MagicMock()
        runtime = RuntimeLoop(config)

        with pytest.raises(AttributeError):
            runtime.flow_manager = MagicMock()  # type: ignore[misc]


class TestConstructorInjection:
    """Verify constructor injection works."""

    def test_du_can_be_injected_via_constructor(self) -> None:
        """Verify du can be passed to constructor."""
        from soni.runtime.loop import RuntimeLoop

        config = MagicMock()
        config.flows = {}
        mock_du = MagicMock()

        runtime = RuntimeLoop(config, du=mock_du)

        # After initialize, the injected du should be used
        # (This test may need adjustment based on actual behavior)
        assert runtime._initializer._du is mock_du


class TestHydratorTypeSafety:
    """Tests for StateHydrator type correctness."""

    def test_prepare_input_returns_valid_type(self) -> None:
        """Test prepare_input return type."""
        from soni.runtime.hydrator import StateHydrator

        hydrator = StateHydrator()

        # New conversation
        result = hydrator.prepare_input("Hello", None)
        assert "user_message" in result
        assert "flow_stack" in result

        # Existing conversation
        result2 = hydrator.prepare_input("Hi again", {"turn_count": 1})
        assert result2["turn_count"] == 2


class TestMypyCompliance:
    """Verify mypy passes on modified files."""

    def test_mypy_passes_on_hydrator(self) -> None:
        """Run mypy on hydrator.py."""
        result = subprocess.run(
            [sys.executable, "-m", "mypy",
             "src/soni/runtime/hydrator.py", "--strict"],
            capture_output=True,
            text=True,
        )
        assert result.returncode == 0, f"mypy failed:\n{result.stdout}\n{result.stderr}"

    def test_mypy_passes_on_loop(self) -> None:
        """Run mypy on loop.py."""
        result = subprocess.run(
            [sys.executable, "-m", "mypy",
             "src/soni/runtime/loop.py", "--strict"],
            capture_output=True,
            text=True,
        )
        assert result.returncode == 0, f"mypy failed:\n{result.stdout}\n{result.stderr}"
```

**Run tests (should fail):**
```bash
uv run pytest tests/unit/runtime/test_type_safety.py -v
```

#### Green Phase: Implement Changes

1. Fix `hydrator.py` (Part 1)
2. Remove setters from `loop.py` (Part 2)
3. Refactor all tests (Part 3)
4. Handle special cases (Part 4)

**Verify:**
```bash
uv run pytest tests/ -v
uv run mypy src/soni --strict
```

---

### Success Criteria

- [ ] `grep "type: ignore" src/soni` returns zero results
- [ ] `RuntimeLoop` has no `du` or `flow_manager` setters
- [ ] All tests use constructor injection pattern
- [ ] `uv run mypy src/soni --strict` passes
- [ ] All tests pass: `uv run pytest tests/ -v`

### Manual Validation

```bash
# 1. No type: ignore in source
grep -r "type: ignore" src/soni/

# 2. Verify setters are removed
python -c "
from soni.runtime.loop import RuntimeLoop
from unittest.mock import MagicMock
r = RuntimeLoop(MagicMock())
try:
    r.du = MagicMock()
    print('FAIL: setter still exists')
except AttributeError:
    print('OK: setter removed')
"

# 3. Verify constructor injection works
python -c "
from soni.runtime.loop import RuntimeLoop
from unittest.mock import MagicMock
mock_du = MagicMock()
r = RuntimeLoop(MagicMock(), du=mock_du)
print('OK: constructor injection works')
"

# 4. Run full test suite
uv run pytest tests/ -v
```

### References

- `src/soni/runtime/hydrator.py` - TypedDict fix
- `src/soni/runtime/loop.py` - Remove setters
- [Dependency Inversion Principle](https://en.wikipedia.org/wiki/Dependency_inversion_principle)
- [Python TypedDict](https://docs.python.org/3/library/typing.html#typing.TypedDict)

### Notes

**Why constructor injection is better:**
1. **Immutable after construction** - No surprise mutations
2. **Clear dependencies** - All deps visible in constructor signature
3. **Testable by design** - Inject mocks at construction time
4. **Type-safe** - No need for `type: ignore` hacks

**Migration effort:**
- ~25 files need test changes
- Most are simple search/replace
- One complex case in `banking/scripts/base.py`

**Future consideration:**
If `flow_manager` injection is needed, add it to constructor:
```python
def __init__(
    self,
    config: SoniConfig,
    checkpointer: BaseCheckpointSaver | None = None,
    registry: ActionRegistry | None = None,
    du: DUProtocol | None = None,
    flow_manager: FlowManager | None = None,  # Add this
):
```
