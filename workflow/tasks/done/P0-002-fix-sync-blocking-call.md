## Task: P0-002 - Fix Incorrect Checkpointer API Usage

**Task ID:** P0-002
**Milestone:** 1.2 - Correct LangGraph API Usage
**Dependencies:** None
**Estimated Duration:** 1 hour

### Objective

Fix incorrect checkpointer API usage in `RuntimeLoop`. The code uses non-existent methods `adelete(config)`/`delete(config)`. Correct LangGraph API is `adelete_thread(thread_id)`.

### Context

**Async-First Principle:** Soni is async-first. All checkpointers used with Soni MUST provide async methods. No sync fallback is needed.

**Current code problem:**

```python
# Lines 230-233 - WRONG API
if hasattr(checkpointer, "adelete"):
    await checkpointer.adelete(config)      # ❌ Method doesn't exist!
elif hasattr(checkpointer, "delete"):
    checkpointer.delete(config)             # ❌ Wrong signature + unnecessary
```

**Correct LangGraph API (from BaseCheckpointSaver):**

```python
async def adelete_thread(self, thread_id: str) -> None:
    """Delete all checkpoints for a thread."""
    ...
```

See: `ref/langgraph/libs/checkpoint/langgraph/checkpoint/base/__init__.py` lines 346-355

### Deliverables

- [ ] Fix `reset_state()` to use `adelete_thread(user_id)`
- [ ] Remove sync fallback (async-first)
- [ ] Tests verify correct API usage

---

### Implementation Details

#### Step 1: Fix reset_state() - Use Correct API

**File:** `src/soni/runtime/loop.py`

**Current code (lines 229-245):**

```python
# Delete the checkpoint for this thread
if hasattr(checkpointer, "adelete"):
    await checkpointer.adelete(config)
elif hasattr(checkpointer, "delete"):
    checkpointer.delete(config)
else:
    # Fallback: Write empty state
    ...
```

**Fixed code:**

```python
# Delete the checkpoint for this thread (async-first)
if hasattr(checkpointer, "adelete_thread"):
    await checkpointer.adelete_thread(user_id)
else:
    # Fallback: Write empty state if checkpointer doesn't support deletion
    from soni.core.state import create_empty_dialogue_state

    empty_state = create_empty_dialogue_state()
    if self._components.graph:
        await self._components.graph.aupdate_state(
            cast(RunnableConfig, config), empty_state
        )
```

**Why:**
- Uses correct API: `adelete_thread(thread_id)` not `adelete(config)`
- Async-first: no sync fallback needed
- Simpler and cleaner

---

### TDD Cycle

#### Red Phase: Write Failing Tests

**Test file:** `tests/unit/runtime/test_loop_reset_state.py`

```python
"""Tests for reset_state using correct LangGraph API."""

import asyncio
from unittest.mock import MagicMock, AsyncMock, patch

import pytest

from soni.runtime.loop import RuntimeLoop


class MockAsyncCheckpointer:
    """Mock checkpointer with correct LangGraph async API."""

    def __init__(self):
        self.adelete_thread_called = False
        self.last_deleted_thread_id: str | None = None

    async def adelete_thread(self, thread_id: str) -> None:
        """Async delete_thread - correct LangGraph API."""
        await asyncio.sleep(0.01)
        self.adelete_thread_called = True
        self.last_deleted_thread_id = thread_id

    async def aclose(self) -> None:
        """Async close."""
        await asyncio.sleep(0.01)


@pytest.fixture
def mock_config() -> MagicMock:
    """Create mock SoniConfig."""
    config = MagicMock()
    config.flows = {}
    config.slots = {}
    return config


class TestResetStateCorrectAPI:
    """Tests for reset_state using correct LangGraph API."""

    @pytest.mark.asyncio
    async def test_reset_state_calls_adelete_thread_with_user_id(
        self, mock_config: MagicMock
    ) -> None:
        """Test that adelete_thread is called with thread_id directly."""
        async_checkpointer = MockAsyncCheckpointer()

        runtime = RuntimeLoop(mock_config, checkpointer=async_checkpointer)
        runtime._components = MagicMock()
        runtime._components.checkpointer = async_checkpointer
        runtime._components.graph = MagicMock()

        with patch.object(runtime, "get_state", new_callable=AsyncMock) as mock_get:
            mock_get.return_value = {"some": "state"}

            await runtime.reset_state("user_123")

            assert async_checkpointer.adelete_thread_called
            assert async_checkpointer.last_deleted_thread_id == "user_123"

    @pytest.mark.asyncio
    async def test_reset_state_does_not_use_old_api(
        self, mock_config: MagicMock
    ) -> None:
        """Verify we don't call the old incorrect adelete method."""
        async_checkpointer = MockAsyncCheckpointer()
        # Add the old incorrect method to verify it's NOT called
        async_checkpointer.adelete = AsyncMock()  # type: ignore

        runtime = RuntimeLoop(mock_config, checkpointer=async_checkpointer)
        runtime._components = MagicMock()
        runtime._components.checkpointer = async_checkpointer
        runtime._components.graph = MagicMock()

        with patch.object(runtime, "get_state", new_callable=AsyncMock) as mock_get:
            mock_get.return_value = {"some": "state"}

            await runtime.reset_state("user_123")

            # Old method should NOT be called
            async_checkpointer.adelete.assert_not_called()  # type: ignore
            # Correct method should be called
            assert async_checkpointer.adelete_thread_called

    @pytest.mark.asyncio
    async def test_reset_state_fallback_to_empty_state(
        self, mock_config: MagicMock
    ) -> None:
        """Test fallback when checkpointer has no adelete_thread."""
        # Checkpointer without adelete_thread method
        basic_checkpointer = MagicMock()
        del basic_checkpointer.adelete_thread  # Ensure it doesn't exist

        runtime = RuntimeLoop(mock_config, checkpointer=basic_checkpointer)
        runtime._components = MagicMock()
        runtime._components.checkpointer = basic_checkpointer
        mock_graph = MagicMock()
        mock_graph.aupdate_state = AsyncMock()
        runtime._components.graph = mock_graph

        with patch.object(runtime, "get_state", new_callable=AsyncMock) as mock_get:
            mock_get.return_value = {"some": "state"}

            result = await runtime.reset_state("user_123")

            assert result is True
            mock_graph.aupdate_state.assert_called_once()
```

**Run tests (should fail):**
```bash
uv run pytest tests/unit/runtime/test_loop_reset_state.py -v
# Expected: FAILED (wrong method names)
```

#### Green Phase: Implement Fix

Apply changes from "Implementation Details" section.

**Verify:**
```bash
uv run pytest tests/unit/runtime/test_loop_reset_state.py -v
# Expected: PASSED ✅
```

---

### Success Criteria

- [ ] Uses `adelete_thread(thread_id)` (not `adelete(config)`)
- [ ] No unnecessary sync fallback code
- [ ] All tests pass: `uv run pytest tests/ -v`

### Manual Validation

```bash
# 1. Verify correct method is used
uv run rg "adelete_thread" src/soni/runtime/loop.py

# 2. Verify old incorrect method is NOT used
uv run rg "checkpointer\.adelete\(" src/soni/runtime/loop.py
# Should return nothing

# 3. Run tests
uv run pytest tests/unit/runtime/test_loop_reset_state.py -v
```

### References

- [LangGraph BaseCheckpointSaver](file:///Users/jorge/Projects/Playground/soni/ref/langgraph/libs/checkpoint/langgraph/checkpoint/base/__init__.py#L346-L355) - Correct API
- `src/soni/runtime/loop.py` - File to modify
