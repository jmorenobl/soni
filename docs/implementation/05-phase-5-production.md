# Phase 5: Production Readiness

**Goal**: Production-ready deployment with observability, error handling, and API.

**Duration**: 2-3 days

**Dependencies**: Phase 1-4 (Complete core system)

## Overview

This phase adds production features:
- Comprehensive error handling
- Logging and metrics
- Health checks
- Configuration management
- FastAPI endpoints
- Deployment readiness

## Tasks

### Task 5.1: Error Handling & Recovery

**Status**: 📋 Backlog

**File**: `src/soni/dm/nodes/handle_error.py`

**What**: Implement error handling node and recovery strategies.

**Why**: Graceful degradation and error recovery.

**Implementation**:

```python
from soni.core.types import DialogueState, RuntimeContext
from langgraph.runtime import Runtime
import logging

logger = logging.getLogger(__name__)

async def handle_error_node(
    state: DialogueState,
    runtime: Runtime[RuntimeContext]
) -> dict:
    """
    Handle errors and attempt recovery.

    Args:
        state: Current dialogue state
        runtime: Runtime context

    Returns:
        Partial state updates with recovery strategy
    """
    error = state.get("metadata", {}).get("error")
    error_type = state.get("metadata", {}).get("error_type")

    logger.error(
        f"Error in dialogue flow: {error}",
        extra={
            "error_type": error_type,
            "conversation_state": state["conversation_state"],
            "turn_count": state["turn_count"]
        }
    )

    flow_manager = runtime.context["flow_manager"]

    # Attempt recovery based on error type
    if error_type == "validation_error":
        # Clear invalid data and retry
        if state["flow_stack"]:
            flow_manager.pop_flow(state, result="cancelled")

        return {
            "last_response": "Let's try that again. What would you like to do?",
            "conversation_state": "idle",
            "metadata": {**state.get("metadata", {}), "error": None, "error_type": None}
        }

    elif error_type == "nlu_error":
        return {
            "last_response": "I didn't understand that. Could you rephrase?",
            "conversation_state": "understanding",
            "metadata": {**state.get("metadata", {}), "error": None, "error_type": None}
        }

    elif error_type == "action_error":
        return {
            "last_response": "Something went wrong while processing your request. Please try again.",
            "conversation_state": "idle",
            "flow_stack": [],
            "flow_slots": {},
            "metadata": {**state.get("metadata", {}), "error": None, "error_type": None}
        }

    # Generic error - clear stack and start over
    return {
        "last_response": "Something went wrong. Let's start fresh.",
        "conversation_state": "idle",
        "flow_stack": [],
        "flow_slots": {},
        "metadata": {**state.get("metadata", {}), "error": None, "error_type": None}
    }
```

**Tests**:

`tests/unit/test_error_handling.py`:
```python
@pytest.mark.asyncio
async def test_handle_error_validation():
    """Test error handling for validation errors."""
    # Arrange
    state = create_empty_state()
    state["metadata"] = {
        "error": "Invalid slot value",
        "error_type": "validation_error"
    }

    mock_flow_manager = MagicMock()
    mock_runtime = MagicMock()
    mock_runtime.context = {"flow_manager": mock_flow_manager}

    # Act
    result = await handle_error_node(state, mock_runtime)

    # Assert
    assert result["conversation_state"] == "idle"
    assert "try that again" in result["last_response"].lower()
```

**Completion Criteria**:
- [ ] Error node implemented
- [ ] Recovery strategies defined
- [ ] Tests passing
- [ ] Logging integrated

---

### Task 5.2: Structured Logging

**Status**: 📋 Backlog

**File**: `src/soni/observability/logging.py`

**What**: Configure structured logging with context.

**Why**: Production debugging and observability.

**Implementation**:

```python
import logging
import logging.config
from typing import Any

def setup_logging(level: str = "INFO") -> None:
    """
    Configure structured logging for Soni.

    Args:
        level: Log level (DEBUG, INFO, WARNING, ERROR)
    """
    config = {
        "version": 1,
        "disable_existing_loggers": False,
        "formatters": {
            "structured": {
                "format": "%(asctime)s - %(name)s - %(levelname)s - %(message)s",
                "datefmt": "%Y-%m-%d %H:%M:%S"
            },
            "json": {
                "()": "pythonjsonlogger.jsonlogger.JsonFormatter",
                "format": "%(asctime)s %(name)s %(levelname)s %(message)s"
            }
        },
        "handlers": {
            "console": {
                "class": "logging.StreamHandler",
                "formatter": "structured",
                "level": level
            },
            "file": {
                "class": "logging.handlers.RotatingFileHandler",
                "filename": "soni.log",
                "maxBytes": 10485760,  # 10MB
                "backupCount": 5,
                "formatter": "json",
                "level": level
            }
        },
        "loggers": {
            "soni": {
                "handlers": ["console", "file"],
                "level": level,
                "propagate": False
            }
        },
        "root": {
            "handlers": ["console"],
            "level": "WARNING"
        }
    }

    logging.config.dictConfig(config)

class ContextLogger:
    """Logger with contextual information."""

    def __init__(self, name: str):
        self.logger = logging.getLogger(name)

    def with_context(self, **context: Any):
        """Add context to log messages."""
        return logging.LoggerAdapter(self.logger, context)
```

**Tests**:

`tests/unit/test_logging.py`:
```python
def test_logging_setup():
    """Test logging configuration."""
    # Arrange & Act
    setup_logging(level="DEBUG")

    # Assert
    logger = logging.getLogger("soni")
    assert logger.level == logging.DEBUG
```

**Completion Criteria**:
- [ ] Logging configured
- [ ] Structured format
- [ ] File rotation
- [ ] Tests passing

---

### Task 5.3: Configuration Management

**Status**: 📋 Backlog

**File**: `src/soni/config/loader.py`

**What**: Load and validate YAML configuration.

**Why**: Production deployments need configuration management.

**Implementation**:

```python
from pathlib import Path
import yaml
from pydantic import BaseModel, Field, ValidationError as PydanticValidationError
from soni.core.errors import ConfigurationError

class SoniConfig(BaseModel):
    """Soni framework configuration."""

    # LLM settings
    llm_model: str = Field(default="gpt-4o-mini", description="LLM model name")
    llm_temperature: float = Field(default=0.0, ge=0.0, le=2.0)
    llm_max_tokens: int = Field(default=1000, gt=0)

    # Flow management
    max_stack_depth: int = Field(default=3, gt=0)
    on_limit_reached: str = Field(default="cancel_oldest")

    # Memory management
    max_completed_flows: int = Field(default=10, gt=0)
    max_trace_entries: int = Field(default=50, gt=0)

    # Persistence
    persistence_backend: str = Field(default="memory")
    persistence_connection_string: str | None = None

    # NLU
    nlu_cache_size: int = Field(default=1000, gt=0)
    nlu_cache_ttl: int = Field(default=300, gt=0)

def load_config(path: Path | str) -> SoniConfig:
    """
    Load configuration from YAML file.

    Args:
        path: Path to configuration file

    Returns:
        Validated SoniConfig

    Raises:
        ConfigurationError: If configuration is invalid
    """
    path = Path(path)

    if not path.exists():
        raise ConfigurationError(
            f"Configuration file not found: {path}",
            path=str(path)
        )

    try:
        with path.open() as f:
            data = yaml.safe_load(f)

        # Extract settings if nested
        settings = data.get("settings", data)

        return SoniConfig(**settings)

    except yaml.YAMLError as e:
        raise ConfigurationError(
            f"Invalid YAML: {e}",
            path=str(path)
        )
    except PydanticValidationError as e:
        raise ConfigurationError(
            f"Invalid configuration: {e}",
            path=str(path)
        )
```

**Tests**:

`tests/unit/test_config.py`:
```python
def test_load_config_valid(tmp_path):
    """Test loading valid configuration."""
    # Arrange
    config_file = tmp_path / "config.yaml"
    config_file.write_text("""
settings:
  llm_model: gpt-4o-mini
  max_stack_depth: 5
""")

    # Act
    config = load_config(config_file)

    # Assert
    assert config.llm_model == "gpt-4o-mini"
    assert config.max_stack_depth == 5

def test_load_config_invalid_raises(tmp_path):
    """Test invalid configuration raises error."""
    # Arrange
    config_file = tmp_path / "config.yaml"
    config_file.write_text("""
settings:
  max_stack_depth: -1  # Invalid
""")

    # Act & Assert
    with pytest.raises(ConfigurationError):
        load_config(config_file)
```

**Completion Criteria**:
- [ ] Configuration loader implemented
- [ ] Validation working
- [ ] Tests passing

---

### Task 5.4: FastAPI Endpoints

**Status**: 📋 Backlog

**File**: `src/soni/server/api.py`

**What**: Implement REST API endpoints.

**Why**: Production deployment requires HTTP API.

**Implementation**:

```python
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from soni.dm.builder import build_graph
from soni.config.loader import load_config, SoniConfig
from langgraph.types import Command
import logging

logger = logging.getLogger(__name__)

app = FastAPI(title="Soni Dialogue System", version="0.8.0")

# Global state (initialized on startup)
graph = None
config: SoniConfig | None = None

class MessageRequest(BaseModel):
    """User message request."""
    user_id: str
    message: str

class MessageResponse(BaseModel):
    """Assistant response."""
    response: str
    conversation_state: str
    waiting_for_input: bool

@app.on_event("startup")
async def startup():
    """Initialize system on startup."""
    global graph, config

    # Load configuration
    config = load_config("soni.yaml")

    # Build dependencies (mocked for now)
    # TODO: Initialize real dependencies
    from unittest.mock import MagicMock, AsyncMock

    context = {
        "flow_manager": MagicMock(),
        "nlu_provider": AsyncMock(),
        "action_handler": AsyncMock(),
        "scope_manager": MagicMock(),
        "normalizer": AsyncMock()
    }

    # Build graph
    graph = build_graph(context)

    logger.info("Soni system initialized")

@app.post("/message", response_model=MessageResponse)
async def process_message(request: MessageRequest) -> MessageResponse:
    """
    Process user message and return response.

    Args:
        request: Message request with user_id and message

    Returns:
        Assistant response
    """
    if graph is None:
        raise HTTPException(status_code=503, detail="System not initialized")

    try:
        thread_config = {"configurable": {"thread_id": request.user_id}}

        # Check if interrupted
        current_state = await graph.aget_state(thread_config)

        if current_state.next:
            # Resume from interrupt
            result = await graph.ainvoke(
                Command(resume=request.message),
                config=thread_config
            )
        else:
            # New message
            from soni.core.state import create_initial_state
            input_state = create_initial_state(request.message)
            result = await graph.ainvoke(input_state, config=thread_config)

        # Extract response
        return MessageResponse(
            response=result.get("last_response", ""),
            conversation_state=result.get("conversation_state", "idle"),
            waiting_for_input=bool(current_state.next)
        )

    except Exception as e:
        logger.error(f"Error processing message: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/health")
async def health_check():
    """Health check endpoint."""
    return {
        "status": "healthy",
        "version": "0.8.0",
        "graph_initialized": graph is not None
    }
```

**Tests**:

`tests/integration/test_api.py`:
```python
import pytest
from fastapi.testclient import TestClient
from soni.server.api import app

@pytest.fixture
def client():
    """Create test client."""
    return TestClient(app)

def test_health_check(client):
    """Test health check endpoint."""
    # Act
    response = client.get("/health")

    # Assert
    assert response.status_code == 200
    assert response.json()["status"] == "healthy"

# Note: Full message test requires mocking dependencies
```

**Completion Criteria**:
- [ ] FastAPI app created
- [ ] Message endpoint implemented
- [ ] Health check working
- [ ] Tests passing

---

### Task 5.5: Deployment Documentation

**Status**: 📋 Backlog

**File**: `docs/deployment/README.md`

**What**: Document deployment procedures.

**Why**: Production deployment guide.

**Content**:

```markdown
# Soni Deployment Guide

## Quick Start

### 1. Install Dependencies

\`\`\`bash
uv sync
\`\`\`

### 2. Configure

Create `soni.yaml`:

\`\`\`yaml
settings:
  llm_model: gpt-4o-mini
  llm_temperature: 0.0
  max_stack_depth: 3
  persistence_backend: sqlite
  persistence_connection_string: "dialogue_state.db"
\`\`\`

### 3. Run Server

\`\`\`bash
uv run uvicorn soni.server.api:app --host 0.0.0.0 --port 8000
\`\`\`

### 4. Test

\`\`\`bash
curl -X POST http://localhost:8000/message \\
  -H "Content-Type: application/json" \\
  -d '{"user_id": "test-user", "message": "Hello"}'
\`\`\`

## Production Deployment

See full guide in this directory.
```

**Completion Criteria**:
- [ ] Deployment docs created
- [ ] Quick start guide
- [ ] Production checklist

---

## Phase 5 Completion Checklist

Before declaring the refactoring complete, verify:

- [ ] All Task 5.x completed
- [ ] Error handling working
- [ ] Logging configured
- [ ] Configuration management working
- [ ] FastAPI server running
- [ ] Health checks working
- [ ] Deployment docs complete
- [ ] All tests passing
- [ ] Mypy passes
- [ ] Ruff passes
- [ ] Code committed

## Phase 5 Validation

```bash
# Type checking
uv run mypy src/soni

# All tests
uv run pytest tests/ -v

# Coverage report
uv run pytest tests/ --cov=soni --cov-report=html

# Start server
uv run uvicorn soni.server.api:app --reload

# Health check
curl http://localhost:8000/health
```

## Production Checklist

- [ ] Configuration validated
- [ ] Error handling tested
- [ ] Logging verified
- [ ] Performance acceptable
- [ ] Security reviewed
- [ ] Documentation complete
- [ ] Deployment tested

## Next Steps

Once Phase 5 is complete:

1. Review **[99-validation.md](99-validation.md)** for final validation
2. Deploy to staging environment
3. Run acceptance tests
4. Deploy to production

---

**Phase**: 5 of 5
**Status**: 📋 Backlog
**Estimated Duration**: 2-3 days
**Final Phase**: Yes ✅
