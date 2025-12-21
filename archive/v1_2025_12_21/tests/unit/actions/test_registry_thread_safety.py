"""Tests for ActionRegistry thread safety.

Verifies that concurrent registration and access operations are safe.
"""

import threading
import time
from concurrent.futures import ThreadPoolExecutor, as_completed

import pytest
from soni.actions.registry import ActionRegistry


class TestActionRegistryThreadSafety:
    """Tests for thread-safe ActionRegistry operations."""

    @pytest.fixture(autouse=True)
    def cleanup(self):
        """Clear global registry before and after each test."""
        ActionRegistry.clear_global()
        yield
        ActionRegistry.clear_global()

    def test_concurrent_global_registration(self):
        """Test that concurrent global registrations don't corrupt state."""
        num_threads = 10
        actions_per_thread = 100

        def register_actions(thread_id: int) -> list[str]:
            registered = []
            for i in range(actions_per_thread):
                name = f"action_{thread_id}_{i}"

                @ActionRegistry.register(name)
                def action(_i=i, **kwargs) -> dict:
                    return {"thread": thread_id, "index": _i}

                registered.append(name)
            return registered

        # Run concurrent registrations
        with ThreadPoolExecutor(max_workers=num_threads) as executor:
            futures = [executor.submit(register_actions, i) for i in range(num_threads)]
            all_registered = []
            for future in as_completed(futures):
                all_registered.extend(future.result())

        # Verify all actions were registered
        registry = ActionRegistry()
        for name in all_registered:
            assert registry.get(name) is not None, f"Action {name} not found"

        # Verify count
        expected_count = num_threads * actions_per_thread
        actions = registry.list_actions()
        assert len(actions["global"]) == expected_count

    def test_concurrent_local_registration(self):
        """Test that concurrent local registrations on same instance are safe."""
        registry = ActionRegistry()
        num_threads = 10
        actions_per_thread = 50

        def register_local_actions(thread_id: int) -> list[str]:
            registered = []
            for i in range(actions_per_thread):
                name = f"local_{thread_id}_{i}"

                def action(_i=i, **kwargs) -> dict:
                    return {"thread": thread_id, "index": _i}

                registry.register_local(name, action)
                registered.append(name)
            return registered

        with ThreadPoolExecutor(max_workers=num_threads) as executor:
            futures = [executor.submit(register_local_actions, i) for i in range(num_threads)]
            all_registered = []
            for future in as_completed(futures):
                all_registered.extend(future.result())

        # Verify all actions
        for name in all_registered:
            assert registry.get(name) is not None, f"Local action {name} not found"

    def test_concurrent_read_write(self):
        """Test concurrent reads and writes don't deadlock or corrupt."""
        registry = ActionRegistry()
        stop_event = threading.Event()
        errors = []

        # Pre-register some actions
        for i in range(10):

            @ActionRegistry.register(f"preset_{i}")
            def preset_action(_i=i, **kwargs) -> dict:
                return {"preset": _i}

        def reader():
            """Continuously read actions."""
            while not stop_event.is_set():
                try:
                    for i in range(10):
                        _ = registry.get(f"preset_{i}")
                    _ = registry.list_actions()
                except Exception as e:
                    errors.append(f"Reader error: {e}")

        def writer(thread_id: int):
            """Continuously write new actions."""
            count = 0
            while not stop_event.is_set():
                try:
                    name = f"dynamic_{thread_id}_{count}"
                    registry.register_local(name, lambda **kwargs: {})
                    count += 1
                    time.sleep(0.001)
                except Exception as e:
                    errors.append(f"Writer {thread_id} error: {e}")

        # Start readers and writers
        threads = []
        for _ in range(3):
            threads.append(threading.Thread(target=reader))
        for i in range(2):
            threads.append(threading.Thread(target=writer, args=(i,)))

        for t in threads:
            t.start()

        # Let them run
        time.sleep(0.5)
        stop_event.set()

        for t in threads:
            t.join(timeout=2)

        assert len(errors) == 0, f"Errors during concurrent access: {errors}"

    def test_duplicate_registration_logs_warning(self, caplog):
        """Test that overwriting an action logs a warning."""
        import logging

        with caplog.at_level(logging.WARNING):

            @ActionRegistry.register("duplicate_test")
            def first_action(**kwargs) -> dict:
                return {"first": True}

            @ActionRegistry.register("duplicate_test")
            def second_action(**kwargs) -> dict:
                return {"second": True}

        # Check warning was logged
        assert "Overwriting" in caplog.text
        assert "duplicate_test" in caplog.text

    def test_clear_global_is_atomic(self):
        """Test that clear_global is atomic and doesn't interfere with reads."""
        # Register actions
        for i in range(100):

            @ActionRegistry.register(f"clear_test_{i}")
            def action(**kwargs) -> dict:
                return {}

        registry = ActionRegistry()
        errors = []

        def reader():
            for _ in range(1000):
                try:
                    actions = registry.list_actions()
                    # Should either have 0 or 100 actions, never partial
                    count = len(actions["global"])
                    if count not in [0, 100] and "clear_test" in str(actions):
                        errors.append(f"Partial state detected: {count} actions")
                except Exception as e:
                    errors.append(f"Reader error: {e}")

        def clearer():
            time.sleep(0.01)
            ActionRegistry.clear_global()

        threads = [
            threading.Thread(target=reader),
            threading.Thread(target=clearer),
        ]

        for t in threads:
            t.start()
        for t in threads:
            t.join()

        assert len(errors) == 0, f"Errors: {errors}"

    def test_list_actions_returns_correct_structure(self):
        """Test that list_actions returns dict with global and local keys."""
        registry = ActionRegistry()

        # Register some actions
        @ActionRegistry.register("global_action")
        def global_action(**kwargs) -> dict:
            return {}

        registry.register_local("local_action", lambda **kwargs: {})

        actions = registry.list_actions()

        assert isinstance(actions, dict)
        assert "global" in actions
        assert "local" in actions
        assert isinstance(actions["global"], list)
        assert isinstance(actions["local"], list)
        assert "global_action" in actions["global"]
        assert "local_action" in actions["local"]
