# Technical Debt Analysis - Soni Framework

**Date**: 2025-12-24
**Status**: Pending Review
**Scope**: `src/soni/` codebase optimization without adding/removing functionality

---

## Executive Summary

This analysis identifies technical debt and optimization opportunities in the Soni codebase. The goal is to improve code quality, readability, and maintainability without changing functionality.

**Codebase Stats**:
- Total lines: ~9,300
- Largest files: `du/metrics.py` (374 LOC), `dataset/domains/flight_booking.py` (381 LOC)
- Complex nodes: `dm/nodes/understand.py` (264 LOC), `dm/nodes/orchestrator.py` (231 LOC)

---

## 🔴 High Priority Issues

### 1. `understand_node` Violates SRP (264 lines)

**File**: [dm/nodes/understand.py](file:///Users/jorge/Projects/Playground/soni/src/soni/dm/nodes/understand.py)

**Problem**: The node does too many things:
- Build dialogue context (FlowInfo, CommandInfo)
- Convert message history formats
- Call NLU Pass 1 (SoniDU)
- Call NLU Pass 2 (SlotExtractor)
- Process StartFlow/CancelFlow commands
- Update flow_stack

**Impact**: Hard to test, modify, and debug. Changes in one area risk breaking others.

**Recommendation**: Extract into focused classes:

```python
# Proposed structure
dm/nodes/
├── understand.py          # Thin orchestrator (~50 LOC)
├── context_builder.py     # DialogueContextBuilder class
├── history_converter.py   # HistoryConverter class
└── flow_command_processor.py  # Process StartFlow/CancelFlow
```

**Estimated Effort**: 2-3 hours

---

### 2. Orchestrator Helper Functions Scattered

**File**: [dm/nodes/orchestrator.py](file:///Users/jorge/Projects/Playground/soni/src/soni/dm/nodes/orchestrator.py)

**Problem**: Contains 5 helper functions (`_merge_state`, `_build_subgraph_state`, `_transform_result`, `_merge_outputs`, `_build_merged_return`) mixed with the main node logic.

**Impact**: File is 232 lines. Helpers are not reusable. Testing requires importing the whole file.

**Recommendation**: Extract to `dm/orchestrator/state_utils.py`:

```python
# dm/orchestrator/state_utils.py
def merge_state(base: dict, delta: dict) -> dict: ...
def build_subgraph_state(state: dict) -> dict: ...
def transform_result(result: dict) -> dict: ...
def merge_outputs(target: dict, source: dict) -> None: ...
def build_merged_return(updates: dict, final_output: dict, pending_task: Any) -> dict: ...
```

**Estimated Effort**: 1-2 hours

---

### 3. Excessive `cast()` Usage (25+ instances)

**Problem**: Many `cast()` calls are redundant or indicate type system issues:

| File | Line | Issue |
|------|------|-------|
| `du/base.py` | 38, 43, 47, 51 | Redundant casts (mypy confirms) |
| `compiler/subgraph.py` | 118, 124 | `cast(str, END)` - END is already str |
| `dm/nodes/orchestrator.py` | 59, 68, 97, 113 | Working with dicts copied from TypedDict |
| `dm/nodes/understand.py` | 123, 124, 179, 183, 189, 198 | Same issue |

**Impact**: Code noise, potential type safety issues being masked.

**Recommendation**:
1. Remove mypy-confirmed redundant casts
2. For dict copies from TypedDict, create proper working state type
3. Consider using `TypedDict(total=False)` for optional fields

**Estimated Effort**: 1 hour

---

### 4. CLI `run_chat` Function Too Complex

**File**: [cli/commands/chat.py](file:///Users/jorge/Projects/Playground/soni/src/soni/cli/commands/chat.py)

**Problems** (from ruff):
```
C901 `run_chat` is too complex (16 > 10)
PLR0913 Too many arguments in function definition (6 > 5)
PLR0915 Too many statements (73 > 50)
```

**Impact**: Hard to maintain, test, and extend.

**Recommendation**: Extract into a `ChatRunner` class:

```python
class ChatRunner:
    def __init__(self, config_path: Path, module: str | None, ...): ...
    def setup(self) -> None: ...
    def run_loop(self) -> None: ...
    def handle_input(self, user_input: str) -> str: ...
    def cleanup(self) -> None: ...
```

**Estimated Effort**: 2 hours

---

## 🟡 Medium Priority Issues

### 5. Duplicate Slot Merge Logic

**Problem**: The same merge pattern for `flow_slots` appears in 4+ locations:

| File | Function/Location |
|------|-------------------|
| [core/types.py](file:///Users/jorge/Projects/Playground/soni/src/soni/core/types.py) | `_merge_flow_slots()` reducer |
| [dm/nodes/orchestrator.py](file:///Users/jorge/Projects/Playground/soni/src/soni/dm/nodes/orchestrator.py) | `_merge_outputs()` |
| [dm/orchestrator/command_processor.py](file:///Users/jorge/Projects/Playground/soni/src/soni/dm/orchestrator/command_processor.py) | inline in `process()` |
| [flow/manager.py](file:///Users/jorge/Projects/Playground/soni/src/soni/flow/manager.py) | `merge_delta()` |

**Impact**: Bug fixes need to be applied in multiple places. Inconsistent behavior risk.

**Recommendation**: Create single authoritative merge utility:

```python
# core/slot_utils.py (or extend core/types.py)
def deep_merge_flow_slots(
    base: dict[str, dict[str, Any]],
    new: dict[str, dict[str, Any]],
) -> dict[str, dict[str, Any]]:
    """Single source of truth for slot merging."""
    ...
```

**Estimated Effort**: 1-2 hours

---

### 6. Inconsistent `merge_delta` APIs

**Problem**: Two different APIs with similar names:

```python
# core/types.py
def merge_deltas(deltas: list[FlowDelta]) -> FlowDelta:
    """Merge multiple deltas into one."""

# flow/manager.py
def merge_delta(updates: dict[str, Any], delta: FlowDelta | None) -> None:
    """Mutates updates dict with delta contents."""
```

**Impact**: Confusing for developers. Easy to use wrong function.

**Recommendation**:
- Rename `flow/manager.py::merge_delta` to `apply_delta_to_dict`
- Or consolidate into `FlowDelta.apply_to(updates: dict)`

**Estimated Effort**: 30 minutes

---

### 7. `du/metrics.py` is Monolithic (375 lines)

**File**: [du/metrics.py](file:///Users/jorge/Projects/Playground/soni/src/soni/du/metrics.py)

**Problem**: Single file contains:
- `MetricScore` dataclass
- `FieldRegistry` class (registry pattern)
- Multiple scoring functions
- GEPA adapter
- Slot extraction metric

**Recommendation**: Split into focused modules:

```
du/metrics/
├── __init__.py          # Public exports
├── core.py              # MetricScore, normalize_value, compare_values
├── registry.py          # FieldRegistry with registered commands
├── scoring.py           # score_command_pair, score_command_lists
├── factory.py           # create_granular_metric, create_strict_metric
└── adapters.py          # adapt_metric_for_gepa, create_slot_extraction_metric
```

**Estimated Effort**: 1 hour

---

### 8. Debug Comments Left in Code

**File**: [core/types.py:78](file:///Users/jorge/Projects/Playground/soni/src/soni/core/types.py#L78)

```python
# print(f"DEBUG: _merge_flow_slots called. Current keys: {list(current.keys()) if current else 'None'}, New keys: {list(new.keys()) if new else 'None'}")
```

**Recommendation**: Remove or convert to proper `logger.debug()` call.

**Estimated Effort**: 15 minutes

---

### 9. Unnecessary Type Ignores

**File**: [config/loader.py:70](file:///Users/jorge/Projects/Playground/soni/src/soni/config/loader.py#L70)

```python
return SoniConfig.model_validate(data)  # type: ignore[no-any-return]
```

Mypy reports: `error: Unused "type: ignore" comment`

**Recommendation**: Remove the type ignore comment.

**Estimated Effort**: 30 minutes (audit all type ignores)

---

## 🟢 Low Priority Issues

### 10. Dataset Domain Files Are Large

Files like `dataset/domains/flight_booking.py` (381 lines) are large but self-contained data definitions. They work fine but could be split if needed.

**Recommendation**: Leave as-is unless adding more domains.

---

### 11. Repetitive Factory Pattern in compiler/nodes

Each step type has its own factory file (`action.py`, `branch.py`, etc.). The pattern is similar across all.

**Current**:
```python
class CollectNodeFactory:
    def create(self, step, all_steps, step_index) -> NodeFunction:
        ...
```

**Possible Improvement**: Use decorator-based registration:
```python
@step_factory("collect")
def create_collect_node(step: CollectStepConfig, ...) -> NodeFunction:
    ...
```

**Recommendation**: Low priority - current approach works fine.

---

### 12. Expression Parser Uses Regex

**File**: [core/expression.py](file:///Users/jorge/Projects/Playground/soni/src/soni/core/expression.py)

Uses manual string parsing with regex for expressions like `age > 18 AND status == 'approved'`.

**Recommendation**: Consider AST-based parsing only if complex expressions are needed in future.

---

## Type System Issues (from mypy)

```
src/soni/du/base.py:38: error: Redundant cast to "T"
src/soni/du/base.py:43: error: Redundant cast to "T"
src/soni/du/base.py:47: error: Redundant cast to "T"
src/soni/du/base.py:51: error: Redundant cast to "T"
src/soni/compiler/subgraph.py:118: error: Redundant cast to "str"
src/soni/compiler/subgraph.py:124: error: Redundant cast to "str"
src/soni/config/loader.py:70: error: Unused "type: ignore" comment
src/soni/dataset/slot_extraction.py:92: error: List item incompatible type
src/soni/dataset/slot_extraction.py:127: error: Argument incompatible type
src/soni/runtime/loop.py:163: error: Incompatible types in assignment
```

---

## Proposed Implementation Phases

### Phase 1: Quick Wins (2 hours)
- [ ] Remove redundant `cast()` calls (10+ files)
- [ ] Remove debug comments
- [ ] Remove unused type ignores
- [ ] Fix mypy errors in `dataset/slot_extraction.py`

### Phase 2: Structure (4 hours)
- [ ] Refactor `understand_node` into separate classes
- [ ] Extract orchestrator helpers to `state_utils.py`

### Phase 3: Consolidation (2 hours)
- [ ] Consolidate slot merge logic
- [ ] Unify `merge_delta` APIs
- [ ] Modularize `du/metrics.py`

### Phase 4: CLI (2 hours)
- [ ] Refactor `run_chat` into `ChatRunner` class

---

## Files Summary

| Priority | File | Issue | Action |
|----------|------|-------|--------|
| 🔴 HIGH | dm/nodes/understand.py | SRP violation, 264 LOC | Split into 3-4 files |
| 🔴 HIGH | dm/nodes/orchestrator.py | Helpers mixed with logic | Extract state_utils.py |
| 🔴 HIGH | Multiple (10+ files) | Redundant casts | Remove |
| 🔴 HIGH | cli/commands/chat.py | Too complex | Extract ChatRunner |
| 🟡 MED | core/types.py + 3 others | Duplicate merge logic | Consolidate |
| 🟡 MED | core/types.py, flow/manager.py | API inconsistency | Rename/unify |
| 🟡 MED | du/metrics.py | Monolithic 375 LOC | Split into modules |
| 🟡 MED | core/types.py | Debug comment | Remove |
| 🟡 MED | config/loader.py | Unused type ignore | Remove |

---

## Estimated Total Effort

| Phase | Hours |
|-------|-------|
| Phase 1: Quick Wins | 2h |
| Phase 2: Structure | 4h |
| Phase 3: Consolidation | 2h |
| Phase 4: CLI | 2h |
| **Total** | **~10 hours** |

---

## Next Steps

1. Review this analysis
2. Decide which phases to implement
3. Create individual task files for each refactoring
4. Implement with TDD approach (tests first where applicable)

---

*Analysis performed by: AI Assistant*
*Methodology: Static analysis, ruff linting, mypy type checking, manual code review*
