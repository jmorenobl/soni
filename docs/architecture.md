# Soni Framework - Architecture Documentation

**Generated:** 2026-01-01
**Project:** Soni Framework (Python Library)
**Version:** 0.4.0

## Executive Summary

Soni is a modern conversational AI framework built on hexagonal architecture principles, combining DSPy's automatic prompt optimization with LangGraph's robust state management. The framework provides a clean separation between declarative configuration (YAML DSL) and implementation (Python), enabling developers to build task-oriented dialogue systems that improve through optimization.

## Technology Stack

| Category | Technology| Version | Purpose |
|----------|-----------|---------|---------|
| **Core Language** | Python | 3.11+ | Implementation language |
| **NLU/Optimization** | DSPy | ≥3.0.4 | Prompt optimization (MIPROv2) |
| **Dialogue Management** | LangGraph | ≥1.0.4 | State machine execution |
| **State Persistence** | SQLite via langgraph-checkpoint-sqlite | ≥3.0.0 | Conversation checkpointing |
| **Web Framework** | FastAPI | ≥0.122.0 | REST API & SSE streaming |
| **ASGI Server** | Uvicorn | ≥0.38.0 | Production server |
| **Data Validation** | Pydantic | ≥2.12.5 | Schema validation |
| **CLI Framework** | Typer | ≥0.15.0 | Command-line interface |
| **HTTP Client** | httpx | ≥0.28.1 | Async HTTP requests |
| **Config Format** | PyYAML | ≥6.0.3 | YAML parsing |
| **Testing** | pytest + pytest-asyncio | ≥9.0.1 | Async testing |
| **Linting** | Ruff | ≥0.14.7 | Fast linting & formatting |
| **Type Checking** | Mypy | ≥1.19.0 | Static type analysis |
| **Documentation** | MkDocs Material | ≥9.5.0 | Doc site generation |

## Architecture Pattern

**Primary Pattern:** Hexagonal Architecture (Ports & Adapters)
**Secondary Patterns:** Event-driven, Layer architecture, Dependency Injection

### Hexagonal Architecture Layers

```
┌─────────────────────────────────────────────────────┐
│ ADAPTER LAYER (Ports)                                │
│  ├─ CLI (Typer)                                      │
│  ├─ REST API (FastAPI)                               │
│  └─ WebSocket                                        │
└─────────────────────────────────────────────────────┘
           │                           ▲
           │ Commands                  │ Events
           ▼                           │
┌─────────────────────────────────────────────────────┐
│ APPLICATION LAYER                                    │
│  ├─ RuntimeLoop (Orchestrator)                       │
│  ├─ RuntimeContext (Dependency Injection)            │
│  └─ ActionExecutor                                   │
└─────────────────────────────────────────────────────┘
           │                           ▲
           │ Domain Events             │ State
           ▼                           │
┌─────────────────────────────────────────────────────┐
│ DOMAIN LAYER                                         │
│  ├─ Dialogue Management (LangGraph nodes)            │
│  ├─ Dialogue Understanding (DSPy modules)            │
│  ├─ Core Types (DialogueState, Commands, Tasks)     │
│  └─ Flow Manager                                     │
└─────────────────────────────────────────────────────┘
           │                           ▲
           │ Configuration             │ Validation
           ▼                           │
┌─────────────────────────────────────────────────────┐
│ INFRASTRUCTURE LAYER                                 │
│  ├─ YAML Compiler (DSL → Runtime)                    │
│  ├─ Config Loader                                    │
│  ├─ LLM Service (DSPy)                               │
│  └─ Validation Framework                             │
└─────────────────────────────────────────────────────┘
```

### Key Design Principles

1. **Zero-Leakage:** YAML defines WHAT, Python implements HOW. No technical details in configuration.
2. **Declarative-First:** Behavior is declared in YAML, not coded imperatively.
3. **Optimizable:** All NLU components use DSPy for automatic prompt optimization.
4. **Async-First:** All I/O operations use `async/await` throughout the stack.
5. **SOLID Compliance:** Single Responsibility, Open/Closed, Liskov Substitution, Interface Segregation, Dependency Inversion.

## Component Overview

### Core Components (`soni.core`)

**Purpose:** Foundation layer with domain types and infrastructure

- **`types.py`** - Core types: `DialogueState`, `FlowContext`, `SlotValue`
- **`commands.py`** - Command pattern: `StartFlow`, `EndFlow`, `UpdateSlot`, `ChitChat`
- **`pending_task.py`** - Task types: `CollectTask`, `ConfirmTask`, `InformTask`
- **`validation.py`** - Slot validation framework (type checking, regex, custom validators)
- **`expression.py`** - Expression evaluation for conditions and slot references
- **`state.py`** - State management utilities
- **`message_sink.py`** - Output abstraction (buffered, WebSocket)
- **`errors.py`** - Custom exception hierarchy

**Design Pattern:** Domain-Driven Design (DDD) - Pure domain model with no dependencies

### Dialogue Understanding (`soni.du`)

**Purpose:** NLU layer using DSPy for optimizable language understanding

- **`CommandGenerator`** - Extracts intents and generates dialogue commands
- **`SlotExtractor`** - Extracts slot values from user messages
- **`ResponseRephraser`** - Adjusts response tone (professional, casual, empathetic)

**Design Pattern:** Strategy Pattern (different DSPy modules for different NLU tasks)

**Optimization:** All modules use DSPy signatures, optimizable via MIPROv2

**Datasets:** Training data in `src/soni/du/datasets/` for optimization runs

### Dialogue Management (`soni.dm`)

**Purpose:** State machine execution using LangGraph

**Graph Structure:**
```
start → understand → orchestrator → execute → respond → END
                         ↓
                     (retry loop)
```

**Nodes:**
- **`understand_node`** - Calls CommandGenerator to extract intent
- **`orchestrator_node`** - Processes commands, manages flow stack
- **`execute_node`** - Invokes Python action handlers
- **`respond_node`** - Rephrases and sends response to user

**Design Pattern:** State Machine + Command Pattern

### Compiler (`soni.compiler`)

**Purpose:** Transforms YAML DSL into executable Python runtime

**Process:**
1. **Load** - Parse YAML files (`loaders.py`)
2. **Validate** - Schema validation (`validators/`)
3. **Transform** - AST transformation (`transforms/`)
4. **Build** - Create LangGraph StateGraph

**Design Pattern:** Interpreter Pattern + Builder Pattern

### Runtime (`soni.runtime`)

**Purpose:** Orchestrates the entire dialogue execution

- **`RuntimeLoop`** - Main orchestrator, delegates to specialized components
- **`RuntimeContext`** - Dependency injection container

**Design Pattern:** Facade Pattern + Dependency Injection

### Actions (`soni.actions`)

**Purpose:** Execute custom Python logic defined by developers

- **`ActionExecutor`** - Invokes action functions
- **`ActionRegistry`** - Registers and manages action handlers

**Design Pattern:** Registry Pattern + Dependency Injection

**Example:**
```python
# In examples/banking/handlers.py
async def execute_transfer(
    amount: float,
    beneficiary_name: str,
    runtime_context: RuntimeContext
) -> dict:
    # Custom business logic
    return {"success": True, "transaction_id": "TX123"}
```

### Flow Management (`soni.flow`)

**Purpose:** Manages flow stack and slot data

- **`FlowManager`** - Push/pop flows, get/set slots by `flow_id` (not `flow_name`)

**Design Pattern:** Stack Pattern + Immutable State (FlowDelta)

**Critical:** Uses `flow_id` (unique instance ID) not `flow_name` (definition name) for data access

### Server (`soni.server`)

**Purpose:** REST API and WebSocket interface

**Endpoints:**
- `POST /chat` - Synchronous dialogue turn
- `GET /stream` - SSE streaming (real-time tokens)
- `GET /health` - Health check
- `WS /ws` - WebSocket for bidirectional communication

**Design Pattern:** Adapter Pattern (FastAPI adapts domain logic to HTTP)

### CLI (`soni.cli`)

**Purpose:** Command-line tools for development and deployment

**Commands:**
- `soni chat` - Interactive REPL mode
- `soni server` - Start FastAPI server
- `soni optimize run` - Run DSPy optimization

**Design Pattern:** Command Pattern (Typer commands)

## Data Architecture

### State Management

**State Type:** `DialogueState` (TypedDict, required by LangGraph)

**Key Fields:**
- `messages: Annotated[list[AnyMessage], add_messages]` - Chat history
- `flow_stack: list[FlowContext]` - Active flow instances
- `flow_slots: dict[str, dict[str, Any]]` - Slot values keyed by `flow_id`
- `pending_task: PendingTask | None` - Current task awaiting user input
- `conversation_state: ConversationState` - Current phase (UNDERSTANDING, DELEGATING, etc.)

**Persistence:** SQLite via `langgraph-checkpoint-sqlite` for conversation checkpointing

### Flow State

**FlowContext:**
```python
class FlowContext(TypedDict):
    flow_id: str       # Unique instance ID (e.g., "book_flight_a3f7")
    flow_name: str     # Flow definition name
    current_step: str  # Current step in flow
    step_history: list[str]
```

**Immutable Updates:** All state mutations return `FlowDelta` objects merged into state by LangGraph

## API Design

### REST API

**Base URL:** `http://localhost:8000`

**POST /chat**
```json
{
  "user_id": "user-123",
  "message": "I want to transfer money"
}
```

**Response:**
```json
{
  "response": "Who would you like to send money to?",
  "conversation_id": "abc-123",
  "state": "collecting"
}
```

**GET /stream**
Server-Sent Events for real-time token streaming

## Development Workflow

### Local Setup

```bash
# Clone repository
git clone https://github.com/jmorenobl/soni.git
cd soni

# Install dependencies
uv sync

# Set API key
export OPENAI_API_KEY="your-key"

# Install pre-commit hooks
uv run pre-commit install
```

### Running the Framework

**Interactive Chat:**
```bash
uv run soni chat --config examples/banking/domain --module examples.banking.handlers
```

**API Server:**
```bash
uv run soni server --config examples/banking/domain --module examples.banking.handlers
```

### Testing

```bash
# All tests
uv run pytest

# Unit tests only
uv run pytest tests/unit/ -v

# Integration tests
uv run pytest tests/integration/ -v

# E2E tests (requires API key)
uv run pytest tests/e2e/ -v
```

**Coverage Targets:**
- Current: >30%
- MVP Goal: >60%

### Code Quality

```bash
# Lint
uv run ruff check .

# Format
uv run ruff format .

# Type check
uv run mypy src/soni
```

## Testing Strategy

| Level | Purpose | Location | Dependencies |
|-------|---------|----------|--------------|
| **Unit** | Component isolation | `tests/unit/` | Mocked |
| **Integration** | Cross-component behavior | `tests/integration/` | Real dependencies |
| **E2E** | Full dialogue scenarios | `tests/e2e/` | Requires LLM API key |

**Test Framework:** pytest + pytest-asyncio
**Mocking:** unittest.mock (AsyncMock for async functions)
**Parallel Execution:** pytest-xdist

## Deployment Architecture

### Production Deployment

**Recommended Stack:**
- **Application:** Soni FastAPI server
- **ASGI Server:** Uvicorn with `--workers` for multi-process
- **Reverse Proxy:** Nginx or Traefik
- **Container:** Docker

**Example Docker Deployment:**
```dockerfile
FROM python:3.11-slim
WORKDIR /app
COPY . .
RUN pip install uv && uv sync --no-dev
CMD ["uv", "run", "soni", "server", "--config", "domain", "--host", "0.0.0.0"]
```

### Environment Variables

- `OPENAI_API_KEY` - Required for LLM calls
- `SONI_LOG_LEVEL` - Logging level (default: INFO)
- `SONI_HOST` - Server host (default: 127.0.0.1)
- `SONI_PORT` - Server port (default: 8000)

## Performance Optimizations

1. **Caching** - DSPy LLM response caching (cachetools)
2. **Async I/O** - All I/O operations are async
3. **Connection Pooling** - httpx connection reuse
4. **Checkpointing** - Async SQLite checkpointing in LangGraph
5. **Dynamic Scoping** - Context-aware action filtering (39.5% token reduction)
6. **Slot Normalization** - Automatic normalization (11.11% validation improvement)

## Security Considerations

- **Input Validation:** Pydantic schemas validate all inputs
- **Slot Validation:** Custom validators prevent injection
- **API Keys:** Environment variables, never in code
- **Rate Limiting:** Recommended via reverse proxy (Nginx/Traefik)

## Future Architecture Plans

See `wiki/strategy/` for detailed roadmap:
- **RAG Integration** (v0.7.5) - Knowledge retrieval with vector stores
- **Optimization Pipeline** (v0.8.0) - Production-ready optimization workflows
- **TUI** (v0.9.0) - Terminal UI for monitoring
- **Event Architecture** (v1.0) - Async event bus

---

**For More Details:**
- [Source Tree Analysis](source-tree-analysis.md)
- [Development Guide](development-guide.md)
- [API Reference](reference/dsl-spec.md)
