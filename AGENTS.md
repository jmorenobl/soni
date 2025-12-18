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

### ChitChat Pattern (Digression Handling)
Digressions (questions outside flow, chitchat) are handled via the `ChitChat` command in `dm/nodes/command_registry.py`.

**Pattern**:
1. NLU detects out-of-flow intent → emits `ChitChat` command
2. `ChitChatHandler` generates response without modifying flow stack
3. Conversation continues in the active flow

**Critical**: Digressions do NOT modify the flow stack.

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

## Key Implementation Patterns

### FlowDelta Pattern (Immutable State Updates)
All state mutations in FlowManager return `FlowDelta` objects instead of mutating state:

```python
@dataclass
class FlowDelta:
    flow_stack: list[FlowContext] | None = None
    flow_slots: dict[str, dict[str, Any]] | None = None

# Usage
delta = flow_manager.push_flow(state, "book_flight")
merge_delta(updates, delta)  # Merge into node return dict
return updates  # LangGraph applies changes
```

### Two-Pass NLU Architecture
1. **Pass 1 (SoniDU):** Intent detection without slot definitions (avoids context overload)
2. **Pass 2 (SlotExtractor):** Slot value extraction, only if StartFlow detected

```python
# In understand_node:
nlu_result = await du.acall(user_message, context)  # Pass 1

if any(isinstance(cmd, StartFlow) for cmd in nlu_result.commands):
    slot_commands = await slot_extractor.acall(user_message, slot_defs)  # Pass 2
    commands.extend(slot_commands)
```

## Project Structure

```
src/soni/
├── core/              # Core abstractions (types, state, errors, commands)
├── du/                # Dialogue Understanding (DSPy-based NLU)
├── dm/                # Dialogue Management (LangGraph)
│   ├── nodes/         # LangGraph node implementations
│   └── patterns/      # Pattern handlers (correction, cancellation, etc.)
├── compiler/          # YAML → LangGraph compilation
├── config/            # Configuration loading
├── actions/           # Action system
├── flow/              # Flow state management (FlowManager)
├── runtime/           # Runtime orchestration (Loop, Hydrator, Extractor)
├── server/            # FastAPI server
├── cli/               # Typer CLI
├── dataset/           # Training data generation
└── utils/             # Utilities
```

## Detailed Guidelines (Obsolete - Not Updated - Do Not Follow)

For comprehensive implementation details, see:

- **Architecture & SOLID**: `.cursor/rules/001-architecture.mdc`
- **Code Style & Conventions**: `.cursor/rules/002-code-style.mdc`
- **Testing Patterns**: `.cursor/rules/003-testing.mdc`
- **DSPy Integration**: `.cursor/rules/004-dspy.mdc`
- **LangGraph Patterns**: `.cursor/rules/005-langgraph.mdc`
- **State Management**: `.cursor/rules/006-state.mdc`
- **YAML DSL**: `.cursor/rules/007-yaml-dsl.mdc`
- **Deployment & Tools**: `.cursor/rules/008-deployment.mdc`

## Design Documentation (Obsolete - Not Updated - Do Not Follow)

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
uv run pytest                           # Run all tests
uv run pytest tests/unit/ -v            # Unit tests only
uv run pytest tests/integration/ -v     # Integration tests
uv run ruff check . && ruff format .    # Lint & format
uv run mypy src/soni                    # Type check

# Server
uv run soni server --config examples/banking/domain

# Interactive Chat
uv run soni chat --config examples/banking/domain \
    --module examples.banking.handlers

# Optimization
uv run soni optimize run --config examples/banking/domain

# Validation
uv run python scripts/validate_flows.py examples/banking/
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
