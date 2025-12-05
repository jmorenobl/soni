# Soni Framework - Agent Instructions

**Quick Overview**: Conversational dialogue system with automatic DSPy prompt optimization and LangGraph execution.

## Core Principles

### Architecture
- **Zero-Leakage (Hexagonal)**: YAML describes WHAT, Python implements HOW
- **SOLID Compliance**: SRP, OCP, LSP, ISP, DIP throughout codebase
- **Async-First**: All I/O operations must be `async def`
- **Pure Data**: TypedDict for state, serialize complex objects with `.model_dump()`

### Language
- **English Only**: All documentation, code, comments, commits, and errors in English

## Key Components

### RuntimeLoop (Orchestrator)
Main orchestrator - delegates to specialized components, no business logic.

### FlowManager (SRP)
Dedicated class for flow stack management (push/pop/get/set slots).

**Critical**: Use `flow_id` (unique instance) not `flow_name` (definition) for data access.

### DigressionHandler (Coordinator)
Coordinates question/help handling. **Does NOT modify flow stack**.

### SoniDU (DSPy Module)
NLU module with structured types (NLUOutput, DialogueContext, SlotValue).

## Critical Patterns

### 1. Every Message Through NLU First
```
User Message → RuntimeLoop → Check State → ALWAYS: Understand Node (NLU)
  ↓
Conditional Routing:
  ├─ Slot Value → Validate
  ├─ Digression → DigressionHandler (NO stack change)
  ├─ Intent Change → Push/Pop Flow (stack change)
  └─ Continue → Next Step
```

### 2. flow_id vs flow_name
```python
# ✅ CORRECT
active_ctx = flow_manager.get_active_context(state)
flow_id = active_ctx["flow_id"]  # "book_flight_3a7f"
slots = state["flow_slots"][flow_id]

# ❌ WRONG
flow_name = active_ctx["flow_name"]  # "book_flight"
slots = state["flow_slots"][flow_name]  # FAILS with multiple instances
```

### 3. TypedDict for State
```python
# ✅ CORRECT - LangGraph requirement
class DialogueState(TypedDict):
    messages: Annotated[list[AnyMessage], add_messages]
    flow_stack: list[FlowContext]
    # ...

# ❌ WRONG
class DialogueState(BaseModel):  # Pydantic not supported
```

### 4. Serialization Pattern
```python
# ✅ CORRECT
return {
    "nlu_result": nlu_result.model_dump(),  # Serialize
    "conversation_state": ConversationState.UNDERSTANDING.value  # Enum to string
}

# ❌ WRONG
return {
    "nlu_result": nlu_result,  # Object (not JSON-serializable)
}
```

### 5. Dependency Injection
```python
# Use RuntimeContext in nodes
async def understand_node(
    state: DialogueState,
    context: RuntimeContext
) -> dict[str, Any]:
    flow_manager = context.flow_manager  # Access dependencies
    nlu_provider = context.nlu_provider
```

## Project Structure

```
src/soni/
├── core/          # Interfaces, state, errors, types, config
├── du/            # Dialogue Understanding (DSPy modules)
├── dm/            # Dialogue Management (LangGraph)
│   └── nodes/     # LangGraph node implementations (package)
├── compiler/      # YAML to Graph compilation
├── actions/       # Action Registry
├── validation/    # Validator Registry
├── server/        # FastAPI
├── cli/           # CLI commands
├── config/        # Configuration package
├── flow/          # FlowManager
├── observability/ # Logging
├── runtime/       # RuntimeLoop and managers
└── utils/         # Utilities
```

## Detailed Guidelines

For comprehensive implementation details, see:

- **Architecture & SOLID**: `.cursor/rules/001-architecture.mdc`
- **Code Style & Conventions**: `.cursor/rules/002-code-style.mdc`
- **Testing Patterns**: `.cursor/rules/003-testing.mdc`
- **DSPy Integration**: `.cursor/rules/004-dspy.mdc`
- **LangGraph Patterns**: `.cursor/rules/005-langgraph.mdc`
- **State Management**: `.cursor/rules/006-state.mdc`
- **YAML DSL**: `.cursor/rules/007-yaml-dsl.mdc`
- **Deployment & Tools**: `.cursor/rules/008-deployment.mdc`

## Design Documentation

Complete architectural details:
- **Index**: `docs/design/README.md`
- **Architecture**: `docs/design/02-architecture.md`
- **Components**: `docs/design/03-components.md`
- **State Machine**: `docs/design/04-state-machine.md`
- **Message Flow**: `docs/design/05-message-flow.md`
- **NLU System**: `docs/design/06-nlu-system.md`
- **Flow Management**: `docs/design/07-flow-management.md`
- **LangGraph Integration**: `docs/design/08-langgraph-integration.md`
- **DSPy Optimization**: `docs/design/09-dspy-optimization.md`
- **DSL Specification**: `docs/design/10-dsl-specification/`

## Quick Reference Commands

```bash
# Setup
uv sync
uv run pre-commit install

# Development
uv run pytest                    # Run tests
uv run ruff check . && ruff format .  # Lint & format
uv run mypy src/soni            # Type check

# Validation
uv run python scripts/validate_config.py examples/flight_booking/soni.yaml
uv run python scripts/validate_runtime.py

# Server
uv run soni server --config examples/flight_booking/soni.yaml

# Optimization
uv run soni optimize --config examples/flight_booking/soni.yaml
```

## Important Reminders

1. **English Only**: All text in English
2. **Async-first**: Everything must be `async def`
3. **Type hints**: Mandatory with modern Python 3.11+ syntax
4. **SOLID Principles**: Follow SRP, OCP, LSP, ISP, DIP
5. **Pure Data**: TypedDict for state, serialize before storing
6. **flow_id not flow_name**: Use flow_id for instance identity
7. **No Retrocompatibility Pre-v1.0**: Focus on correct design

---

**Version**: 1.0 (Hybrid)
**Last Updated**: 2025-12-05
**Status**: Production-ready with modular .mdc rules
