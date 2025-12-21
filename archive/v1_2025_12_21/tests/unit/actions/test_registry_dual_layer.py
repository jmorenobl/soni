"""Tests for ActionRegistry dual-layer behavior.

Tests global vs local action precedence and isolation.
"""

import pytest

from soni.actions.registry import ActionRegistry


class TestActionRegistryDualLayer:
    """Tests for global + local action registration."""

    @pytest.fixture(autouse=True)
    def cleanup(self):
        """Clear registry before and after each test."""
        ActionRegistry.clear_global()
        yield
        ActionRegistry.clear_global()

    def test_local_takes_precedence_over_global(self):
        """Test that local action overrides global with same name."""

        # Register global
        @ActionRegistry.register("shared_action")
        def global_action(**kwargs) -> dict:
            return {"source": "global"}

        # Create instance and register local
        registry = ActionRegistry()
        registry.register_local("shared_action", lambda **kwargs: {"source": "local"})

        # Get should return local
        action = registry.get("shared_action")
        result = action()

        assert result["source"] == "local"

    def test_global_available_without_local(self):
        """Test that global actions are available when no local override."""

        @ActionRegistry.register("global_only")
        def global_action(**kwargs) -> dict:
            return {"global": True}

        registry = ActionRegistry()
        action = registry.get("global_only")

        assert action is not None
        assert action()["global"] is True

    def test_local_not_available_in_other_instances(self):
        """Test that local actions are instance-specific."""
        registry1 = ActionRegistry()
        registry2 = ActionRegistry()

        registry1.register_local("instance_action", lambda **k: {"instance": 1})

        assert registry1.get("instance_action") is not None
        assert registry2.get("instance_action") is None

    def test_clear_local_does_not_affect_global(self):
        """Test that clearing local doesn't affect global actions."""

        @ActionRegistry.register("persistent")
        def global_action(**kwargs) -> dict:
            return {}

        registry = ActionRegistry()
        registry.register_local("temporary", lambda **k: {})

        registry.clear_local()

        assert registry.get("persistent") is not None
        assert registry.get("temporary") is None

    def test_clear_global_affects_all_instances(self):
        """Test that clearing global affects all registry instances."""

        @ActionRegistry.register("shared")
        def global_action(**kwargs) -> dict:
            return {}

        registry1 = ActionRegistry()
        registry2 = ActionRegistry()

        assert registry1.get("shared") is not None
        assert registry2.get("shared") is not None

        ActionRegistry.clear_global()

        assert registry1.get("shared") is None
        assert registry2.get("shared") is None

    def test_list_actions_shows_both_layers(self):
        """Test that list_actions shows global and local separately."""

        @ActionRegistry.register("global_a")
        def ga(**k):
            return {}

        @ActionRegistry.register("global_b")
        def gb(**k):
            return {}

        registry = ActionRegistry()
        registry.register_local("local_x", lambda **k: {})

        actions = registry.list_actions()

        assert "global_a" in actions["global"]
        assert "global_b" in actions["global"]
        assert "local_x" in actions["local"]
        assert "local_x" not in actions["global"]

    def test_has_checks_both_layers(self):
        """Test that has() checks both global and local."""

        @ActionRegistry.register("global_action")
        def ga(**k):
            return {}

        registry = ActionRegistry()
        registry.register_local("local_action", lambda **k: {})

        assert registry.has("global_action") is True
        assert registry.has("local_action") is True
        assert registry.has("nonexistent") is False
