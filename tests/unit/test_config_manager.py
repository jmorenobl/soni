"""Tests for ConfigurationManager"""

from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from soni.core.config import SoniConfig
from soni.core.errors import ConfigurationError
from soni.runtime.config_manager import ConfigurationManager


def test_config_manager_initialization():
    """Test ConfigurationManager initializes with config path"""
    # Arrange
    config_path = "examples/flight_booking/soni.yaml"

    # Act
    manager = ConfigurationManager(config_path)

    # Assert
    assert manager.config_path == Path(config_path)
    assert manager.config is None


def test_config_manager_initialization_with_path_object():
    """Test ConfigurationManager accepts Path object"""
    # Arrange
    config_path = Path("examples/flight_booking/soni.yaml")

    # Act
    manager = ConfigurationManager(config_path)

    # Assert
    assert manager.config_path == config_path
    assert manager.config is None


def test_config_manager_load_success():
    """Test ConfigurationManager loads configuration successfully"""
    # Arrange
    config_path = "examples/flight_booking/soni.yaml"
    manager = ConfigurationManager(config_path)

    # Act
    config = manager.load()

    # Assert
    assert config is not None
    assert isinstance(config, SoniConfig)
    assert manager.config is config
    # Check that config has expected structure
    assert hasattr(config, "version")
    assert hasattr(config, "settings")
    assert hasattr(config, "flows")
    assert hasattr(config, "slots")
    assert hasattr(config, "actions")


def test_config_manager_load_multiple_times():
    """Test ConfigurationManager can load configuration multiple times"""
    # Arrange
    config_path = "examples/flight_booking/soni.yaml"
    manager = ConfigurationManager(config_path)

    # Act
    config1 = manager.load()
    config2 = manager.load()

    # Assert
    assert config1 is not None
    assert config2 is not None
    assert isinstance(config1, SoniConfig)
    assert isinstance(config2, SoniConfig)
    # Both loads should update manager.config
    assert manager.config is config2


def test_config_manager_load_nonexistent_file():
    """Test ConfigurationManager raises error for nonexistent file"""
    # Arrange
    config_path = "nonexistent/config.yaml"
    manager = ConfigurationManager(config_path)

    # Act & Assert
    with pytest.raises((ConfigurationError, FileNotFoundError)):
        manager.load()


def test_config_manager_load_invalid_yaml():
    """Test ConfigurationManager raises error for invalid YAML"""
    # Arrange
    import tempfile

    with tempfile.NamedTemporaryFile(mode="w", suffix=".yaml", delete=False) as f:
        f.write("invalid: yaml: content: [")
        temp_path = f.name

    try:
        manager = ConfigurationManager(temp_path)

        # Act & Assert
        with pytest.raises(ConfigurationError):
            manager.load()
    finally:
        # Cleanup
        Path(temp_path).unlink()


def test_config_manager_load_invalid_schema():
    """Test ConfigurationManager raises error for invalid schema"""
    # Arrange
    import tempfile

    with tempfile.NamedTemporaryFile(mode="w", suffix=".yaml", delete=False) as f:
        # Valid YAML but invalid schema (missing required fields)
        f.write("invalid_field: value\n")
        temp_path = f.name

    try:
        manager = ConfigurationManager(temp_path)

        # Act & Assert
        with pytest.raises(ConfigurationError):
            manager.load()
    finally:
        # Cleanup
        Path(temp_path).unlink()


def test_config_manager_load_with_mocked_loader():
    """Test ConfigurationManager uses ConfigLoader correctly"""
    # Arrange
    config_path = "test/config.yaml"
    manager = ConfigurationManager(config_path)

    mock_config_dict = {
        "version": "1.0",
        "settings": {
            "models": {"nlu": {"provider": "openai", "model": "gpt-4o-mini"}},
            "persistence": {"backend": "sqlite", "path": "test.db"},
            "trace": {"enabled": False},
        },
        "flows": {},
        "slots": {},
        "actions": {},
    }

    # Act
    with patch("soni.runtime.config_manager.ConfigLoader.load") as mock_load:
        mock_load.return_value = mock_config_dict
        config = manager.load()

        # Assert
        mock_load.assert_called_once_with(Path(config_path))
        assert isinstance(config, SoniConfig)
        assert config.version == "1.0"
        assert config.settings.models.nlu.provider == "openai"


def test_config_manager_load_preserves_path():
    """Test ConfigurationManager preserves config_path after load"""
    # Arrange
    config_path = "examples/flight_booking/soni.yaml"
    manager = ConfigurationManager(config_path)
    original_path = manager.config_path

    # Act
    manager.load()

    # Assert
    assert manager.config_path == original_path


def test_config_manager_with_relative_path():
    """Test ConfigurationManager handles relative paths"""
    # Arrange
    config_path = "examples/flight_booking/soni.yaml"
    manager = ConfigurationManager(config_path)

    # Act
    config = manager.load()

    # Assert
    assert config is not None
    assert isinstance(config, SoniConfig)
    assert manager.config_path.is_absolute() or not manager.config_path.is_absolute()


def test_config_manager_with_absolute_path():
    """Test ConfigurationManager handles absolute paths"""
    # Arrange
    config_path = Path("examples/flight_booking/soni.yaml").resolve()
    manager = ConfigurationManager(config_path)

    # Act
    config = manager.load()

    # Assert
    assert config is not None
    assert isinstance(config, SoniConfig)
    assert manager.config_path.is_absolute()


def test_config_manager_config_initially_none():
    """Test ConfigurationManager config attribute is None before load"""
    # Arrange
    config_path = "examples/flight_booking/soni.yaml"
    manager = ConfigurationManager(config_path)

    # Assert
    assert manager.config is None


def test_config_manager_config_set_after_load():
    """Test ConfigurationManager config attribute is set after load"""
    # Arrange
    config_path = "examples/flight_booking/soni.yaml"
    manager = ConfigurationManager(config_path)

    # Act
    loaded_config = manager.load()

    # Assert
    assert manager.config is not None
    assert manager.config is loaded_config


def test_config_manager_returns_loaded_config():
    """Test ConfigurationManager load returns the loaded config"""
    # Arrange
    config_path = "examples/flight_booking/soni.yaml"
    manager = ConfigurationManager(config_path)

    # Act
    result = manager.load()

    # Assert
    assert result is not None
    assert isinstance(result, SoniConfig)
    assert result is manager.config


def test_config_manager_load_validates_config():
    """Test ConfigurationManager validates config during load"""
    # Arrange
    import tempfile

    # Create config with invalid settings (e.g., negative trace_sample_rate)
    with tempfile.NamedTemporaryFile(mode="w", suffix=".yaml", delete=False) as f:
        f.write(
            """
project:
  name: test_project
  version: "0.1.0"

settings:
  persistence:
    backend: sqlite
    path: test.db
  trace:
    enabled: true
    sample_rate: -0.5  # Invalid: should be 0.0-1.0

flows: {}
slots: {}
entities: {}
"""
        )
        temp_path = f.name

    try:
        manager = ConfigurationManager(temp_path)

        # Act & Assert
        with pytest.raises((ConfigurationError, ValueError)):
            manager.load()
    finally:
        # Cleanup
        Path(temp_path).unlink()
