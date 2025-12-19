## Task: P0-003 - Fix Config Mutation in SubgraphBuilder

**Task ID:** P0-003
**Milestone:** 1.3 - Prevent Concurrency Bugs
**Dependencies:** None
**Estimated Duration:** 2 hours

### Objective

Eliminate direct mutation of input parameters in `SubgraphBuilder`, which causes bugs when multiple threads compile the same configuration simultaneously.

### Context

**The problem (lines 171-172 and 191-196 of `compiler/subgraph.py`):**

```python
# In _compile_while (line 171-172)
if not last_step.jump_to:
    last_step.jump_to = guard_name  # ❌ MUTATES INPUT

# In _translate_jumps (line 191)
step.jump_to = name_mappings[target]  # ❌ MUTATES INPUT

# In _translate_jumps (lines 195-196)
step.cases = {  # ❌ MUTATES INPUT
    key: name_mappings.get(target, target) for key, target in step.cases.items()
}
```

**Bug scenario:**
1. Thread A compiles flow "transfer" - modifies `last_step.jump_to`
2. Thread B compiles flow "transfer" simultaneously - reads already modified `last_step.jump_to`
3. Result: Unpredictable behavior, infinite loops, or incorrect jumps

**Principles violated:**
- **Immutability**: Transformation functions must not mutate inputs
- **Thread Safety**: Shared code must be free of side effects
- **SRP**: Method should return new objects, not modify existing ones

### Deliverables

- [ ] `_transform_while_loops` creates deep copies before any mutation
- [ ] No input parameters are mutated
- [ ] Concurrent compilation tests verify isolation
- [ ] Existing compiler tests pass

---

### Implementation Details

#### Step 1: Add deepcopy import

**File:** `src/soni/compiler/subgraph.py`

**Add to imports:**

```python
from copy import deepcopy
from typing import Any
# ... rest
```

#### Step 2: Create copies in _transform_while_loops

**File:** `src/soni/compiler/subgraph.py`

**Current code (lines 87-108):**

```python
def _transform_while_loops(
    self, steps: list[StepConfig]
) -> tuple[list[StepConfig], dict[str, str]]:
    """Transform while loops into branch + jump_to pattern."""
    transformed_steps = []
    name_mappings: dict[str, str] = {}

    for step in steps:
        if isinstance(step, WhileStepConfig):
            guard_step, mapping = self._compile_while(step, steps)  # ❌ Passes original
            transformed_steps.append(guard_step)
            name_mappings.update(mapping)
        else:
            transformed_steps.append(step)

    return transformed_steps, name_mappings
```

**Fixed code:**

```python
def _transform_while_loops(
    self, steps: list[StepConfig]
) -> tuple[list[StepConfig], dict[str, str]]:
    """Transform while loops into branch + jump_to pattern.

    Creates deep copies of steps to avoid mutating input configuration.
    This ensures thread-safe compilation of the same config.
    """
    # Deep copy all steps to avoid mutating input
    # Critical for thread safety when compiling same config concurrently
    mutable_steps = [deepcopy(step) for step in steps]

    transformed_steps = []
    name_mappings: dict[str, str] = {}

    for step in mutable_steps:
        if isinstance(step, WhileStepConfig):
            # Pass mutable_steps so _compile_while can safely modify
            guard_step, mapping = self._compile_while(step, mutable_steps)
            transformed_steps.append(guard_step)
            name_mappings.update(mapping)
        else:
            transformed_steps.append(step)

    return transformed_steps, name_mappings
```

#### Step 3: Update docstring in _compile_while

**File:** `src/soni/compiler/subgraph.py`

```python
def _compile_while(
    self, step: WhileStepConfig, all_steps: list[StepConfig]
) -> tuple[StepConfig, dict[str, str]]:
    """Compile a while step into a branch guard step.

    Note: This method mutates `all_steps` to set jump_to on the last step
    of the do: block. Callers must pass a mutable copy if the original
    should remain unchanged.

    Args:
        step: The while step configuration to compile.
        all_steps: Mutable list of all steps (will be modified).

    Returns:
        Tuple of (guard_step, name_mapping).
    """
```

---

### TDD Cycle (MANDATORY)

#### Red Phase: Write Failing Tests

**Test file:** `tests/unit/compiler/test_subgraph_immutability.py`

```python
"""Tests for SubgraphBuilder immutability and thread safety.

Verifies that compilation doesn't mutate input configuration,
ensuring safe concurrent compilation of the same config.
"""

import threading
from concurrent.futures import ThreadPoolExecutor
from copy import deepcopy
from unittest.mock import MagicMock

import pytest

from soni.compiler.subgraph import SubgraphBuilder
from soni.config.models import FlowConfig
from soni.config.steps import (
    BranchStepConfig,
    CollectStepConfig,
    StepConfig,
    WhileStepConfig,
)


def create_while_flow_config() -> FlowConfig:
    """Create a flow config with a while loop for testing."""
    steps: list[StepConfig] = [
        CollectStepConfig(
            step="ask_continue",
            type="collect",
            slot="continue_choice",
            message="Do you want to continue?",
        ),
        WhileStepConfig(
            step="retry_loop",
            type="while",
            condition="slots.continue_choice == 'yes'",
            do=["ask_continue"],
        ),
        CollectStepConfig(
            step="final_step",
            type="collect",
            slot="final_input",
            message="Final question",
        ),
    ]

    config = MagicMock(spec=FlowConfig)
    config.steps = steps
    config.name = "test_flow"

    return config


class TestCompileWhileImmutability:
    """Tests for _compile_while not mutating input."""

    def test_compile_does_not_mutate_original_steps(self) -> None:
        """Test that build() doesn't mutate the input FlowConfig.steps."""
        flow_config = create_while_flow_config()
        original_steps = deepcopy(flow_config.steps)

        builder = SubgraphBuilder()
        builder.build(flow_config)

        # Verify original steps are unchanged
        for original, current in zip(original_steps, flow_config.steps):
            assert original.jump_to == current.jump_to, (
                f"Step '{current.step}' was mutated: "
                f"jump_to changed from {original.jump_to!r} to {current.jump_to!r}"
            )

    def test_compile_while_returns_independent_steps(self) -> None:
        """Test that transformed steps are independent from original."""
        flow_config = create_while_flow_config()
        original_collect_step = flow_config.steps[0]  # ask_continue

        builder = SubgraphBuilder()
        builder.build(flow_config)

        # Original step should not have jump_to set
        assert original_collect_step.jump_to is None, (
            f"Original step was mutated: jump_to = {original_collect_step.jump_to!r}"
        )

    def test_branch_cases_not_mutated(self) -> None:
        """Test that branch step cases are not mutated."""
        # Create flow with branch that references a while loop
        steps: list[StepConfig] = [
            BranchStepConfig(
                step="check_branch",
                type="branch",
                slot="choice",
                cases={"yes": "my_loop", "no": "end_step"},
            ),
            CollectStepConfig(
                step="loop_body",
                type="collect",
                slot="data",
                message="Enter data",
            ),
            WhileStepConfig(
                step="my_loop",
                type="while",
                condition="slots.continue == 'yes'",
                do=["loop_body"],
            ),
            CollectStepConfig(
                step="end_step",
                type="collect",
                slot="final",
                message="Done",
            ),
        ]

        config = MagicMock(spec=FlowConfig)
        config.steps = steps
        config.name = "test_flow"

        original_cases = steps[0].cases.copy()

        builder = SubgraphBuilder()
        builder.build(config)

        # Original branch cases should be unchanged
        assert steps[0].cases == original_cases, (
            f"Branch cases mutated: {original_cases} -> {steps[0].cases}"
        )


class TestConcurrentCompilation:
    """Tests for thread-safe concurrent compilation."""

    def test_concurrent_compilation_produces_consistent_results(self) -> None:
        """Test that compiling same config concurrently produces same results."""
        flow_config = create_while_flow_config()
        builder = SubgraphBuilder()

        results: list[tuple[int, int]] = []
        errors: list[tuple[int, Exception]] = []

        def compile_and_store(thread_id: int) -> None:
            try:
                graph = builder.build(flow_config)
                node_count = len(graph.nodes)
                results.append((thread_id, node_count))
            except Exception as e:
                errors.append((thread_id, e))

        # Run 10 concurrent compilations
        threads = [
            threading.Thread(target=compile_and_store, args=(i,))
            for i in range(10)
        ]

        for t in threads:
            t.start()
        for t in threads:
            t.join()

        assert not errors, f"Compilation errors: {errors}"

        # All results should have same node count
        node_counts = [r[1] for r in results]
        assert len(set(node_counts)) == 1, (
            f"Inconsistent results from concurrent compilation: {node_counts}"
        )

    def test_concurrent_compilation_with_threadpool(self) -> None:
        """Test compilation with ThreadPoolExecutor (like production)."""
        flow_config = create_while_flow_config()
        builder = SubgraphBuilder()

        def compile_flow(_: int) -> int:
            graph = builder.build(flow_config)
            return len(graph.nodes)

        with ThreadPoolExecutor(max_workers=5) as executor:
            futures = [executor.submit(compile_flow, i) for i in range(20)]
            results = [f.result() for f in futures]

        assert len(set(results)) == 1, f"Inconsistent results: {results}"

    def test_original_config_unchanged_after_concurrent_compilation(self) -> None:
        """Test that original config unchanged after many concurrent compiles."""
        flow_config = create_while_flow_config()
        original_steps_snapshot = [
            (s.step, s.jump_to) for s in flow_config.steps
        ]

        builder = SubgraphBuilder()

        with ThreadPoolExecutor(max_workers=5) as executor:
            futures = [
                executor.submit(builder.build, flow_config)
                for _ in range(20)
            ]
            for f in futures:
                f.result()

        current_steps_snapshot = [
            (s.step, s.jump_to) for s in flow_config.steps
        ]

        assert original_steps_snapshot == current_steps_snapshot, (
            f"Original config was mutated!\n"
            f"Before: {original_steps_snapshot}\n"
            f"After: {current_steps_snapshot}"
        )


class TestDeepCopyUsage:
    """Tests verifying deep copy is used correctly."""

    def test_steps_are_deep_copied(self) -> None:
        """Test that steps are deep copied during transformation."""
        flow_config = create_while_flow_config()
        original_collect_step = flow_config.steps[0]

        builder = SubgraphBuilder()

        # Access internal method to verify deep copy behavior
        transformed, _ = builder._transform_while_loops(flow_config.steps)

        # Find the transformed ask_continue step
        transformed_collect = next(
            (s for s in transformed if s.step == "ask_continue"),
            None
        )

        # Should be a different object (deep copied)
        if transformed_collect is not None:
            assert transformed_collect is not original_collect_step, (
                "Transformed step is same object as original (not deep copied)"
            )

    def test_nested_dicts_are_copied(self) -> None:
        """Test that nested dicts in steps are also copied."""
        # BranchStepConfig has cases dict
        branch_step = BranchStepConfig(
            step="test_branch",
            type="branch",
            slot="choice",
            cases={"a": "step_a", "b": "step_b"},
        )

        steps: list[StepConfig] = [branch_step]
        original_cases_id = id(branch_step.cases)

        builder = SubgraphBuilder()
        transformed, _ = builder._transform_while_loops(steps)

        transformed_branch = next(
            (s for s in transformed if s.step == "test_branch"),
            None
        )

        if transformed_branch and isinstance(transformed_branch, BranchStepConfig):
            # Cases dict should be a different object
            assert id(transformed_branch.cases) != original_cases_id, (
                "cases dict was not deep copied"
            )
```

**Run tests (should fail):**
```bash
uv run pytest tests/unit/compiler/test_subgraph_immutability.py -v
# Expected: FAILED (steps are being mutated)
```

**Commit:**
```bash
git add tests/
git commit -m "test: add failing tests for SubgraphBuilder immutability (P0-003)"
```

#### Green Phase: Make Tests Pass

**Implement the changes described in "Implementation Details" section.**

**Verify tests pass:**
```bash
uv run pytest tests/unit/compiler/test_subgraph_immutability.py -v
# Expected: PASSED ✅
```

**Commit:**
```bash
git add src/ tests/
git commit -m "fix: prevent config mutation in SubgraphBuilder (P0-003)"
```

---

### Success Criteria

- [ ] `build()` does not mutate `FlowConfig.steps`
- [ ] Concurrent compilation produces consistent results
- [ ] Transformed steps are independent objects (deep copied)
- [ ] All existing compiler tests pass
- [ ] Concurrent tests (10+ threads) pass consistently

### Manual Validation

```bash
# 1. Run immutability tests
uv run pytest tests/unit/compiler/test_subgraph_immutability.py -v

# 2. Run all compiler tests for regressions
uv run pytest tests/unit/compiler/ -v

# 3. Run concurrent tests multiple times
for i in {1..5}; do
    echo "Run $i:"
    uv run pytest tests/unit/compiler/test_subgraph_immutability.py::TestConcurrentCompilation -v
done

# 4. Verify deepcopy is used
uv run rg "deepcopy" src/soni/compiler/subgraph.py
```

### References

- `src/soni/compiler/subgraph.py` - File to modify
- [Python copy module](https://docs.python.org/3/library/copy.html)
- [Thread Safety in Python](https://docs.python.org/3/library/threading.html)

### Notes

**Why deepcopy not shallow copy:**
`copy.copy()` only copies the top-level object. If a step has list or dict attributes, they would be shared between original and copy. `deepcopy` guarantees fully independent copies.

**Performance:**
For typical configs (<100 steps), deepcopy is negligible (~1ms). If it becomes a bottleneck:
1. Cache compilations by config hash
2. Use immutable structures from the start (frozen dataclasses)

**Future improvement - Frozen Steps:**
Consider making StepConfig immutable by design:

```python
@dataclass(frozen=True)
class StepConfig:
    step: str
    type: str
    jump_to: str | None = None

# Instead of mutating, create new object:
new_step = replace(last_step, jump_to=guard_name)
```

This prevents the problem at compile time. Evaluate as future enhancement.
