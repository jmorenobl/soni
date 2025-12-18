"""Unit tests for configuration."""

from pathlib import Path

import pytest

from soni.config import (
    ActionStepConfig,
    CollectStepConfig,
    FlowConfig,
    SoniConfig,
    StepConfig,
)
from soni.config.loader import ConfigLoader
from soni.core.errors import ConfigError


class TestConfigModels:
    """Tests for Pydantic config models."""

    def test_step_config_defaults(self):
        """
        GIVEN minimal step data
        WHEN StepConfig is created
        THEN defaults are applied
        """
        # Test defaults on a specific type
        step = CollectStepConfig(step="step1", type="collect", slot="my_slot")
        assert step.message is None  # Optional field default

        # Action step doesn't have 'slot'
        action = ActionStepConfig(step="step2", type="action", call="my_func")
        assert not hasattr(action, "slot")

    def test_steps_or_process_property(self):
        """Test steps_or_process returns correct list."""
        # Case 1: steps
        fc1 = FlowConfig(
            description="desc",
            steps=[ActionStepConfig(step="s1", type="action", call="my_func")],
        )
        assert len(fc1.steps) == 1


class TestConfigLoader:
    """Tests for ConfigLoader."""

    def test_load_non_existent_file_raises_error(self):
        """
        GIVEN valid path to missing file
        WHEN load is called
        THEN raises ConfigError
        """
        with pytest.raises(ConfigError, match="Configuration file not found"):
            ConfigLoader.load(Path("non_existent.yaml"))

    def test_load_valid_yaml(self, tmp_path):
        """Test loading valid YAML configuration."""
        # Arrange
        config_file = tmp_path / "soni.yaml"
        yaml_content = """
version: "1.0"
flows:
  book_flight:
    name: book_flight
    description: "Book a flight"
    steps:
      - step: collect_origin
        type: collect
        slot: origin
"""
        config_file.write_text(yaml_content)

        # Act
        config = ConfigLoader.load(config_file)

        # Assert
        assert config.version == "1.0"
        assert "book_flight" in config.flows
        assert config.flows["book_flight"].description == "Book a flight"
        # Access specifically typed step
        step = config.flows["book_flight"].steps[0]
        assert isinstance(step, CollectStepConfig)
        assert step.slot == "origin"
