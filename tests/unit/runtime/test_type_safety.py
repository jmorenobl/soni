"""Tests for type safety in runtime components."""

import inspect
import subprocess
import sys
from typing import Any, cast
from unittest.mock import MagicMock

import pytest


class TestNoTypeIgnore:
    """Verify no type: ignore comments in source."""

    def test_no_type_ignore_in_hydrator(self) -> None:
        """Verify hydrator.py has no type: ignore."""
        import soni.runtime.hydrator as module

        source = inspect.getsource(module)
        assert "type: ignore" not in source

    def test_no_type_ignore_in_loop(self) -> None:
        """Verify loop.py has no type: ignore."""
        import soni.runtime.loop as module

        source = inspect.getsource(module)
        assert "type: ignore" not in source


class TestSettersRemoved:
    """Verify setters have been removed."""

    def test_runtime_loop_has_no_du_setter(self) -> None:
        """Verify RuntimeLoop.du is read-only."""
        from soni.runtime.loop import RuntimeLoop

        config = MagicMock()
        runtime = RuntimeLoop(config)

        with pytest.raises(AttributeError):
            runtime.du = MagicMock()  # type: ignore[misc]

    def test_runtime_loop_has_no_flow_manager_setter(self) -> None:
        """Verify RuntimeLoop.flow_manager is read-only."""
        from soni.runtime.loop import RuntimeLoop

        config = MagicMock()
        runtime = RuntimeLoop(config)

        with pytest.raises(AttributeError):
            runtime.flow_manager = MagicMock()  # type: ignore[misc]


class TestConstructorInjection:
    """Verify constructor injection works."""

    def test_du_can_be_injected_via_constructor(self) -> None:
        """Verify du can be passed to constructor."""
        from soni.runtime.loop import RuntimeLoop

        config = MagicMock()
        config.flows = {}
        mock_du = MagicMock()

        runtime = RuntimeLoop(config, du=mock_du)

        # After initialize, the injected du should be used
        # (This test may need adjustment based on actual behavior)
        # Note: initialize must be called or internal check must confirm storage
        # Access internal structure to verify it was stored in initializer config
        assert runtime._initializer._custom_du is mock_du


class TestHydratorTypeSafety:
    """Tests for StateHydrator type correctness."""

    def test_prepare_input_returns_valid_type(self) -> None:
        """Test prepare_input return type."""
        from soni.runtime.hydrator import StateHydrator

        hydrator = StateHydrator()

        # New conversation
        result = hydrator.prepare_input("Hello", None)
        assert "user_message" in result
        assert "flow_stack" in result

        # Existing conversation
        result2 = hydrator.prepare_input("Hi again", {"turn_count": 1})
        assert result2["turn_count"] == 2


class TestMypyCompliance:
    """Verify mypy passes on modified files."""

    def test_mypy_passes_on_hydrator(self) -> None:
        """Run mypy on hydrator.py."""
        result = subprocess.run(
            [sys.executable, "-m", "mypy", "src/soni/runtime/hydrator.py", "--strict"],
            capture_output=True,
            text=True,
        )
        assert result.returncode == 0, f"mypy failed:\n{result.stdout}\n{result.stderr}"

    def test_mypy_passes_on_loop(self) -> None:
        """Run mypy on loop.py."""
        # Using strict might be too aggressive for now if many deps are missing types,
        # but we should aim for cleans run.
        result = subprocess.run(
            [sys.executable, "-m", "mypy", "src/soni/runtime/loop.py", "--strict"],
            capture_output=True,
            text=True,
        )
        assert result.returncode == 0, f"mypy failed:\n{result.stdout}\n{result.stderr}"
