# Architecture Guide - Soni Framework

This document provides an overview of the Soni Framework architecture.

## Overview

Soni is a conversational dialogue framework that combines:
- **DSPy** for automatic prompt optimization (NLU)
- **LangGraph** for dialogue management (state machines)
- **YAML DSL** for declarative dialogue configuration

## Core Components

### 1. Dialogue Understanding (DU)

The DU module uses DSPy to understand user intents and extract slots from natural language.

**Key Files:**
- `src/soni/du/modules.py` - SoniDU module
- `src/soni/du/signatures.py` - DSPy signatures
- `src/soni/du/optimizers.py` - Optimization pipeline

**How it works:**
1. User message is processed by SoniDU
2. DSPy predicts intent and extracts slots
3. Result is passed to dialogue manager

### 2. Dialogue Management (DM)

The DM module uses LangGraph to manage dialogue state and flow.

**Key Files:**
- `src/soni/dm/graph.py` - Graph builder (orchestration)
- `src/soni/dm/validators.py` - Flow validation
- `src/soni/dm/nodes.py` - Node factory functions
- `src/soni/dm/persistence.py` - Checkpointer factory
- `src/soni/dm/routing.py` - Routing logic
- `src/soni/compiler/flow_compiler.py` - YAML to DAG compiler
- `src/soni/compiler/dag.py` - DAG structures
- `src/soni/core/state.py` - DialogueState and RuntimeContext

**How it works:**
1. FlowCompiler compiles YAML to intermediate DAG
2. Graph builder constructs LangGraph from DAG
3. State is managed by LangGraph checkpointing
4. Nodes execute steps (collect slots, call actions)

### 3. Runtime Loop

The runtime loop orchestrates DU and DM to process conversations.

**Key Files:**
- `src/soni/runtime/runtime.py` - RuntimeLoop (orchestration)
- `src/soni/runtime/config_manager.py` - Configuration management
- `src/soni/runtime/conversation_manager.py` - Multi-user state management
- `src/soni/runtime/streaming_manager.py` - Streaming responses

**How it works:**
1. ConfigurationManager loads and validates config
2. User message arrives
3. ConversationManager loads/creates state for user
4. Graph executes with current state
5. StreamingManager streams events (if streaming)
6. Response is extracted and returned

### 4. Configuration System

YAML configuration defines dialogue structure declaratively.

**Key Files:**
- `src/soni/core/config.py` - ConfigLoader
- `examples/flight_booking/soni.yaml` - Example config

**Structure:**
- `flows`: Define dialogue flows with steps
- `slots`: Define entities to collect
- `actions`: Define external handlers

## Data Flow

```
User Message
    ↓
RuntimeLoop.process_message()
    ↓
SoniDU.predict() → NLUResult
    ↓
DialogueState updated
    ↓
LangGraph execution
    ↓
Action handlers called
    ↓
Response generated
    ↓
State persisted
    ↓
Response returned
```

## State Management

Dialogue state is managed by LangGraph's checkpointing system:
- State is persisted between turns
- Each user has independent state
- State includes: messages, slots, current flow

### RuntimeContext Pattern

v0.3.0 introduces `RuntimeContext` to cleanly separate state from configuration:

**DialogueState** (Pure, Serializable):
- Contains only runtime state: messages, slots, current flow
- No configuration or dependencies
- Can be safely serialized/deserialized for checkpointing

**RuntimeContext** (Configuration & Dependencies):
- Contains: config, scope_manager, normalizer, action_handler, du (NLU provider)
- Passed to node factories via closures
- Never serialized - exists only during graph execution

**Example:**
```python
# Creating RuntimeContext
context = RuntimeContext(
    config=soni_config,
    scope_manager=scope_mgr,
    normalizer=normalizer,
    action_handler=handler,
    du=nlu_provider,
)

# Using in node factory
def create_my_node(context: RuntimeContext):
    async def my_node(state: DialogueState) -> DialogueState:
        # Access config via context
        slot_config = context.get_slot_config("my_slot")
        # Process state...
        return state
    return my_node
```

This pattern ensures:
- Clean separation of concerns
- State remains serializable
- Dependencies can be mocked for testing
- No "config hacks" in state

## Extension Points

### Adding Actions

Actions are Python functions that implement business logic:

```python
async def my_action(param: str) -> dict:
    return {"result": f"Processed {param}"}
```

### Adding Validators

Validators check slot values using the ValidatorRegistry:

```python
from soni.validation.registry import ValidatorRegistry

@ValidatorRegistry.register("my_validator")
def validate_my_field(value: str) -> bool:
    return value.startswith("prefix")
```

Validators are automatically registered when imported. Reference them in YAML by name:

```yaml
slots:
  my_slot:
    type: string
    validator: my_validator
```

### Adding Actions

Actions implement business logic using the ActionRegistry:

```python
from soni.actions.registry import ActionRegistry

@ActionRegistry.register("my_action")
async def my_action(param: str) -> dict[str, Any]:
    return {"result": f"Processed {param}"}
```

Actions are automatically registered when imported. Reference them in YAML by name:

```yaml
actions:
  my_action:
    inputs:
      - param
    outputs:
      - result
```

### Dependency Injection

All components support dependency injection via Protocols:

```python
from soni.core.interfaces import IScopeManager, INLUProvider
from soni.runtime import RuntimeLoop

# Inject custom implementations
runtime = RuntimeLoop(
    config_path="config.yaml",
    scope_manager=my_scope_manager,
    nlu_provider=my_nlu_provider,
)
```

This enables:
- Easy testing with mocks
- Swapping implementations
- Following SOLID principles

## Architecture Evolution

### v0.3.0 (Current) - Architectural Refactoring

**Completed:**
- ✅ Dependency Injection (100% Protocol-based)
- ✅ RuntimeContext pattern
- ✅ ValidatorRegistry and ActionRegistry
- ✅ Modular architecture (0 God Objects)
- ✅ FlowCompiler and DAG intermediate representation
- ✅ 80%+ test coverage maintained

**Metrics:**
- Overall Quality: 9.2/10 (was 7.8/10)
- Architecture Score: 95/100 (was 56/100)
- Dependency Inversion: 100% (was 0%)
- God Objects: 0 (was 2)

### Current Limitations

- Linear flows only (no branching) - *Planned for v0.4.0*
- Limited jump support - *Planned for v0.4.0*
- Basic procedural DSL - *Full Zero-Leakage in v0.4.0*

## Future Architecture

See [ADR-001](adr/ADR-001-Soni-Framework-Architecture.md) for the complete architecture vision, including:
- Zero-Leakage Architecture (v0.4.0)
- Advanced branching and jumps (v0.4.0)
- Complete Action/Validator Registry integration (v0.4.0)
