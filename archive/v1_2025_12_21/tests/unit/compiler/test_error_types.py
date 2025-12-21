import pytest

from soni.compiler.factory import NodeFactoryRegistry
from soni.compiler.subgraph import SubgraphBuilder
from soni.core.errors import GraphBuildError, ValidationError


class TestFactoryErrorTypes:
    """Tests for error types in factory module."""

    def test_unknown_step_type_raises_graph_build_error(self):
        """Test that unknown step type raises GraphBuildError, not ValueError."""
        with pytest.raises(GraphBuildError) as exc_info:
            NodeFactoryRegistry.get("nonexistent_type")

        assert "Unknown step type" in str(exc_info.value)
        assert "nonexistent_type" in str(exc_info.value)

    def test_unknown_step_type_includes_available_types(self):
        """Test that error message includes available step types."""
        with pytest.raises(GraphBuildError) as exc_info:
            NodeFactoryRegistry.get("invalid")

        # Should mention some valid types
        error_msg = str(exc_info.value)
        assert "say" in error_msg or "collect" in error_msg


class TestSubgraphErrorTypes:
    """Tests for error types in subgraph module."""

    def test_while_missing_condition_raises_graph_build_error(self):
        """Test that while step without condition raises GraphBuildError."""
        from soni.config.steps import WhileStepConfig

        from soni.config.models import FlowConfig

        # Create flow with invalid while step - Note: Pydantic validation might kick in first if using strict types
        # But here we simulate runtime config loaded which might bypass if constructed manually via dict or if optional in pydantic but enforced in logic
        # Actually WhileStepConfig makes condition optional? Let's check.
        # If strict Pydantic models are used, this might raise ValidationError during init.
        # However, SubgraphBuilder might be checking fields on objects.
        # Let's assume we construct a config that passes Pydantic but fails logic, or use generic dict access via StepConfig if that was allowed.
        # Given Task 006 migration, WhileStepConfig enforces structure.
        # If 'condition' is required in Pydantic, we can't construct invalid object easily.
        # But 'condition' might be optional in model but required for graph building?
        # Let's try to construct manually or see if we can trigger the compiler error.

        # If Pydantic catches it, that's ValidationError. Task says replace ValueError in compiler.
        # Compiler code checks `if not step.condition`.
        # We need to construct a step that enters that block.
        # If `step` is `WhileStepConfig`, and condition is `str`.
        # If I pass empty string?

        flow_config = FlowConfig(
            name="test_flow",
            description="Test",
            steps=[
                WhileStepConfig(step="loop", do=["step1"], condition="")  # Empty condition
            ],
        )

        builder = SubgraphBuilder()

        with pytest.raises(GraphBuildError) as exc_info:
            builder.build(flow_config)

        assert "condition" in str(exc_info.value).lower()
        # Verify it's not generic ValueError
        assert exc_info.type == GraphBuildError

    def test_while_missing_do_raises_graph_build_error(self):
        """Test that while step without do block raises GraphBuildError."""
        from soni.config.steps import WhileStepConfig

        from soni.config.models import FlowConfig

        flow_config = FlowConfig(
            name="test_flow",
            description="Test",
            steps=[
                WhileStepConfig(step="loop", condition="slots.count < 3", do=[])  # Empty do list?
                # Compiler checks `if not step.do`. Empty list is falsy.
            ],
        )

        builder = SubgraphBuilder()

        with pytest.raises(GraphBuildError) as exc_info:
            builder.build(flow_config)

        assert "do" in str(exc_info.value).lower()
        assert exc_info.type == GraphBuildError


class TestNodeFactoryErrorTypes:
    """Tests for error types in individual node factories."""

    def test_say_missing_message_raises_validation_error(self):
        """Test that say step without message raises ValidationError."""
        from soni.config.steps import SayStepConfig

        from soni.compiler.nodes.say import SayNodeFactory

        # Use model_construct to bypass Pydantic validation
        step = SayStepConfig.model_construct(step="greet", type="say")
        factory = SayNodeFactory()

        with pytest.raises(ValidationError) as exc_info:
            factory.create(step, all_steps=[], step_index=0)

        assert "message" in str(exc_info.value).lower()

    def test_collect_missing_slot_raises_validation_error(self):
        """Test that collect step without slot raises ValidationError."""
        from soni.config.steps import CollectStepConfig

        from soni.compiler.nodes.collect import CollectNodeFactory

        step = CollectStepConfig.model_construct(step="get_name", type="collect", message="hi")
        factory = CollectNodeFactory()

        with pytest.raises(ValidationError) as exc_info:
            factory.create(step, all_steps=[], step_index=0)

        assert "slot" in str(exc_info.value).lower()

    def test_action_missing_call_raises_validation_error(self):
        """Test that action step without call raises ValidationError."""
        from soni.compiler.nodes.action import ActionNodeFactory
        from soni.config.steps import ActionStepConfig

        step = ActionStepConfig.model_construct(step="do_something", type="action")
        factory = ActionNodeFactory()

        with pytest.raises(ValidationError) as exc_info:
            factory.create(step, all_steps=[], step_index=0)

        assert "call" in str(exc_info.value).lower()

    def test_branch_missing_cases_raises_validation_error(self):
        """Test that branch step without cases raises ValidationError."""
        from soni.compiler.nodes.branch import BranchNodeFactory
        from soni.config.steps import BranchStepConfig

        step = BranchStepConfig.model_construct(step="check", type="branch", evaluate="slots.value")
        factory = BranchNodeFactory()

        with pytest.raises(ValidationError) as exc_info:
            factory.create(step, all_steps=[], step_index=0)

        assert "cases" in str(exc_info.value).lower()
