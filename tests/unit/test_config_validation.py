"""Tests for configuration validation."""

from pathlib import Path

import pytest
from pydantic import ValidationError

from soni.core.config import ConfigLoader, SoniConfig
from soni.core.errors import ConfigurationError


def test_load_config_valid(tmp_path):
    """Test loading valid configuration."""
    # Arrange
    config_file = tmp_path / "config.yaml"
    config_file.write_text(
        """
version: "1.0"
settings:
  models:
    nlu:
      provider: openai
      model: gpt-4o-mini
      temperature: 0.0
flows: {}
slots: {}
actions: {}
"""
    )

    # Act
    config = SoniConfig.from_yaml(config_file)

    # Assert
    assert config.version == "1.0"
    assert config.settings.models.nlu.model == "gpt-4o-mini"


def test_load_config_invalid_temperature_raises(tmp_path):
    """Test invalid configuration raises error."""
    # Arrange
    config_file = tmp_path / "config.yaml"
    config_file.write_text(
        """
version: "1.0"
settings:
  models:
    nlu:
      provider: openai
      model: gpt-4o-mini
      temperature: -1.0  # Invalid: negative temperature
flows: {}
slots: {}
actions: {}
"""
    )

    # Act & Assert
    with pytest.raises(ValidationError):
        SoniConfig.from_yaml(config_file)


def test_load_config_missing_file():
    """Test loading non-existent file raises error."""
    # Arrange
    non_existent = Path("/non/existent/config.yaml")

    # Act & Assert
    with pytest.raises(ConfigurationError):
        ConfigLoader.load(non_existent)


def test_config_default_values():
    """Test configuration has appropriate default values."""
    # Arrange & Act
    config = SoniConfig(
        version="1.0",
        settings={
            "models": {
                "nlu": {
                    "provider": "openai",
                    "model": "gpt-4o-mini",
                }
            }
        },
        flows={},
        slots={},
        actions={},
    )

    # Assert
    assert config.settings.persistence.backend == "sqlite"
    assert config.settings.logging.level == "INFO"


def test_config_validation_error_messages(tmp_path):
    """Test configuration validation provides clear error messages."""
    # Arrange
    config_file = tmp_path / "config.yaml"
    config_file.write_text(
        """
version: "1.0"
settings:
  models:
    nlu:
      provider: openai
      model: gpt-4o-mini
      temperature: 3.0  # Invalid: > 2.0
flows: {}
slots: {}
actions: {}
"""
    )

    # Act & Assert
    with pytest.raises(ValidationError) as exc_info:
        SoniConfig.from_yaml(config_file)

    # Assert error message is helpful
    assert exc_info.value is not None
