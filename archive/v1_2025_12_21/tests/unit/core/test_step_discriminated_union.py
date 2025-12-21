import pytest
from pydantic import TypeAdapter, ValidationError

from soni.config.steps import (
    BranchStepConfig,
    CollectStepConfig,
    SayStepConfig,
    StepConfig,
)


class TestStepConfigDiscriminator:
    """Tests for discriminated union step parsing."""

    def test_say_step_parses_correctly(self):
        """Test that say step with message parses to SayStepConfig."""
        data = {"step": "greet", "type": "say", "message": "Hello!"}

        # Parse through Pydantic adapter
        adapter = TypeAdapter(StepConfig)
        result = adapter.validate_python(data)

        assert isinstance(result, SayStepConfig)
        assert result.message == "Hello!"

    def test_collect_step_parses_correctly(self):
        """Test that collect step parses to CollectStepConfig."""
        data = {"step": "get_name", "type": "collect", "slot": "name"}

        adapter = TypeAdapter(StepConfig)
        result = adapter.validate_python(data)

        assert isinstance(result, CollectStepConfig)
        assert result.slot == "name"

    def test_say_step_requires_message(self):
        """Test that say step without message raises validation error."""
        data = {"step": "greet", "type": "say"}  # Missing message!

        adapter = TypeAdapter(StepConfig)

        with pytest.raises(ValidationError) as exc_info:
            adapter.validate_python(data)

        assert "message" in str(exc_info.value)

    def test_collect_step_requires_slot(self):
        """Test that collect step without slot raises validation error."""
        data = {"step": "get_name", "type": "collect"}  # Missing slot!

        adapter = TypeAdapter(StepConfig)

        with pytest.raises(ValidationError) as exc_info:
            adapter.validate_python(data)

        assert "slot" in str(exc_info.value)

    def test_unknown_type_raises_error(self):
        """Test that unknown step type raises validation error."""
        data = {"step": "invalid", "type": "nonexistent"}

        adapter = TypeAdapter(StepConfig)

        with pytest.raises(ValidationError) as exc_info:
            adapter.validate_python(data)

        # Should mention discriminator issue or invalid type
        assert (
            "type" in str(exc_info.value).lower()
            or "input should be" in str(exc_info.value).lower()
        )

    def test_branch_step_requires_cases(self):
        """Test that branch step requires cases dict."""
        data = {
            "step": "check",
            "type": "branch",
            "evaluate": "slots.value > 0",
            # Missing cases!
        }

        adapter = TypeAdapter(StepConfig)

        with pytest.raises(ValidationError) as exc_info:
            adapter.validate_python(data)

        assert "cases" in str(exc_info.value)


class TestStepConfigTypeNarrowing:
    """Tests for type narrowing with isinstance."""

    def test_isinstance_say_step(self):
        """Test that parsed say step passes isinstance check."""
        step = SayStepConfig(step="greet", type="say", message="Hello")

        assert isinstance(step, SayStepConfig)
        # IDE should know step.message is str, not str | None

    def test_isinstance_in_loop(self):
        """Test type narrowing in a processing loop."""
        steps = [
            SayStepConfig(step="greet", type="say", message="Hello"),
            CollectStepConfig(step="get_name", type="collect", slot="name"),
        ]

        for step in steps:
            if isinstance(step, SayStepConfig):
                # Type narrowed to SayStepConfig
                assert step.message is not None
            elif isinstance(step, CollectStepConfig):
                # Type narrowed to CollectStepConfig
                assert step.slot is not None


class TestFlowConfigWithDiscriminatedSteps:
    """Tests for FlowConfig using discriminated steps."""

    def test_flow_config_parses_mixed_steps(self):
        """Test that FlowConfig correctly parses mixed step types."""
        from soni.config.models import FlowConfig

        data = {
            "name": "greeting_flow",
            "description": "A test flow",
            "steps": [
                {"step": "greet", "type": "say", "message": "Hello!"},
                {"step": "get_name", "type": "collect", "slot": "name"},
                {"step": "farewell", "type": "say", "message": "Goodbye {name}!"},
            ],
        }

        flow = FlowConfig(**data)

        assert len(flow.steps) == 3
        assert isinstance(flow.steps[0], SayStepConfig)
        assert isinstance(flow.steps[1], CollectStepConfig)
        assert isinstance(flow.steps[2], SayStepConfig)

    def test_flow_config_rejects_invalid_step(self):
        """Test that FlowConfig rejects flow with invalid step."""
        from soni.config.models import FlowConfig

        data = {
            "name": "bad_flow",
            "description": "Invalid flow",
            "steps": [
                {"step": "greet", "type": "say"},  # Missing message!
            ],
        }

        with pytest.raises(ValidationError):
            FlowConfig(**data)
