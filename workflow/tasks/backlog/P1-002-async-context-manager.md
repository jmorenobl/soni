## Task: P1-002 - Add Async Context Manager to RuntimeLoop

**Task ID:** P1-002
**Milestone:** 2.1 - Resource Management
**Dependencies:** None
**Estimated Duration:** 3 hours

### Objective

Implement `AsyncContextManager` protocol (`__aenter__`/`__aexit__`) in `RuntimeLoop` to ensure proper resource cleanup (checkpointer connections, memory) during server lifecycle.

### Context

**Current problem:**
Resource cleanup depends on caller manually invoking `cleanup()`. If exceptions occur or server shuts down abruptly, resources may leak:

```python
# Current code (fragile)
runtime = RuntimeLoop(config)
await runtime.initialize()
try:
    # ... use runtime
finally:
    await runtime.cleanup()  # May not execute on crash
```

**Solution - Context Manager:**
```python
# Robust code
async with RuntimeLoop(config) as runtime:
    # ... use runtime
# cleanup() called automatically, even on exceptions
```

**Benefits:**
- Guaranteed cleanup even on exceptions
- Idiomatic Python resource management pattern
- Better FastAPI lifespan integration
- Prevents memory leaks and connection leaks

**SOLID principles:**
- **SRP**: RuntimeLoop already has cleanup(), we just add the protocol
- **OCP**: Extend without modifying existing logic

### Deliverables

- [ ] `RuntimeLoop.__aenter__` implemented
- [ ] `RuntimeLoop.__aexit__` implemented
- [ ] Server lifespan updated to use `async with`
- [ ] Tests verify cleanup on success and error cases
- [ ] Documentation updated

---

### Implementation Details

#### Step 1: Implement __aenter__ and __aexit__

**File:** `src/soni/runtime/loop.py`

**Add import:**
```python
from types import TracebackType
```

**Add after `__init__` (~line 60):**

```python
async def __aenter__(self) -> "RuntimeLoop":
    """Async context manager entry - initialize runtime.

    Returns:
        Self for use in `async with` statements.

    Example:
        async with RuntimeLoop(config) as runtime:
            response = await runtime.process_message("hi", "user1")
    """
    await self.initialize()
    return self

async def __aexit__(
    self,
    exc_type: type[BaseException] | None,
    exc_val: BaseException | None,
    exc_tb: TracebackType | None,
) -> bool:
    """Async context manager exit - cleanup resources.

    Always performs cleanup, regardless of whether an exception occurred.

    Args:
        exc_type: Exception type if an exception was raised.
        exc_val: Exception instance if an exception was raised.
        exc_tb: Traceback if an exception was raised.

    Returns:
        False to propagate exceptions (never suppresses).
    """
    await self.cleanup()
    return False  # Don't suppress exceptions
```

**Update class docstring:**

```python
class RuntimeLoop:
    """Main runtime for processing dialogue messages.

    Supports async context manager protocol for resource management:

        async with RuntimeLoop(config, checkpointer) as runtime:
            response = await runtime.process_message("hi", "user1")
        # Resources automatically cleaned up

    Can also be used without context manager, but cleanup() must be
    called manually to release resources.
    """
```

#### Step 2: Make cleanup() idempotent

**File:** `src/soni/runtime/loop.py`

**Add attribute in `__init__`:**

```python
def __init__(
    self,
    config: SoniConfig,
    checkpointer: BaseCheckpointSaver | None = None,
    registry: ActionRegistry | None = None,
    du: DUProtocol | None = None,
):
    self.config = config
    self._initializer = RuntimeInitializer(config, checkpointer, registry, du)
    self._hydrator = StateHydrator()
    self._extractor = ResponseExtractor()
    self._components: RuntimeComponents | None = None
    self._cleanup_done = False  # Track cleanup state
```

**Update cleanup():**

```python
async def cleanup(self) -> None:
    """Clean up runtime resources.

    Safe to call multiple times - subsequent calls are no-ops.
    Should be called during server shutdown to release resources gracefully.
    """
    if self._cleanup_done:
        logger.debug("Cleanup already completed, skipping")
        return

    logger.info("RuntimeLoop cleanup starting...")

    if not self._components:
        logger.debug("No components to clean up")
        self._cleanup_done = True
        return

    # Close checkpointer if it has a close method
    checkpointer = self._components.checkpointer
    if checkpointer:
        if hasattr(checkpointer, "aclose"):
            try:
                await checkpointer.aclose()
                logger.debug("Checkpointer closed (async)")
            except Exception as e:
                logger.warning(f"Error closing checkpointer: {e}")

    # Clear references to allow GC
    self._components = None
    self._cleanup_done = True

    logger.info("RuntimeLoop cleanup completed")
```

#### Step 3: Update Server Lifespan

**File:** `src/soni/server/api.py`

**Current code (lines 34-79):**
```python
@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan - initialize on startup, cleanup on shutdown."""
    config_path = Path(os.getenv("SONI_CONFIG_PATH", "soni.yaml"))

    if config_path.exists():
        try:
            config = ConfigLoader.load(config_path)
            runtime = RuntimeLoop(config)
            await runtime.initialize()
            app.state.config = config
            app.state.runtime = runtime
            # ...
        except Exception as e:
            # ...

    yield

    # === SHUTDOWN ===
    shutdown_runtime = getattr(app.state, "runtime", None)
    if shutdown_runtime is not None:
        try:
            await shutdown_runtime.cleanup()
            # ...
```

**New code (using context manager):**

```python
@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan with automatic resource management.

    Uses RuntimeLoop as async context manager for guaranteed cleanup.
    """
    config_path = Path(os.getenv("SONI_CONFIG_PATH", "soni.yaml"))

    if not config_path.exists():
        logger.warning(
            f"Configuration file {config_path} not found. "
            "Server will start but message processing will fail."
        )
        yield
        return

    logger.info(f"Loading configuration from {config_path}")
    config = ConfigLoader.load(config_path)

    async with RuntimeLoop(config) as runtime:
        app.state.config = config
        app.state.runtime = runtime
        logger.info("Soni server initialized successfully")

        yield

        # Cleanup happens automatically here via __aexit__

    # Clear references after context manager exits
    app.state.runtime = None
    app.state.config = None
    logger.info("Soni server shutdown completed")
```

**Why this is better:**
- Cleaner, more readable
- Guaranteed cleanup via context manager
- Exception handling built into `async with`
- No manual try/finally needed

---

### TDD Cycle (MANDATORY)

#### Red Phase: Write Failing Tests

**Test file:** `tests/unit/runtime/test_loop_context_manager.py`

```python
"""Tests for RuntimeLoop async context manager protocol.

Verifies proper resource management via __aenter__/__aexit__.
"""

import asyncio
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from soni.runtime.loop import RuntimeLoop


@pytest.fixture
def mock_config() -> MagicMock:
    """Create mock SoniConfig."""
    config = MagicMock()
    config.flows = {}
    config.slots = {}
    return config


class TestAsyncContextManagerProtocol:
    """Tests for __aenter__ and __aexit__ implementation."""

    @pytest.mark.asyncio
    async def test_aenter_initializes_runtime(
        self, mock_config: MagicMock
    ) -> None:
        """Test that __aenter__ calls initialize()."""
        runtime = RuntimeLoop(mock_config)

        with patch.object(runtime, "initialize", new_callable=AsyncMock) as mock_init:
            result = await runtime.__aenter__()

            mock_init.assert_called_once()
            assert result is runtime

    @pytest.mark.asyncio
    async def test_aexit_calls_cleanup(
        self, mock_config: MagicMock
    ) -> None:
        """Test that __aexit__ calls cleanup()."""
        runtime = RuntimeLoop(mock_config)
        runtime._components = MagicMock()

        with patch.object(runtime, "cleanup", new_callable=AsyncMock) as mock_cleanup:
            result = await runtime.__aexit__(None, None, None)

            mock_cleanup.assert_called_once()
            assert result is False  # Should not suppress exceptions

    @pytest.mark.asyncio
    async def test_aexit_calls_cleanup_on_exception(
        self, mock_config: MagicMock
    ) -> None:
        """Test that __aexit__ calls cleanup even when exception occurred."""
        runtime = RuntimeLoop(mock_config)
        runtime._components = MagicMock()

        with patch.object(runtime, "cleanup", new_callable=AsyncMock) as mock_cleanup:
            result = await runtime.__aexit__(
                ValueError, ValueError("test error"), None
            )

            mock_cleanup.assert_called_once()
            assert result is False  # Should propagate exception

    @pytest.mark.asyncio
    async def test_context_manager_usage(
        self, mock_config: MagicMock
    ) -> None:
        """Test RuntimeLoop can be used as async context manager."""
        with patch.object(
            RuntimeLoop, "initialize", new_callable=AsyncMock
        ) as mock_init, patch.object(
            RuntimeLoop, "cleanup", new_callable=AsyncMock
        ) as mock_cleanup:
            async with RuntimeLoop(mock_config) as runtime:
                assert runtime is not None
                mock_init.assert_called_once()

            mock_cleanup.assert_called_once()


class TestContextManagerCleanup:
    """Tests for cleanup behavior in context manager."""

    @pytest.mark.asyncio
    async def test_cleanup_on_normal_exit(
        self, mock_config: MagicMock
    ) -> None:
        """Test resources are cleaned up on normal context exit."""
        cleanup_called = False

        async def track_cleanup() -> None:
            nonlocal cleanup_called
            cleanup_called = True

        runtime = RuntimeLoop(mock_config)

        with patch.object(
            runtime, "initialize", new_callable=AsyncMock
        ), patch.object(
            runtime, "cleanup", side_effect=track_cleanup
        ):
            async with runtime:
                assert not cleanup_called

            assert cleanup_called

    @pytest.mark.asyncio
    async def test_cleanup_on_exception(
        self, mock_config: MagicMock
    ) -> None:
        """Test resources are cleaned up when exception raised inside context."""
        cleanup_called = False

        async def track_cleanup() -> None:
            nonlocal cleanup_called
            cleanup_called = True

        runtime = RuntimeLoop(mock_config)

        with patch.object(
            runtime, "initialize", new_callable=AsyncMock
        ), patch.object(
            runtime, "cleanup", side_effect=track_cleanup
        ):
            with pytest.raises(ValueError, match="intentional"):
                async with runtime:
                    raise ValueError("intentional error")

            assert cleanup_called

    @pytest.mark.asyncio
    async def test_exception_propagates(
        self, mock_config: MagicMock
    ) -> None:
        """Test that exceptions inside context are propagated."""
        runtime = RuntimeLoop(mock_config)

        with patch.object(
            runtime, "initialize", new_callable=AsyncMock
        ), patch.object(
            runtime, "cleanup", new_callable=AsyncMock
        ):
            with pytest.raises(RuntimeError, match="test error"):
                async with runtime:
                    raise RuntimeError("test error")


class TestCleanupIdempotency:
    """Tests for idempotent cleanup behavior."""

    @pytest.mark.asyncio
    async def test_cleanup_can_be_called_multiple_times(
        self, mock_config: MagicMock
    ) -> None:
        """Test cleanup() is safe to call multiple times."""
        runtime = RuntimeLoop(mock_config)
        runtime._components = MagicMock()
        runtime._components.checkpointer = None

        # First cleanup
        await runtime.cleanup()
        assert runtime._components is None
        assert runtime._cleanup_done is True

        # Second cleanup should be no-op
        await runtime.cleanup()  # Should not raise

    @pytest.mark.asyncio
    async def test_cleanup_flag_prevents_double_cleanup(
        self, mock_config: MagicMock
    ) -> None:
        """Test _cleanup_done flag prevents redundant cleanup."""
        mock_checkpointer = MagicMock()
        mock_checkpointer.aclose = AsyncMock()

        runtime = RuntimeLoop(mock_config, checkpointer=mock_checkpointer)
        runtime._components = MagicMock()
        runtime._components.checkpointer = mock_checkpointer

        await runtime.cleanup()
        await runtime.cleanup()  # Second call

        # aclose should only be called once
        assert mock_checkpointer.aclose.call_count == 1


class TestIntegrationScenarios:
    """Tests for real-world usage scenarios."""

    @pytest.mark.asyncio
    async def test_multiple_requests_within_context(
        self, mock_config: MagicMock
    ) -> None:
        """Test multiple process_message calls work within context."""
        runtime = RuntimeLoop(mock_config)

        with patch.object(
            runtime, "initialize", new_callable=AsyncMock
        ), patch.object(
            runtime, "cleanup", new_callable=AsyncMock
        ), patch.object(
            runtime, "process_message", new_callable=AsyncMock, return_value="response"
        ) as mock_process:
            async with runtime:
                await runtime.process_message("msg1", "user1")
                await runtime.process_message("msg2", "user2")
                await runtime.process_message("msg3", "user1")

            assert mock_process.call_count == 3

    @pytest.mark.asyncio
    async def test_cleanup_releases_checkpointer(
        self, mock_config: MagicMock
    ) -> None:
        """Test checkpointer is properly closed during cleanup."""
        mock_checkpointer = MagicMock()
        mock_checkpointer.aclose = AsyncMock()

        runtime = RuntimeLoop(mock_config, checkpointer=mock_checkpointer)

        # Simulate initialized state
        runtime._components = MagicMock()
        runtime._components.checkpointer = mock_checkpointer

        await runtime.cleanup()

        mock_checkpointer.aclose.assert_called_once()
```

**Run tests (should fail):**
```bash
uv run pytest tests/unit/runtime/test_loop_context_manager.py -v
# Expected: FAILED (__aenter__/__aexit__ not implemented)
```

**Commit:**
```bash
git add tests/
git commit -m "test: add failing tests for RuntimeLoop context manager (P1-002)"
```

#### Green Phase: Make Tests Pass

**Implement changes from "Implementation Details" section.**

**Verify:**
```bash
uv run pytest tests/unit/runtime/test_loop_context_manager.py -v
# Expected: PASSED ✅
```

**Commit:**
```bash
git add src/ tests/
git commit -m "feat: add async context manager to RuntimeLoop (P1-002)"
```

---

### Success Criteria

- [ ] `RuntimeLoop` implements `__aenter__` and `__aexit__`
- [ ] `async with RuntimeLoop(config) as runtime:` works
- [ ] Cleanup executes even on exceptions
- [ ] Cleanup is idempotent (safe to call multiple times)
- [ ] Server lifespan uses context manager
- [ ] All tests pass

### Manual Validation

```bash
# 1. Run context manager tests
uv run pytest tests/unit/runtime/test_loop_context_manager.py -v

# 2. Verify protocol implementation
uv run python -c "
from soni.runtime.loop import RuntimeLoop
from unittest.mock import MagicMock

# Check protocol methods exist
assert hasattr(RuntimeLoop, '__aenter__')
assert hasattr(RuntimeLoop, '__aexit__')
print('Protocol methods implemented ✓')

# Check return type annotations
import inspect
sig = inspect.signature(RuntimeLoop.__aenter__)
print(f'__aenter__ signature: {sig}')
"

# 3. Run all runtime tests
uv run pytest tests/unit/runtime/ -v

# 4. Run server tests
uv run pytest tests/unit/server/ -v
```

### References

- `src/soni/runtime/loop.py` - RuntimeLoop implementation
- `src/soni/server/api.py` - Server lifespan
- [Python Async Context Managers](https://docs.python.org/3/reference/datamodel.html#asynchronous-context-managers)
- [FastAPI Lifespan](https://fastapi.tiangolo.com/advanced/events/)

### Notes

**Why implement methods directly vs `@asynccontextmanager` decorator:**
1. More explicit for classes
2. Allows instance reuse
3. Standard pattern for class-based resources

**Error handling in cleanup:**
- Checkpointer close errors: Log warning, continue
- Critical errors: Propagate
- Currently using `logger.warning()` which is appropriate

**Future consideration - Timeout:**
```python
async def cleanup(self) -> None:
    try:
        async with asyncio.timeout(30):
            # ... cleanup logic
    except asyncio.TimeoutError:
        logger.error("Cleanup timed out after 30s")
```
Evaluate if production issues arise.
