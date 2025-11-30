"""Tests for StepParser"""

import pytest

from soni.compiler.parser import ParsedStep, StepParser
from soni.core.config import StepConfig
from soni.core.errors import CompilationError


def test_parser_validates_collect_step():
    """Test parser validates collect step correctly"""
    # Arrange
    parser = StepParser()
    steps = [StepConfig(step="get_dest", type="collect", slot="destination")]

    # Act
    parsed = parser.parse(steps)

    # Assert
    assert len(parsed) == 1
    assert parsed[0].step_id == "get_dest"
    assert parsed[0].step_type == "collect"
    assert parsed[0].config["slot_name"] == "destination"


def test_parser_validates_action_step():
    """Test parser validates action step correctly"""
    # Arrange
    parser = StepParser()
    steps = [
        StepConfig(
            step="search",
            type="action",
            call="search_flights",
            map_outputs={"flights": "api_flights"},
        )
    ]

    # Act
    parsed = parser.parse(steps)

    # Assert
    assert len(parsed) == 1
    assert parsed[0].step_id == "search"
    assert parsed[0].step_type == "action"
    assert parsed[0].config["action_name"] == "search_flights"
    assert parsed[0].config["map_outputs"] == {"flights": "api_flights"}


def test_parser_rejects_empty_step_id():
    """Test parser rejects step with empty step identifier"""
    # Arrange
    parser = StepParser()
    steps = [StepConfig(step="", type="collect", slot="destination")]

    # Act & Assert
    with pytest.raises(CompilationError) as exc_info:
        parser.parse(steps)

    assert "non-empty 'step' identifier" in str(exc_info.value)
    assert exc_info.value.step_index == 1
    assert exc_info.value.step_name == ""


def test_parser_rejects_missing_type():
    """Test parser rejects step without type"""
    # Arrange
    parser = StepParser()
    steps = [StepConfig(step="get_dest", type="", slot="destination")]

    # Act & Assert
    with pytest.raises(CompilationError) as exc_info:
        parser.parse(steps)

    assert "must specify a 'type'" in str(exc_info.value)
    assert exc_info.value.step_index == 1
    assert exc_info.value.step_name == "get_dest"


def test_parser_rejects_unsupported_type():
    """Test parser rejects unsupported step type"""
    # Arrange
    parser = StepParser()
    steps = [StepConfig(step="invalid_step", type="invalid_type", slot=None)]

    # Act & Assert
    with pytest.raises(CompilationError) as exc_info:
        parser.parse(steps)

    assert "Unsupported step type 'invalid_type'" in str(exc_info.value)
    assert exc_info.value.step_index == 1
    assert exc_info.value.step_name == "invalid_step"


def test_parser_rejects_collect_without_slot():
    """Test parser rejects collect step without slot"""
    # Arrange
    parser = StepParser()
    steps = [StepConfig(step="get_dest", type="collect", slot=None)]

    # Act & Assert
    with pytest.raises(CompilationError) as exc_info:
        parser.parse(steps)

    assert "must specify a 'slot'" in str(exc_info.value)
    assert exc_info.value.step_index == 1
    assert exc_info.value.step_name == "get_dest"


def test_parser_rejects_action_without_call():
    """Test parser rejects action step without call"""
    # Arrange
    parser = StepParser()
    steps = [StepConfig(step="search", type="action", call=None)]

    # Act & Assert
    with pytest.raises(CompilationError) as exc_info:
        parser.parse(steps)

    assert "must specify a 'call'" in str(exc_info.value)
    assert exc_info.value.step_index == 1
    assert exc_info.value.step_name == "search"


def test_parser_handles_multiple_steps():
    """Test parser handles multiple valid steps"""
    # Arrange
    parser = StepParser()
    steps = [
        StepConfig(step="get_origin", type="collect", slot="origin"),
        StepConfig(step="get_dest", type="collect", slot="destination"),
        StepConfig(step="search", type="action", call="search_flights"),
    ]

    # Act
    parsed = parser.parse(steps)

    # Assert
    assert len(parsed) == 3
    assert parsed[0].step_id == "get_origin"
    assert parsed[1].step_id == "get_dest"
    assert parsed[2].step_id == "search"


def test_parser_error_includes_step_index():
    """Test parser error includes step index for debugging"""
    # Arrange
    parser = StepParser()
    steps = [
        StepConfig(step="valid", type="collect", slot="origin"),
        StepConfig(step="invalid", type="collect", slot=None),  # Missing slot
    ]

    # Act & Assert
    with pytest.raises(CompilationError) as exc_info:
        parser.parse(steps)

    assert "step 2" in str(exc_info.value).lower()
    assert "'invalid'" in str(exc_info.value)
    assert exc_info.value.step_index == 2
    assert exc_info.value.step_name == "invalid"


def test_parser_handles_action_without_map_outputs():
    """Test parser handles action step without map_outputs"""
    # Arrange
    parser = StepParser()
    steps = [StepConfig(step="search", type="action", call="search_flights", map_outputs=None)]

    # Act
    parsed = parser.parse(steps)

    # Assert
    assert len(parsed) == 1
    assert parsed[0].step_id == "search"
    assert parsed[0].step_type == "action"
    assert "map_outputs" not in parsed[0].config


def test_parser_handles_empty_steps_list():
    """Test parser handles empty steps list"""
    # Arrange
    parser = StepParser()
    steps: list[StepConfig] = []

    # Act
    parsed = parser.parse(steps)

    # Assert
    assert len(parsed) == 0
