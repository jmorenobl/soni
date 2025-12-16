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
        registry = ActionRegistry()

        async def my_action(x: int):
            return {"result": x * 2}

        registry.register("double")(my_action)

        assert registry.get("double") == my_action
        assert "double" in registry.list()

    def test_decorator_syntax(self):
        registry = ActionRegistry()

        @registry.register("square")
        async def square(x: int):
            return {"result": x * x}

        assert registry.get("square") == square


class TestActionHandler:
    @pytest.mark.asyncio
    async def test_execute_action(self):
        registry = ActionRegistry()

        @registry.register("add")
        async def add(a: int, b: int):
            return {"sum": a + b}

        handler = ActionHandler(registry)
        result = await handler.execute("add", {"a": 1, "b": 2})
        assert result["sum"] == 3

    @pytest.mark.asyncio
    async def test_execute_missing_action(self):
        registry = ActionRegistry()
        handler = ActionHandler(registry)

        with pytest.raises(ActionError, match="Action 'unknown' not found"):
            await handler.execute("unknown", {})

    @pytest.mark.asyncio
    async def test_execute_missing_inputs(self):
        registry = ActionRegistry()

        @registry.register("greet")
        async def greet(name: str):
            return {}

        handler = ActionHandler(registry)
        with pytest.raises(ActionError, match="missing inputs"):
            await handler.execute("greet", {})

    @pytest.mark.asyncio
    async def test_execute_runtime_error(self):
        registry = ActionRegistry()

        @registry.register("fail")
        async def fail():
            raise ValueError("Boom")

        handler = ActionHandler(registry)
        with pytest.raises(ActionError, match="execution failed"):
            await handler.execute("fail", {})
