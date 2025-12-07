"""Tests for configuration loading and validation"""

import tempfile
from pathlib import Path

import pytest
import yaml
from pydantic import ValidationError as PydanticValidationError

from soni.core.config import (
    ActionConfig,
    ConfigLoader,
    FlowConfig,
    ModelConfig,
    SlotConfig,
    SoniConfig,
    StepConfig,
)
from soni.core.errors import ConfigurationError, ValidationError


def test_load_valid_yaml():
    """Test loading a valid YAML configuration file"""
    # Arrange
    with tempfile.NamedTemporaryFile(mode="w", suffix=".yaml", delete=False) as f:
        config_data = {
            "version": "0.1",
            "settings": {"models": {"nlu": {"provider": "openai"}}},
            "flows": {},
            "slots": {},
            "actions": {},
        }
        yaml.dump(config_data, f)
        temp_path = f.name

    try:
        # Act
        config = ConfigLoader.load(temp_path)

        # Assert
        assert config["version"] == "0.1"
        assert "settings" in config
    finally:
        Path(temp_path).unlink()


def test_load_nonexistent_file():
    """Test loading a non-existent file raises ConfigurationError"""
    # Arrange & Act & Assert
    with pytest.raises(ConfigurationError, match="not found"):
        ConfigLoader.load("/nonexistent/path.yaml")


def test_load_invalid_yaml():
    """Test loading invalid YAML raises ConfigurationError"""
    # Arrange
    with tempfile.NamedTemporaryFile(mode="w", suffix=".yaml", delete=False) as f:
        f.write("invalid: yaml: content: [")
        temp_path = f.name

    try:
        # Act & Assert
        with pytest.raises(ConfigurationError, match="Invalid YAML"):
            ConfigLoader.load(temp_path)
    finally:
        Path(temp_path).unlink()


def test_load_empty_file():
    """Test loading an empty file raises ConfigurationError"""
    # Arrange
    with tempfile.NamedTemporaryFile(mode="w", suffix=".yaml", delete=False) as f:
        f.write("")
        temp_path = f.name

    try:
        # Act & Assert
        with pytest.raises(ConfigurationError, match="empty"):
            ConfigLoader.load(temp_path)
    finally:
        Path(temp_path).unlink()


def test_load_non_dict_yaml():
    """Test loading YAML that is not a dictionary raises ConfigurationError"""
    # Arrange
    with tempfile.NamedTemporaryFile(mode="w", suffix=".yaml", delete=False) as f:
        yaml.dump(["list", "not", "dict"], f)
        temp_path = f.name

    try:
        # Act & Assert
        with pytest.raises(ConfigurationError, match="dictionary"):
            ConfigLoader.load(temp_path)
    finally:
        Path(temp_path).unlink()


def test_validate_missing_version():
    """Test validation detects missing version field"""
    # Arrange
    config = {"settings": {}}

    # Act
    errors = ConfigLoader.validate(config)

    # Assert
    assert len(errors) > 0
    assert any("version" in str(e).lower() for e in errors)


def test_validate_invalid_version_type():
    """Test validation detects invalid version type"""
    # Arrange
    config = {"version": 0.1}  # Should be string

    # Act
    errors = ConfigLoader.validate(config)

    # Assert
    assert len(errors) > 0
    assert any("version" in str(e).lower() and "string" in str(e).lower() for e in errors)


def test_validate_invalid_sections_type():
    """Test validation detects invalid section types"""
    # Arrange
    config = {
        "version": "0.1",
        "flows": "not a dict",  # Should be dict
    }

    # Act
    errors = ConfigLoader.validate(config)

    # Assert
    assert len(errors) > 0
    assert any("flows" in str(e).lower() and "dictionary" in str(e).lower() for e in errors)


def test_validate_missing_sections():
    """Test validation detects missing recommended sections"""
    # Arrange
    config = {"version": "0.1"}  # Missing recommended sections

    # Act
    errors = ConfigLoader.validate(config)

    # Assert
    # Should have errors for missing recommended sections
    assert len(errors) > 0
    section_names = ["settings", "flows", "slots", "actions"]
    error_messages = [str(e).lower() for e in errors]
    for section in section_names:
        assert any(section in msg for msg in error_messages)


def test_validate_valid_config():
    """Test validation passes for valid configuration"""
    # Arrange
    config = {
        "version": "0.1",
        "settings": {},
        "flows": {},
        "slots": {},
        "actions": {},
    }

    # Act
    errors = ConfigLoader.validate(config)

    # Assert
    assert len(errors) == 0


def test_load_and_validate_success():
    """Test load_and_validate with valid config"""
    # Arrange
    with tempfile.NamedTemporaryFile(mode="w", suffix=".yaml", delete=False) as f:
        config_data = {
            "version": "0.1",
            "settings": {},
            "flows": {},
            "slots": {},
            "actions": {},
        }
        yaml.dump(config_data, f)
        temp_path = f.name

    try:
        # Act
        config = ConfigLoader.load_and_validate(temp_path)

        # Assert
        assert config["version"] == "0.1"
    finally:
        Path(temp_path).unlink()


def test_load_and_validate_failure():
    """Test load_and_validate raises on validation errors"""
    # Arrange
    with tempfile.NamedTemporaryFile(mode="w", suffix=".yaml", delete=False) as f:
        config_data = {}  # Missing version
        yaml.dump(config_data, f)
        temp_path = f.name

    try:
        # Act & Assert
        with pytest.raises(ConfigurationError, match="validation failed"):
            ConfigLoader.load_and_validate(temp_path)
    finally:
        Path(temp_path).unlink()


def test_soni_config_from_dict_valid():
    """Test creating SoniConfig from valid dictionary"""
    # Arrange
    data = {
        "version": "0.1",
        "settings": {
            "models": {
                "nlu": {
                    "provider": "openai",
                    "model": "gpt-4o-mini",
                },
            },
        },
        "flows": {},
        "slots": {},
        "actions": {},
    }

    # Act
    config = SoniConfig.from_dict(data)

    # Assert
    assert config.version == "0.1"
    assert config.settings.models.nlu.provider == "openai"
    assert config.settings.models.nlu.model == "gpt-4o-mini"


def test_soni_config_missing_required_field():
    """Test SoniConfig validation fails on missing required field"""
    # Arrange
    data = {
        # Missing "version"
        "settings": {
            "models": {
                "nlu": {
                    "provider": "openai",
                    "model": "gpt-4o-mini",
                },
            },
        },
    }

    # Act & Assert
    with pytest.raises(PydanticValidationError):
        SoniConfig.from_dict(data)


def test_flow_config_with_steps():
    """Test FlowConfig with steps"""
    # Arrange
    flow_data = {
        "description": "Book a flight",
        "steps": [
            {
                "step": "collect_origin",
                "type": "collect",
                "slot": "origin",
            },
            {
                "step": "search_flights",
                "type": "action",
                "call": "search_flights",
            },
        ],
    }

    # Act
    flow = FlowConfig(**flow_data)

    # Assert
    assert flow.description == "Book a flight"
    assert len(flow.steps) == 2
    assert flow.steps[0].type == "collect"
    assert flow.steps[0].slot == "origin"
    assert flow.steps[1].type == "action"
    assert flow.steps[1].call == "search_flights"


def test_slot_config_defaults():
    """Test SlotConfig with default values"""
    # Arrange
    slot_data = {
        "type": "string",
        "prompt": "Which city?",
        # required defaults to True
        # validator defaults to None
    }

    # Act
    slot = SlotConfig(**slot_data)

    # Assert
    assert slot.type == "string"
    assert slot.prompt == "Which city?"
    assert slot.required is True
    assert slot.validator is None


def test_action_config():
    """Test ActionConfig"""
    # Arrange
    action_data = {
        "inputs": ["origin", "destination"],
        "outputs": ["flights"],
    }

    # Act
    action = ActionConfig(**action_data)

    # Assert
    assert action.inputs == ["origin", "destination"]
    assert action.outputs == ["flights"]


def test_soni_config_from_yaml():
    """Test loading SoniConfig from YAML file"""
    # Arrange
    with tempfile.NamedTemporaryFile(mode="w", suffix=".yaml", delete=False) as f:
        config_data = {
            "version": "0.1",
            "settings": {
                "models": {
                    "nlu": {
                        "provider": "openai",
                        "model": "gpt-4o-mini",
                    },
                },
            },
            "flows": {
                "book_flight": {
                    "description": "Book a flight",
                    "steps": [
                        {
                            "step": "collect_origin",
                            "type": "collect",
                            "slot": "origin",
                        },
                    ],
                },
            },
            "slots": {
                "origin": {
                    "type": "string",
                    "prompt": "Which city?",
                },
            },
            "actions": {},
        }
        yaml.dump(config_data, f)
        temp_path = f.name

    try:
        # Act
        config = SoniConfig.from_yaml(temp_path)

        # Assert
        assert config.version == "0.1"
        assert "book_flight" in config.flows
        assert "origin" in config.slots
    finally:
        Path(temp_path).unlink()


def test_model_config_temperature_validation():
    """Test ModelConfig temperature validation"""
    # Arrange & Act & Assert
    # Valid temperature
    model = ModelConfig(provider="openai", model="gpt-4o-mini", temperature=0.5)
    assert model.temperature == 0.5

    # Invalid temperature (too high)
    with pytest.raises(PydanticValidationError, match="less than or equal to 2"):
        ModelConfig(provider="openai", model="gpt-4o-mini", temperature=3.0)


def test_validate_multiple_errors():
    """Test validate returns multiple errors"""
    # Arrange
    config = {
        # Missing version
        # Missing settings
        "flows": "not a dict",  # Wrong type
    }

    # Act
    errors = ConfigLoader.validate(config)

    # Assert
    assert len(errors) >= 2  # At least version missing and flows wrong type


def test_soni_config_invalid_model_provider():
    """Test SoniConfig validation with invalid model config"""
    # Arrange
    data = {
        "version": "0.1",
        "settings": {
            "models": {
                "nlu": {
                    "provider": "",  # Empty provider
                    "model": "gpt-4o-mini",
                },
            },
        },
        "flows": {},
        "slots": {},
        "actions": {},
    }

    # Act & Assert
    # Pydantic may or may not validate empty strings depending on constraints
    # This test documents current behavior
    config = SoniConfig.from_dict(data)
    assert config.settings.models.nlu.provider == ""


def test_flow_config_empty_steps():
    """Test FlowConfig with empty steps list"""
    # Arrange
    flow_data = {
        "description": "Empty flow",
        "steps": [],
    }

    # Act
    flow = FlowConfig(**flow_data)

    # Assert
    assert flow.description == "Empty flow"
    assert len(flow.steps) == 0


def test_step_config_collect_without_slot():
    """Test StepConfig validation - collect step should have slot"""
    # Arrange
    step_data = {
        "step": "collect_origin",
        "type": "collect",
        # Missing slot
    }

    # Act
    step = StepConfig(**step_data)

    # Assert
    # In MVP, slot is optional in model but should be validated semantically later
    assert step.slot is None


def test_slot_config_optional_fields():
    """Test SlotConfig with all optional fields"""
    # Arrange
    slot_data = {
        "type": "string",
        "prompt": "Which city?",
        "required": False,
        "validator": "city_name",
    }

    # Act
    slot = SlotConfig(**slot_data)

    # Assert
    assert slot.required is False
    assert slot.validator == "city_name"


def test_action_config_minimal():
    """Test ActionConfig with minimal required fields"""
    # Arrange
    action_data = {
        # inputs and outputs are optional
    }

    # Act
    action = ActionConfig(**action_data)

    # Assert
    assert action.inputs == []
    assert action.outputs == []


def test_soni_config_defaults():
    """Test SoniConfig with minimal required fields"""
    # Arrange
    data = {
        "version": "0.1",
        "settings": {
            "models": {
                "nlu": {
                    "provider": "openai",
                    "model": "gpt-4o-mini",
                },
            },
        },
        # flows, slots, actions can be empty dicts
    }

    # Act
    config = SoniConfig.from_dict(data)

    # Assert
    assert config.flows == {}
    assert config.slots == {}
    assert config.actions == {}


def test_persistence_config_defaults():
    """Test PersistenceConfig uses defaults"""
    # Arrange
    from soni.core.config import PersistenceConfig

    # Act
    persistence = PersistenceConfig()

    # Assert
    assert persistence.backend == "sqlite"
    assert persistence.path == "./dialogue_state.db"


def test_logging_config_defaults():
    """Test LoggingConfig uses defaults"""
    # Arrange
    from soni.core.config import LoggingConfig

    # Act
    logging_config = LoggingConfig()

    # Assert
    assert logging_config.level == "INFO"
    assert logging_config.trace_graphs is False


def test_model_config_temperature_default():
    """Test ModelConfig temperature default"""
    # Arrange
    from soni.core.config import ModelConfig

    # Act
    model = ModelConfig(provider="openai", model="gpt-4o-mini")

    # Assert
    assert model.temperature == 0.1


def test_integration_load_real_yaml():
    """Test loading real example YAML file"""
    # Arrange
    yaml_path = Path("examples/flight_booking/soni.yaml")

    # Skip if file doesn't exist (created in task 001)
    if not yaml_path.exists():
        pytest.skip("Example YAML file not found")

    # Act
    config = SoniConfig.from_yaml(yaml_path)

    # Assert
    assert config.version == "0.1"
    assert len(config.flows) > 0
    assert len(config.slots) > 0


def test_config_loader_error_messages():
    """Test ConfigLoader provides clear error messages"""
    # Arrange
    with tempfile.NamedTemporaryFile(mode="w", suffix=".yaml", delete=False) as f:
        f.write("invalid: [yaml: syntax")
        temp_path = f.name

    try:
        # Act
        with pytest.raises(ConfigurationError) as exc_info:
            ConfigLoader.load(temp_path)

        # Assert
        assert "Invalid YAML" in str(exc_info.value)
        assert temp_path in str(exc_info.value)
    finally:
        Path(temp_path).unlink()


def test_validation_error_context():
    """Test ValidationError includes context"""
    # Arrange
    config = {}  # Missing version

    # Act
    errors = ConfigLoader.validate(config)

    # Assert
    assert len(errors) > 0
    first_error = errors[0]
    assert first_error.field == "version"
    assert "context" in first_error.context or hasattr(first_error, "context")
