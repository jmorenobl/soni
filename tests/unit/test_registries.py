"""Tests for Action and Validator Registries"""

import pytest

from soni.actions.registry import ActionRegistry
from soni.validation.registry import ValidatorRegistry


class TestActionRegistry:
    """Tests for ActionRegistry"""

    def test_register_action(self):
        """Test registering an action"""

        # Arrange & Act
        @ActionRegistry.register("test_action")
        async def test_func(param: str) -> dict:
            return {"result": param}

        # Assert
        assert ActionRegistry.is_registered("test_action")
        action = ActionRegistry.get("test_action")
        assert action is test_func

    @pytest.mark.asyncio
    async def test_registered_action_executes(self):
        """Test that registered action can be executed"""

        # Arrange
        @ActionRegistry.register("greet")
        async def greet(name: str) -> dict:
            return {"message": f"Hello {name}"}

        # Act
        action = ActionRegistry.get("greet")
        result = await action(name="World")

        # Assert
        assert result["message"] == "Hello World"

    def test_get_nonexistent_action_raises(self):
        """Test that getting non-existent action raises ValueError"""
        # Act & Assert
        with pytest.raises(ValueError, match="Action 'nonexistent' not registered"):
            ActionRegistry.get("nonexistent")

    def test_list_actions(self):
        """Test listing all registered actions"""

        # Arrange
        @ActionRegistry.register("action1")
        def action1() -> dict:
            return {}

        @ActionRegistry.register("action2")
        def action2() -> dict:
            return {}

        # Act
        actions = ActionRegistry.list_actions()

        # Assert
        assert "action1" in actions
        assert "action2" in actions

    def test_is_registered_true(self):
        """Test is_registered returns True for registered action"""

        # Arrange
        @ActionRegistry.register("check_action")
        def check() -> dict:
            return {}

        # Act & Assert
        assert ActionRegistry.is_registered("check_action") is True

    def test_is_registered_false(self):
        """Test is_registered returns False for non-existent action"""
        # Act & Assert
        assert ActionRegistry.is_registered("not_registered") is False


class TestValidatorRegistry:
    """Tests for ValidatorRegistry"""

    def test_register_validator(self):
        """Test registering a validator"""

        # Arrange & Act
        @ValidatorRegistry.register("test_validator")
        def test_func(value: str) -> bool:
            return len(value) > 5

        # Assert
        validator = ValidatorRegistry.get("test_validator")
        assert validator is test_func

    def test_validator_execution(self):
        """Test that validator can be executed"""

        # Arrange
        @ValidatorRegistry.register("length_check")
        def check_length(value: str) -> bool:
            return len(value) == 3

        # Act
        validator = ValidatorRegistry.get("length_check")

        # Assert
        assert validator("abc") is True
        assert validator("abcd") is False

    def test_validate_method(self):
        """Test validate helper method"""

        # Arrange
        @ValidatorRegistry.register("positive_number")
        def check_positive(value: int) -> bool:
            return value > 0

        # Act & Assert
        assert ValidatorRegistry.validate("positive_number", 5) is True
        assert ValidatorRegistry.validate("positive_number", -1) is False

    def test_get_nonexistent_validator_raises(self):
        """Test that getting non-existent validator raises ValueError"""
        # Act & Assert
        with pytest.raises(ValueError, match="Validator 'nonexistent' not registered"):
            ValidatorRegistry.get("nonexistent")

    def test_list_validators(self):
        """Test listing all registered validators"""

        # Arrange
        @ValidatorRegistry.register("validator1")
        def validator1(value) -> bool:
            return True

        @ValidatorRegistry.register("validator2")
        def validator2(value) -> bool:
            return True

        # Act
        validators = ValidatorRegistry.list_validators()

        # Assert
        assert "validator1" in validators
        assert "validator2" in validators
