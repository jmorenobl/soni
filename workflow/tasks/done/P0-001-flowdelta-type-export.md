## Task: P0-001 - Export FlowDelta to core/types.py for Type Safety

**Task ID:** P0-001
**Milestone:** 1.1 - Type Safety Restoration
**Dependencies:** None
**Estimated Duration:** 1.5 hours

### Objective

Move `FlowDelta` class from `flow/manager.py` to `core/types.py` and update all Protocols to use concrete types instead of `Any`, restoring full type safety.

### Context

Currently `FlowDelta` is defined in `flow/manager.py` but is used by multiple Protocols in `core/types.py`. The Protocols use `Any` as return type because importing `FlowDelta` from `manager.py` would create a circular dependency.

**Current problem in `core/types.py`:**
```python
def set_slot(...) -> Any | None:  # ❌ Should be FlowDelta | None
def push_flow(...) -> tuple[str, Any]:  # ❌ Should be tuple[str, FlowDelta]
def pop_flow(...) -> tuple[FlowContext, Any]:  # ❌ Should be tuple[FlowContext, FlowDelta]
def advance_step(...) -> Any | None:  # ❌ Should be FlowDelta | None
def handle_intent_change(...) -> Any | None:  # ❌ Should be FlowDelta | None
```

**Impact:**
- Loss of IDE autocompletion for FlowDelta fields
- Type checker cannot validate correct delta usage
- Violation of explicit types principle

**SOLID principles applied:**
- **ISP**: Protocols should have concrete types so consumers know what to expect
- **DIP**: Abstractions (types.py) should not depend on implementations (manager.py)

### Deliverables

- [ ] `FlowDelta` moved to `core/types.py`
- [ ] All Protocols updated with concrete types
- [ ] Imports updated in `flow/manager.py`
- [ ] Mypy passes without errors
- [ ] All existing tests pass

---

### Implementation Details

#### Step 1: Add FlowDelta to core/types.py

**File:** `src/soni/core/types.py`

**Location:** Insert after `FlowContext` (line 32), before `DialogueState` (line 35)

```python
# After FlowContext class (line 32), add:

@dataclass
class FlowDelta:
    """State delta returned by FlowManager mutation methods.

    Callers must merge these into their return dict for LangGraph to track.
    This follows the immutable state pattern where mutations return deltas
    instead of modifying state in-place.

    Attributes:
        flow_stack: Updated flow stack if changed, None if unchanged.
        flow_slots: Updated slot mapping if changed, None if unchanged.
    """

    flow_stack: list[FlowContext] | None = None
    flow_slots: dict[str, dict[str, Any]] | None = None
```

**Note:** `dataclass` is already imported at line 11.

#### Step 2: Update Protocols with concrete types

**File:** `src/soni/core/types.py`

**SlotProvider (around line 88-92):**
```python
def set_slot(
    self, state: DialogueState, slot_name: str, value: Any
) -> FlowDelta | None:  # ✅ Concrete type
    """Set a slot value in the active flow context."""
    ...
```

**FlowStackProvider (around lines 110-133):**
```python
def push_flow(
    self,
    state: DialogueState,
    flow_name: str,
    inputs: dict[str, Any] | None = None,
) -> tuple[str, FlowDelta]:  # ✅ Concrete type
    """Push a new flow onto the stack."""
    ...

def pop_flow(
    self,
    state: DialogueState,
    result: FlowContextState = FlowContextState.COMPLETED,
) -> tuple[FlowContext, FlowDelta]:  # ✅ Concrete type
    """Pop the top flow from the stack."""
    ...

def handle_intent_change(
    self,
    state: DialogueState,
    new_flow: str,
) -> FlowDelta | None:  # ✅ Concrete type
    """Handle intent switch (push new flow)."""
    ...
```

**FlowContextProvider (around line 147):**
```python
def advance_step(self, state: DialogueState) -> FlowDelta | None:  # ✅ Concrete type
    """Advance to next step in current flow."""
    ...
```

#### Step 3: Update imports in flow/manager.py

**File:** `src/soni/flow/manager.py`

**Remove:**
```python
from dataclasses import dataclass

@dataclass
class FlowDelta:
    """State delta returned by FlowManager mutation methods..."""
    flow_stack: list[FlowContext] | None = None
    flow_slots: dict[str, dict[str, Any]] | None = None
```

**Update imports to:**
```python
from soni.core.types import DialogueState, FlowContext, FlowContextState, FlowDelta
```

**Note:** Remove `from dataclasses import dataclass` line since it's no longer used in manager.py.

#### Step 4: Verify all imports of FlowDelta

**Commands:**
```bash
rg "from soni.flow.manager import.*FlowDelta" src/
rg "FlowDelta" src/ --type py
```

**Update any found imports to:**
```python
from soni.core.types import FlowDelta
```

**Keep backward-compatible re-export in manager.py (optional):**
```python
# At the end of flow/manager.py, for backwards compatibility:
__all__ = ["FlowManager", "FlowDelta", "merge_delta"]
```

This allows existing code using `from soni.flow.manager import FlowDelta` to continue working.

---

### TDD Cycle (MANDATORY)

#### Red Phase: Write Failing Tests

**Test file:** `tests/unit/core/test_types_flowdelta.py`

```python
"""Tests for FlowDelta type export and Protocol type safety."""

from dataclasses import fields
from typing import get_type_hints

import pytest

from soni.core.types import (
    DialogueState,
    FlowContext,
    FlowDelta,
    FlowStackProvider,
    FlowContextProvider,
    SlotProvider,
)


class TestFlowDeltaExport:
    """Tests verifying FlowDelta is properly exported from core/types."""

    def test_flowdelta_importable_from_core_types(self) -> None:
        """Test that FlowDelta can be imported from core/types."""
        from soni.core.types import FlowDelta

        assert FlowDelta is not None

    def test_flowdelta_is_dataclass(self) -> None:
        """Test that FlowDelta is a dataclass with expected fields."""
        field_names = {f.name for f in fields(FlowDelta)}
        assert "flow_stack" in field_names
        assert "flow_slots" in field_names

    def test_flowdelta_fields_are_optional(self) -> None:
        """Test that FlowDelta can be created with no arguments."""
        delta = FlowDelta()
        assert delta.flow_stack is None
        assert delta.flow_slots is None

    def test_flowdelta_accepts_flow_stack(self) -> None:
        """Test FlowDelta with flow_stack argument."""
        stack: list[FlowContext] = []
        delta = FlowDelta(flow_stack=stack)
        assert delta.flow_stack == stack

    def test_flowdelta_accepts_flow_slots(self) -> None:
        """Test FlowDelta with flow_slots argument."""
        slots: dict[str, dict[str, object]] = {"flow_1": {"name": "test"}}
        delta = FlowDelta(flow_slots=slots)
        assert delta.flow_slots == slots


class TestProtocolReturnTypes:
    """Tests verifying Protocols use FlowDelta instead of Any."""

    def test_slot_provider_set_slot_returns_flowdelta(self) -> None:
        """Test SlotProvider.set_slot returns FlowDelta | None, not Any."""
        hints = get_type_hints(SlotProvider.set_slot)
        return_type = hints.get("return")

        assert return_type is not None
        # Check it contains FlowDelta (handles Union types)
        assert "FlowDelta" in str(return_type) or return_type == FlowDelta | None

    def test_flow_stack_provider_push_flow_returns_flowdelta(self) -> None:
        """Test FlowStackProvider.push_flow returns tuple[str, FlowDelta]."""
        hints = get_type_hints(FlowStackProvider.push_flow)
        return_type = hints.get("return")

        assert return_type is not None
        assert "FlowDelta" in str(return_type)

    def test_flow_stack_provider_pop_flow_returns_flowdelta(self) -> None:
        """Test FlowStackProvider.pop_flow returns tuple[FlowContext, FlowDelta]."""
        hints = get_type_hints(FlowStackProvider.pop_flow)
        return_type = hints.get("return")

        assert return_type is not None
        assert "FlowDelta" in str(return_type)

    def test_flow_stack_provider_handle_intent_change_returns_flowdelta(self) -> None:
        """Test FlowStackProvider.handle_intent_change returns FlowDelta | None."""
        hints = get_type_hints(FlowStackProvider.handle_intent_change)
        return_type = hints.get("return")

        assert return_type is not None
        assert "FlowDelta" in str(return_type) or return_type == FlowDelta | None

    def test_flow_context_provider_advance_step_returns_flowdelta(self) -> None:
        """Test FlowContextProvider.advance_step returns FlowDelta | None."""
        hints = get_type_hints(FlowContextProvider.advance_step)
        return_type = hints.get("return")

        assert return_type is not None
        assert "FlowDelta" in str(return_type) or return_type == FlowDelta | None


class TestFlowManagerImplementsProtocols:
    """Tests verifying FlowManager still implements protocols correctly."""

    def test_flow_manager_is_slot_provider(self) -> None:
        """Test FlowManager implements SlotProvider protocol."""
        from soni.flow.manager import FlowManager

        assert isinstance(FlowManager(), SlotProvider)

    def test_flow_manager_is_flow_stack_provider(self) -> None:
        """Test FlowManager implements FlowStackProvider protocol."""
        from soni.flow.manager import FlowManager

        assert isinstance(FlowManager(), FlowStackProvider)

    def test_flow_manager_is_flow_context_provider(self) -> None:
        """Test FlowManager implements FlowContextProvider protocol."""
        from soni.flow.manager import FlowManager

        assert isinstance(FlowManager(), FlowContextProvider)


class TestBackwardsCompatibility:
    """Tests for backwards compatibility of imports."""

    def test_flowdelta_importable_from_manager(self) -> None:
        """Test FlowDelta can still be imported from flow.manager."""
        from soni.flow.manager import FlowDelta

        assert FlowDelta is not None

    def test_merge_delta_still_works(self) -> None:
        """Test merge_delta function works with FlowDelta."""
        from soni.flow.manager import FlowDelta, merge_delta

        updates: dict[str, object] = {}
        delta = FlowDelta(flow_slots={"flow_1": {"key": "value"}})
        merge_delta(updates, delta)

        assert "flow_slots" in updates
```

**Run tests (should fail):**
```bash
uv run pytest tests/unit/core/test_types_flowdelta.py -v
# Expected: FAILED (FlowDelta not in core/types yet)
```

**Commit:**
```bash
git add tests/
git commit -m "test: add failing tests for FlowDelta type export (P0-001)"
```

#### Green Phase: Make Tests Pass

**Implement the changes from "Implementation Details" section.**

**Verify tests pass:**
```bash
uv run pytest tests/unit/core/test_types_flowdelta.py -v
# Expected: PASSED ✅
```

**Commit:**
```bash
git add src/ tests/
git commit -m "feat: export FlowDelta to core/types.py for type safety (P0-001)"
```

---

### Success Criteria

- [ ] `FlowDelta` is importable from `soni.core.types`
- [ ] No Protocol uses `Any` where it should use `FlowDelta`
- [ ] `mypy src/soni` passes without FlowDelta-related errors
- [ ] IDE autocomplete works for FlowDelta fields
- [ ] All tests pass: `uv run pytest tests/ -v`
- [ ] Backwards compatibility: `from soni.flow.manager import FlowDelta` still works

### Manual Validation

```bash
# 1. Verify FlowDelta is importable from core/types
uv run python -c "from soni.core.types import FlowDelta; print(FlowDelta)"

# 2. Verify backwards compatibility
uv run python -c "from soni.flow.manager import FlowDelta; print(FlowDelta)"

# 3. Verify no Any in Protocol return types
uv run rg "-> Any" src/soni/core/types.py

# 4. Type check
uv run mypy src/soni

# 5. Full test suite
uv run pytest tests/ -v
```

### References

- `src/soni/core/types.py` - Destination for FlowDelta (lines 32-35 insertion point)
- `src/soni/flow/manager.py` - Current FlowDelta location (lines 19-27)
- [LangGraph State Patterns](https://langchain-ai.github.io/langgraph/concepts/low_level/)

### Notes

**Definition order in `core/types.py` is important:**
1. `FlowContext` (TypedDict) - line 23
2. `FlowDelta` (dataclass using FlowContext) - NEW, insert after line 32
3. `DialogueState` (TypedDict) - line 35
4. Protocols (using FlowDelta) - line 80+

**merge_delta function:**
The `merge_delta` helper function stays in `flow/manager.py` since it's an implementation helper, not a type. It uses `FlowDelta` which it will now import from `core/types.py`.
