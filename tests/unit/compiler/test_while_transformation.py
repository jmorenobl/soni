"""Unit tests for while loop transformation in SubgraphBuilder."""

import pytest

from soni.compiler.subgraph import SubgraphBuilder
from soni.core.config import FlowConfig, StepConfig


class TestWhileLoopTransformation:
    """Tests for while loop to branch+jump_to transformation."""

    def test_while_loop_transforms_to_branch_guard(self):
        """
        GIVEN a while loop step
        WHEN built
        THEN while step is transformed to branch guard with correct name
        """
        # Arrange
        config = FlowConfig(
            description="Test while loop",
            steps=[
                StepConfig(
                    step="counter_loop",
                    type="while",
                    condition="counter < 3",
                    do=["increment"],
                ),
                StepConfig(
                    step="increment",
                    type="action",
                    call="increment_counter",
                ),
            ],
        )
        builder = SubgraphBuilder()

        # Act
        graph = builder.build(config)
        compiled = graph.compile()

        # Assert - while node should not exist, guard should
        assert "counter_loop" not in compiled.nodes
        assert "counter_loop_guard" in compiled.nodes
        assert "increment" in compiled.nodes

    def test_while_loop_auto_adds_jump_to_on_last_step(self):
        """
        GIVEN while loop with multiple steps in do block
        WHEN built
        THEN last step gets auto-added jump_to pointing to guard
        """
        # Arrange
        steps = [
            StepConfig(
                step="my_loop",
                type="while",
                condition="x < 10",
                do=["step_a", "step_b"],
            ),
            StepConfig(step="step_a", type="say", message="A"),
            StepConfig(step="step_b", type="say", message="B"),
        ]
        builder = SubgraphBuilder()

        # Act
        transformed_steps, mappings = builder._transform_while_loops(steps)

        # Assert
        # Find step_b in transformed steps
        step_b = next(s for s in transformed_steps if s.step == "step_b")
        assert step_b.jump_to == "my_loop_guard"

    def test_name_mapping_translates_jump_to_references(self):
        """
        GIVEN a step with jump_to pointing to while loop name
        WHEN name mapping is applied
        THEN jump_to is translated to guard name
        """
        # Arrange
        steps = [
            StepConfig(
                step="my_loop",
                type="while",
                condition="i < 5",
                do=["work"],
            ),
            StepConfig(step="work", type="action", call="do_work"),
            StepConfig(
                step="restart",
                type="say",
                message="Restarting",
                jump_to="my_loop",  # Points to while loop
            ),
        ]
        builder = SubgraphBuilder()

        # Act - transform and translate
        transformed, mappings = builder._transform_while_loops(steps)
        builder._translate_jumps(transformed, mappings)

        # Assert
        restart_step = next(s for s in transformed if s.step == "restart")
        assert restart_step.jump_to == "my_loop_guard"

    def test_while_loop_calculates_exit_target(self):
        """
        GIVEN while loop without explicit exit_to
        WHEN compiled
        THEN exit target is auto-calculated to first step after do block
        """
        # Arrange
        steps = [
            StepConfig(
                step="loop",
                type="while",
                condition="running",
                do=["process"],
            ),
            StepConfig(step="process", type="action", call="process_item"),
            StepConfig(step="done", type="say", message="Complete"),
        ]
        builder = SubgraphBuilder()

        # Act
        transformed, mappings = builder._transform_while_loops(steps)

        # Assert
        assert "loop" in mappings
        guard = next(s for s in transformed if s.step == "loop_guard")
        assert guard.type == "branch"
        assert guard.cases is not None
        assert guard.cases["false"] == "done"  # Exit to first step after loop

    def test_while_loop_with_explicit_exit_to(self):
        """
        GIVEN while loop with explicit exit_to
        WHEN compiled
        THEN uses specified exit target
        """
        # Arrange
        steps = [
            StepConfig(
                step="loop",
                type="while",
                condition="active",
                do=["work"],
                exit_to="cleanup",
            ),
            StepConfig(step="work", type="action", call="do_work"),
            StepConfig(step="next_flow", type="say", message="Next"),
            StepConfig(step="cleanup", type="say", message="Cleanup"),
        ]
        builder = SubgraphBuilder()

        # Act
        transformed, _ = builder._transform_while_loops(steps)

        # Assert
        guard = next(s for s in transformed if s.step == "loop_guard")
        assert guard.cases is not None
        assert guard.cases["false"] == "cleanup"

    def test_branch_guard_uses_evaluate_not_slot(self):
        """
        GIVEN while loop with condition
        WHEN transformed
        THEN guard uses evaluate field, not slot
        """
        # Arrange
        steps = [
            StepConfig(
                step="counter",
                type="while",
                condition="index < max_count",
                do=["increment"],
            ),
            StepConfig(step="increment", type="action", call="inc"),
        ]
        builder = SubgraphBuilder()

        # Act
        transformed, _ = builder._transform_while_loops(steps)

        # Assert
        guard = next(s for s in transformed if s.step == "counter_guard")
        assert guard.type == "branch"
        assert guard.evaluate == "index < max_count"
        assert guard.slot is None
        assert guard.cases is not None
        assert "true" in guard.cases
        assert "false" in guard.cases

    def test_multiple_while_loops_each_get_unique_guards(self):
        """
        GIVEN multiple while loops in same flow
        WHEN transformed
        THEN each gets its own guard with unique name
        """
        # Arrange
        steps = [
            StepConfig(step="loop1", type="while", condition="a < 5", do=["work1"]),
            StepConfig(step="work1", type="action", call="work"),
            StepConfig(step="loop2", type="while", condition="b < 10", do=["work2"]),
            StepConfig(step="work2", type="action", call="work"),
        ]
        builder = SubgraphBuilder()

        # Act
        transformed, mappings = builder._transform_while_loops(steps)

        # Assert
        assert "loop1" in mappings
        assert "loop2" in mappings
        assert mappings["loop1"] == "loop1_guard"
        assert mappings["loop2"] == "loop2_guard"

        guard_names = [s.step for s in transformed if s.type == "branch"]
        assert "loop1_guard" in guard_names
        assert "loop2_guard" in guard_names

    def test_while_loop_without_condition_raises_error(self):
        """
        GIVEN while loop without condition
        WHEN compiled
        THEN raises ValueError
        """
        # Arrange
        steps = [
            StepConfig(step="bad_loop", type="while", do=["work"]),
            StepConfig(step="work", type="action", call="work"),
        ]
        builder = SubgraphBuilder()

        # Act & Assert
        with pytest.raises(ValueError, match="missing condition"):
            builder._compile_while(steps[0], steps)

    def test_while_loop_without_do_block_raises_error(self):
        """
        GIVEN while loop without do block
        WHEN compiled
        THEN raises ValueError
        """
        # Arrange
        steps = [
            StepConfig(step="bad_loop", type="while", condition="x < 5"),
        ]
        builder = SubgraphBuilder()

        # Act & Assert
        with pytest.raises(ValueError, match="missing do block"):
            builder._compile_while(steps[0], steps)

    def test_full_flow_with_while_loop_compiles(self):
        """
        GIVEN complete flow with while loop
        WHEN built
        THEN compiles successfully and contains all nodes
        """
        # Arrange
        config = FlowConfig(
            description="Full test",
            steps=[
                StepConfig(step="init", type="say", message="Start"),
                StepConfig(
                    step="process_loop",
                    type="while",
                    condition="items_remaining > 0",
                    do=["process_item", "decrement"],
                ),
                StepConfig(step="process_item", type="action", call="process"),
                StepConfig(step="decrement", type="action", call="decrement_count"),
                StepConfig(step="finish", type="say", message="Done"),
            ],
        )
        builder = SubgraphBuilder()

        # Act
        graph = builder.build(config)
        compiled = graph.compile()

        # Assert
        assert "init" in compiled.nodes
        assert "process_loop_guard" in compiled.nodes
        assert "process_item" in compiled.nodes
        assert "decrement" in compiled.nodes
        assert "finish" in compiled.nodes
        assert "process_loop" not in compiled.nodes  # Original while node removed
