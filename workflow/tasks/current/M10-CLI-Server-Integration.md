# M10: CLI & Server Integration

**Status**: 🔴 Not Started
**Priority**: High
**Estimated Effort**: 4-6 hours
**Dependencies**: M0-M9 (completed)

---

## Overview

Integrate the archived CLI and Server code with the current `RuntimeLoop` implementation. The CLI (`soni chat`) and Server (`soni server`) commands reference an outdated API that no longer exists.

### Problem Summary

| Issue | Location | Impact |
|-------|----------|--------|
| Missing `dspy_service` module | `cli/chat.py:156`, `cli/optimize.py:46` | CLI broken |
| Missing `stream_extractor` module | `cli/chat.py:43`, `server/api.py:283` | Streaming broken |
| Missing `checkpointer` module | `cli/chat.py:167` | Persistence broken |
| Outdated `RuntimeLoop` API | `cli/chat.py`, `server/api.py` | All endpoints broken |

### Current RuntimeLoop API

```python
# Correct usage pattern (async context manager):
async with RuntimeLoop(config, checkpointer) as runtime:
    response = await runtime.process_message(message, user_id)
```

### Broken Code Examples

```python
# cli/chat.py (BROKEN):
await runtime.initialize()  # ❌ Method doesn't exist
runtime.du                  # ❌ Property doesn't exist

# server/api.py (BROKEN):
runtime._components         # ❌ Private attr doesn't exist
runtime.get_state()         # ❌ Method doesn't exist
runtime.reset_state()       # ❌ Method doesn't exist
```

---

## Acceptance Criteria

- [ ] `uv run soni chat --config examples/banking/domain` starts interactive session
- [ ] `uv run soni server --config examples/banking/domain` starts HTTP server
- [ ] `GET /health` returns 200 OK
- [ ] `POST /chat` processes messages correctly
- [ ] `GET /state/{user_id}` returns conversation state
- [ ] `DELETE /state/{user_id}` resets conversation
- [ ] All mypy errors in `cli/` and `server/` are fixed
- [ ] Streaming mode works (optional, can defer to M11)

---

## Implementation Plan

### Phase 1: Fix CLI Chat Command

#### 1.1 Update RuntimeLoop Usage

**File**: [cli/commands/chat.py](file:///Users/jorge/Projects/Playground/soni/src/soni/cli/commands/chat.py)

Replace:
```python
runtime = RuntimeLoop(config=soni_config, checkpointer=checkpointer)
await runtime.initialize()
```

With:
```python
async with RuntimeLoop(config=soni_config, checkpointer=checkpointer) as runtime:
    chat = SoniChatCLI(runtime, user_id=...)
    await chat.start()
```

#### 1.2 Fix DSPy Bootstrap

Option A: Inline DSPy setup (simple):
```python
import dspy
dspy.configure(lm=dspy.LM("openai/gpt-4o-mini"))
```

Option B: Create `soni.core.dspy_service` module (proper):
```python
# src/soni/core/dspy_service.py
class DSPyBootstrapper:
    def __init__(self, config: SoniConfig): ...
    def configure(self) -> DSPyResult: ...
```

#### 1.3 Fix Checkpointer Import

Replace:
```python
from soni.runtime.checkpointer import create_checkpointer
```

With:
```python
from langgraph.checkpoint.memory import MemorySaver
from langgraph.checkpoint.sqlite.aio import AsyncSqliteSaver

def create_checkpointer(backend: str, **kwargs):
    if backend == "memory":
        return MemorySaver()
    elif backend == "sqlite":
        return AsyncSqliteSaver.from_conn_string(kwargs.get("path", ":memory:"))
    raise ValueError(f"Unknown backend: {backend}")
```

#### 1.4 Remove optimized_du Loading (defer to M11)

The `--optimized-du` flag can be removed for now since the RuntimeLoop creates its own NLU modules.

---

### Phase 2: Fix Server API

#### 2.1 Update Lifespan

**File**: [server/api.py](file:///Users/jorge/Projects/Playground/soni/src/soni/server/api.py)

The lifespan should use async context manager:

```python
@asynccontextmanager
async def lifespan(app: FastAPI):
    config = SoniConfig.from_yaml(os.environ.get("SONI_CONFIG_PATH"))
    checkpointer = MemorySaver()

    async with RuntimeLoop(config, checkpointer) as runtime:
        app.state.runtime = runtime
        app.state.config = config
        yield
```

#### 2.2 Simplify Health Checks

Remove references to `runtime._components`. Use simple checks:

```python
@app.get("/health")
async def health_check():
    return {"status": "healthy", "version": __version__}
```

#### 2.3 Fix State Endpoints

The `get_state` and `reset_state` methods don't exist. Options:

1. **Remove endpoints** (simplest for M10)
2. **Implement via checkpointer** (proper, requires LangGraph state access)

For M10, recommend simplifying or stubbing these endpoints.

#### 2.4 Fix Chat Endpoint

Use `runtime.process_message()`:

```python
@app.post("/chat")
async def chat(request: MessageRequest, runtime: RuntimeDep):
    response = await runtime.process_message(
        request.message,
        user_id=request.user_id
    )
    return MessageResponse(response=response)
```

---

### Phase 3: Fix Streaming (Optional - Defer to M11)

The `stream_extractor` module doesn't exist. Options:

1. **Defer streaming to M11** - remove streaming code paths
2. **Implement streaming** - use LangGraph's native streaming:
   ```python
   async for chunk in graph.astream(state, config=config, stream_mode="updates"):
       yield chunk
   ```

---

### Phase 4: Type Fixes

Run `uv run mypy src/soni/cli src/soni/server` and fix all errors:

1. Fix `StateError` import (doesn't exist in `core/errors.py`)
2. Fix `VersionResponse` type mismatches
3. Fix `HealthResponse` status literal type

---

## Verification Plan

### Automated Tests

1. **Existing tests must still pass**:
   ```bash
   uv run pytest tests/ -v
   ```

2. **New integration tests for CLI/Server** (to be created):
   ```bash
   uv run pytest tests/integration/test_cli.py -v
   uv run pytest tests/integration/test_server.py -v
   ```

### Manual Verification

1. **Test CLI Chat**:
   ```bash
   cd /Users/jorge/Projects/Playground/soni
   uv run soni chat --config examples/banking/domain
   # Type: "I want to check my balance"
   # Expected: Starts check_balance flow, asks for account
   ```

2. **Test Server**:
   ```bash
   # Terminal 1:
   uv run soni server --config examples/banking/domain --port 8000

   # Terminal 2:
   curl http://localhost:8000/health
   # Expected: {"status": "healthy", ...}

   curl -X POST http://localhost:8000/chat \
     -H "Content-Type: application/json" \
     -d '{"user_id": "test", "message": "I want to transfer money"}'
   # Expected: {"response": "...", ...}
   ```

3. **Mypy Clean**:
   ```bash
   uv run mypy src/soni/cli src/soni/server
   # Expected: No errors
   ```

---

## Files to Modify

| File | Changes |
|------|---------|
| `cli/commands/chat.py` | Update RuntimeLoop usage, fix imports |
| `cli/commands/server.py` | Minor updates if needed |
| `cli/commands/optimize.py` | Fix dspy_service import |
| `server/api.py` | Update lifespan, fix endpoints, remove broken code |
| `server/models.py` | Fix type definitions if needed |
| `core/errors.py` | Add `StateError` if needed |

## Files to Create (Optional)

| File | Purpose |
|------|---------|
| `core/dspy_service.py` | DSPy bootstrapping (optional) |
| `runtime/checkpointer.py` | Checkpointer factory (optional) |
| `tests/integration/test_cli.py` | CLI integration tests |
| `tests/integration/test_server.py` | Server integration tests |

---

## Out of Scope (Defer to M11)

- Streaming support (`process_message_streaming`)
- Optimized NLU loading (`--optimized-du` flag)
- Advanced health checks with component status
- State inspection endpoints

---

## Notes

The CLI and Server code comes from the archived codebase and was not updated during the M1-M9 refactoring. The core patterns are sound but need alignment with the new `RuntimeLoop` async context manager API.
