"""Unit tests for configuration."""

from pathlib import Path

import pytest

from soni.core.config import FlowConfig, SoniConfig, StepConfig
from soni.core.errors import ConfigError
from soni.core.loader import ConfigLoader


class TestConfigModels:
    """Tests for Pydantic config models."""

    def test_step_config_defaults(self):
        """
        GIVEN minimal step data
        WHEN StepConfig is created
        THEN defaults are applied
        """
        step = StepConfig(step="step1", type="action")
        assert step.slot is None
        assert step.call is None

    def test_steps_or_process_property(self):
        """Test steps_or_process returns correct list."""
        # Case 1: steps
        fc1 = FlowConfig(description="desc", steps=[StepConfig(step="s1", type="action")])
        assert len(fc1.steps) == 1


class TestConfigLoader:
    """Tests for ConfigLoader."""

    def test_load_non_existent_file_raises_error(self):
        """
        GIVEN valid path to missing file
        WHEN load is called
        THEN raises ConfigError
        """
        with pytest.raises(ConfigError, match="Config not found"):
            ConfigLoader.from_yaml(Path("non_existent.yaml"))

    def test_load_valid_yaml(self, tmp_path):
        """
        GIVEN valid YAML file
        WHEN loaded
        THEN returns SoniConfig object
        """
        # Arrange
        config_file = tmp_path / "soni.yaml"
        yaml_content = """
        version: "1.0"
        flows:
          book_flight:
            description: "Book a flight"
            steps:
              - step: collect_origin
                type: collect
                slot: origin
        """
        config_file.write_text(yaml_content)

        # Act
        config = ConfigLoader.from_yaml(config_file)

        # Assert
        assert config.version == "1.0"
        assert "book_flight" in config.flows
        assert config.flows["book_flight"].description == "Book a flight"
        assert config.flows["book_flight"].steps[0].slot == "origin"
