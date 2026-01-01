# Soni Framework - Project Overview

**Generated:** 2026-01-01
**Project Type:** Python Library/Framework
**Architecture:** Modular conversational AI framework

## Executive Summary

Soni is an open-source conversational AI framework that combines DSPy for prompt optimization with LangGraph for robust dialogue management. It provides a declarative YAML-based DSL for defining dialogue flows, with automatic optimization capabilities and async-first architecture.

## Technology Stack Summary

| Category | Technology | Version | Purpose |
|----------|------------|---------|---------|
| **Language** | Python | 3.11+ | Core implementation |
| **NLU/Optimization** | DSPy | ≥3.0.4 | Prompt optimization (MIPROv2) |
| **Dialogue Management** | LangGraph | ≥1.0.4 | State machine & graph execution |
| **Web Framework** | FastAPI | ≥0.122.0 | REST API & streaming |
| **Data Validation** | Pydantic | ≥2.12.5 | Schema validation & serialization |
| **CLI** | Typer | ≥0.15.0 | Command-line interface |
| **Testing** | Pytest | ≥9.0.1 | Unit & integration tests |
| **Code Quality** | Ruff + Mypy | Latest | Linting & type checking |
| **Documentation** | MkDocs Material | ≥9.5.0 | Documentation site |

## Repository Structure

**Type:** Monolithic Python package
**Entry Point:** `src/soni/cli/main.py` (CLI) and `src/soni/server/main.py` (API Server)

### Core Packages

- **soni.core** - Core domain types, state management, validation
- **soni.du** - Dialogue Understanding (DSPy modules for NLU)
- **soni.dm** - Dialogue Management (LangGraph nodes & orchestration)
- **soni.compiler** - YAML DSL compiler
- **soni.config** - Configuration management
- **soni.server** - FastAPI REST API & WebSocket support
- **soni.cli** - Typer-based command-line tools
- **soni.actions** - Action execution framework
- **soni.flow** - Flow state management
- **soni.runtime** - Runtime loop orchestration
- **soni.dataset** - Training dataset management

## Architecture Type

**Pattern:** Hexagonal Architecture (Ports & Adapters)
**Style:** Event-driven dialogue system with declarative configuration

- Configuration layer (YAML DSL) → Compiler → Runtime graph
- Clean separation: YAML defines WHAT, Python implements HOW
- Zero-leakage: Technical details don't leak into configuration
- Async-first: All I/O operations use `async/await`

## Development Workflow

### Prerequisites
- Python 3.11+
- OpenAI API key (or compatible LLM provider)
- `uv` package manager (recommended)

### Local Development
```bash
# Install
uv sync

# Run tests
uv run pytest

# Start server
uv run soni server --config examples/banking/domain

# Interactive chat
uv run soni chat --config examples/banking/domain --module examples.banking.handlers
```

## Testing Strategy

- **Unit Tests:** `/tests/unit/` - Component-level testing
- **Integration Tests:** `/tests/integration/` - Cross-component testing
- **E2E Tests:** `/tests/e2e/` - End-to-end dialogue scenarios
- **Coverage Target:** >30% (current), >60% (MVP goal)
- **Test Runner:** pytest with async support

## Links to Detailed Documentation

- [Architecture](architecture.md)
- [Development Guide](development-guide.md)
- [Source Tree Analysis](source-tree-analysis.md)
- [API Reference](docs/reference/dsl-spec.md)

## Project Metadata

- **License:** MIT
- **Python Version:** ≥3.11
- **Current Version:** 0.4.0
- **Status:** Alpha (Experimental)
- **Repository:** https://github.com/jmorenobl/soni
