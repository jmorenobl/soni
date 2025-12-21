"""Tests for ActionRegistry and Handler."""

import pytest
from soni.actions.handler import ActionHandler
from soni.actions.registry import ActionRegistry

from soni.core.errors import ActionError


class TestActionRegistry:
    @pytest.fixture(autouse=True)
    def clear_registry(self):
        ActionRegistry.clear()
        yield
        ActionRegistry.clear()

    def test_register_and_get(self):
        """
        GIVEN an action registry
        WHEN an action is registered
        THEN it can be retrieved by name and appears in list
        """
        # Arrange
        registry = ActionRegistry()

        async def my_action(x: int):
            return {"result": x * 2}

        # Act
        registry.register("double")(my_action)

        # Assert
        assert registry.get("double") == my_action
        assert "double" in registry.list()

    def test_decorator_syntax(self):
        """
        GIVEN an action registry
        WHEN using decorator syntax to register
        THEN action is registered correctly
        """
        # Arrange
        registry = ActionRegistry()

        # Act
        @registry.register("square")
        async def square(x: int):
            return {"result": x * x}

        # Assert
        assert registry.get("square") == square


class TestActionHandler:
    @pytest.mark.asyncio
    async def test_execute_action(self):
        """
        GIVEN a registered action
        WHEN executed with valid inputs
        THEN returns expected result
        """
        # Arrange
        registry = ActionRegistry()

        @registry.register("add")
        async def add(a: int, b: int):
            return {"sum": a + b}

        handler = ActionHandler(registry)

        # Act
        result = await handler.execute("add", {"a": 1, "b": 2})

        # Assert
        assert result["sum"] == 3

    @pytest.mark.asyncio
    async def test_execute_missing_action(self):
        """
        GIVEN an action handler
        WHEN executing a non-existent action
        THEN raises ActionError with 'not found' message
        """
        # Arrange
        registry = ActionRegistry()
        handler = ActionHandler(registry)

        # Act & Assert
        with pytest.raises(ActionError, match="Action 'unknown' not found"):
            await handler.execute("unknown", {})

    @pytest.mark.asyncio
    async def test_execute_missing_inputs(self):
        """
        GIVEN an action requiring inputs
        WHEN executed without required inputs
        THEN raises ActionError with 'missing inputs' message
        """
        # Arrange
        registry = ActionRegistry()

        @registry.register("greet")
        async def greet(name: str):
            return {}

        handler = ActionHandler(registry)

        # Act & Assert
        with pytest.raises(ActionError, match="missing inputs"):
            await handler.execute("greet", {})

    @pytest.mark.asyncio
    async def test_execute_runtime_error(self):
        """
        GIVEN an action that raises an exception
        WHEN executed
        THEN raises ActionError with 'execution failed' message
        """
        # Arrange
        registry = ActionRegistry()

        @registry.register("fail")
        async def fail():
            raise ValueError("Boom")

        handler = ActionHandler(registry)

        # Act & Assert
        with pytest.raises(ActionError, match="execution failed"):
            await handler.execute("fail", {})
