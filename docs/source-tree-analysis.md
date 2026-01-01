# Soni Framework - Source Tree Analysis

**Generated:** 2026-01-01

## Directory Structure

```
soni/
├── src/soni/                    # Main package source code
│   ├── __init__.py             # Package initialization
│   ├── __version__.py          # Version management
│   ├── core/                   # ⭐ Core domain types & infrastructure
│   │   ├── commands.py         # Command types (StartFlow, EndFlow, UpdateSlot, etc.)
│   │   ├── types.py            # DialogueState, FlowContext, SlotValue
│   │   ├── pending_task.py     # Task types (collect, confirm, inform)
│   │   ├── validation.py       # Slot validation framework
│   │   ├── expression.py       # Expression evaluation (conditions, slots)
│   │   ├── state.py            # State management utilities
│   │   ├── message_sink.py     # Message output abstractions
│   │   ├── dspy_service.py     # DSPy LLM configuration
│   │   └── errors.py           # Custom exceptions
│   ├── du/                     # ⭐ Dialogue Understanding (DSPy NLU)
│   │   ├── modules/            # DSPy modules for NLU tasks
│   │   │   ├── extract_commands.py    # CommandGenerator (intent → commands)
│   │   │   ├── extract_slots.py       # SlotExtractor (extract slot values)
│   │   │   └── rephrase_response.py   # ResponseRephraser (tone adjustment)
│   │   ├── schemas/            # Pydantic schemas for NLU I/O
│   │   ├── optimized/          # Optimized prompts (saved after DSPy optimization)
│   │   └── datasets/           # Training datasets for optimization
│   ├── dm/                     # ⭐ Dialogue Management (LangGraph execution)
│   │   ├── builder.py          # LangGraph StateGraph construction
│   │   ├── nodes/              # Graph nodes (understand, orchestrator, execute, respond)
│   │   ├── orchestrator/       # Command handling & flow management
│   │   └── routing.py          # Conditional edge routing
│   ├── compiler/               # ⭐ YAML → Runtime compilation
│   │   ├── compiler.py         # Main compiler entry point
│   │   ├── loaders.py          # YAML file loading
│   │   ├── validators/         # Schema validation
│   │   └── transforms/         # AST transformations
│   ├── config/                 # Configuration management
│   │   ├── loader.py           # Config file loading
│   │   └── schema.py           # Config schemas
│   ├── actions/                # Action execution framework
│   │   ├── executor.py         # Action invocation
│   │   └── registry.py         # Action registration
│   ├── flow/                   # Flow state management
│   │   └── manager.py          # FlowManager (push/pop flows, slot access)
│   ├── runtime/                # Runtime orchestration
│   │   ├── loop.py             # RuntimeLoop (main orchestrator)
│   │   └── context.py          # RuntimeContext (dependency injection)
│   ├── server/                 # ⭐ FastAPI REST API & WebSocket
│   │   ├── main.py             # Server entry point
│   │   ├── app.py              # FastAPI app creation
│   │   ├── routes.py           # HTTP endpoints (/chat, /health, /stream)
│   │   └── websocket.py        # WebSocket support
│   └── cli/                    # ⭐ Typer CLI
│       ├── main.py             # CLI entry point
│       ├── chat.py             # Interactive chat mode
│       ├── server.py           # Server commands
│       └── optimize.py         # Optimization commands
│
├── examples/                   # Example dialogue systems
│   └── banking/                # Complete banking assistant example
│       ├── domain/             # YAML flow definitions
│       │   └── soni.yaml       # Main configuration
│       └── handlers.py         # Python action handlers
│
├── tests/                      # Test suite
│   ├── unit/                   # Unit tests (per module)
│   │   ├── core/
│   │   ├── du/
│   │   ├── dm/
│   │   └── compiler/
│   ├── integration/            # Integration tests (cross-module)
│   └── e2e/                    # End-to-end dialogue scenarios
│
├── docs/                       # 📚 Documentation (Output folder)
│   ├── tutorials/              # Step-by-step guides
│   ├── how-to/                 # Problem-solving guides
│   ├── reference/              # Technical specifications
│   └── explanation/            # Concepts & architecture
│
├── wiki/                       # Technical wiki (Internal)
│   ├── adr/                    # Architectural Decision Records
│   ├── prd/                    # Product Requirements
│   └── strategy/               # Strategic planning docs
│
├── scripts/                    # Utility scripts
│   └── generate_baseline_optimization.py
│
├── _bmad/                      # BMad workflow framework (meta-development)
│
├── pyproject.toml              # ⭐ Project configuration & dependencies
├── uv.lock                     # Dependency lock file
├── mkdocs.yml                  # Documentation site configuration
├── Makefile                    # Common development tasks
├── .pre-commit-config.yaml     # Pre-commit hook configuration
├── README.md                   # Project README
└── CONTRIBUTING.md             # Contribution guidelines
```

## Critical Directories

### Entry Points

1. **`src/soni/cli/main.py`**
   - CLI entry point (`soni` command)
   - Commands: `chat`, `server`, `optimize`

2. **`src/soni/server/main.py`**
   - FastAPI server entry point
   - Endpoints: `/chat`, `/stream`, `/health`

3. **`pyproject.toml`**
   - Defines `[project.scripts]` entry point: `soni = "soni.cli.main:cli"`

### Core Framework Modules

- **`src/soni/core/`** - Foundation layer (types, validation, state)
- **`src/soni/du/`** - NLU layer (DSPy modules for intent & slot extraction)
- **`src/soni/dm/`** - Dialogue management (LangGraph nodes & orchestration)
- **`src/soni/compiler/`** - DSL compilation (YAML → Python runtime)
- **`src/soni/runtime/`** - Orchestration (RuntimeLoop coordinates everything)

### Integration Points

#### External APIs
- **DSPy** - Used in `soni.du` for NLU optimization
- **LangGraph** - Used in `soni.dm` for state graph execution
- **FastAPI** - Used in `soni.server` for REST API
- **Typer** - Used in `soni.cli` for CLI interface

#### Internal Flow
```
User Message → RuntimeLoop → LangGraph Execute:
  ├─ understand_node (soni.du.CommandGenerator)
  ├─ orchestrator_node (soni.dm.orchestrator)
  ├─ execute_node (soni.actions)
  └─ respond_node (soni.du.ResponseRephraser)
```

### Configuration Management

- **YAML DSL** - Located in `examples/{domain}/domain/soni.yaml`
- **Python Handlers** - Action implementations in `examples/{domain}/handlers.py`
- **Compiled Runtime** - Compiler creates LangGraph from YAML definitions

### Test Organization

- **Unit:** Isolated component testing (`tests/unit/`)
- **Integration:** Cross-component testing (`tests/integration/`)
- **E2E:** Full dialogue scenario testing (`tests/e2e/`, requires API key)

### Documentation Structure

- **User Docs** (`docs/`) - Public-facing documentation (MkDocs format)
- **Internal Docs** (`wiki/`) - ADRs, PRDs, strategic planning
- **Code Docs** - Inline docstrings (Google style)

## Asset Locations

- **Optimized Prompts:** `src/soni/du/optimized/*.json`
- **Training Data:** `src/soni/du/datasets/*.json`
- **State Database:** `banking_state.db` (example runtime state)

## Development Files

- **`.venv/`** - Virtual environment (created by `uv`)
- **`.pytest_cache/`** - Pytest cache
- **`.ruff_cache/`** - Ruff linter cache
- **`.mypy_cache/`** - Mypy type checker cache
- **`htmlcov/`** - Coverage reports

## Key File Patterns

| Pattern | Purpose |
|---------|---------|
| `**/test_*.py` | Unit/integration tests |
| `**/*_test.py` | Alternative test naming |
| `examples/*/handlers.py` | Action handler implementations |
| `examples/*/domain/soni.yaml` | Flow definitions |
| `.env`, `.env.example` | Environment variables (API keys) |
| `pyproject.toml` | Dependencies, build config, tool settings |
| `Makefile` | Common dev tasks (test, lint, format, etc.) |
