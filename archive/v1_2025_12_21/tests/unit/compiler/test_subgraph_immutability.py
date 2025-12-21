"""Tests for SubgraphBuilder immutability and thread safety.

Verifies that compilation doesn't mutate input configuration,
ensuring safe concurrent compilation of the same config.
"""

import threading
from concurrent.futures import ThreadPoolExecutor
from copy import deepcopy
from unittest.mock import MagicMock

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
        for original, current in zip(original_steps, flow_config.steps, strict=True):
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
        threads = [threading.Thread(target=compile_and_store, args=(i,)) for i in range(10)]

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
        original_steps_snapshot = [(s.step, s.jump_to) for s in flow_config.steps]

        builder = SubgraphBuilder()

        with ThreadPoolExecutor(max_workers=5) as executor:
            futures = [executor.submit(builder.build, flow_config) for _ in range(20)]
            for f in futures:
                f.result()

        current_steps_snapshot = [(s.step, s.jump_to) for s in flow_config.steps]

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
        transformed_collect = next((s for s in transformed if s.step == "ask_continue"), None)

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

        transformed_branch = next((s for s in transformed if s.step == "test_branch"), None)

        if transformed_branch and isinstance(transformed_branch, BranchStepConfig):
            # Cases dict should be a different object
            assert id(transformed_branch.cases) != original_cases_id, (
                "cases dict was not deep copied"
            )
