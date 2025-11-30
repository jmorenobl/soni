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

### Compiler Architecture

The compiler has two main components:

1. **FlowCompiler** (`compiler/flow_compiler.py`):
   - `compile_flow()`: Compiles YAML to intermediate DAG representation
     - Use when you need the DAG for validation, transformation, or inspection
     - Returns `FlowDAG` intermediate representation
   - `compile_flow_to_graph()`: Compiles YAML directly to StateGraph
     - Use when you need a ready-to-use StateGraph for execution
     - Returns `StateGraph[DialogueState]` ready for compilation

2. **SoniGraphBuilder** (`dm/graph.py`):
   - Uses `compile_flow()` + `_build_from_dag()` to inject RuntimeContext
   - Controls graph construction with dependencies (checkpointer, context)
   - Separates YAML-to-DAG translation from graph construction
   - Why not use `compile_flow_to_graph()` directly?
     - Needs to inject RuntimeContext into nodes
     - Requires custom node creation with context
     - Maintains separation of concerns (compiler vs builder)

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
- **Always required** in node factory functions

**Usage Pattern:**

1. `SoniGraphBuilder` creates `RuntimeContext` with all dependencies
2. Factory functions in `nodes.py` receive `RuntimeContext` as required parameter
3. Nodes access config and dependencies through `RuntimeContext`

**Why Always Required?**

- Simplifies code (no need to handle None case)
- Makes dependencies explicit
- Consistent with Dependency Injection pattern
- Provides access to config for normalization and validation

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

# Using in node factory (context is always required)
def create_my_node(
    scope_manager: IScopeManager,
    normalizer: INormalizer,
    nlu_provider: INLUProvider,
    context: RuntimeContext,  # Always required
):
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

### Adding Validators (Zero-Leakage Architecture)

Validators check slot values using the ValidatorRegistry. This follows zero-leakage architecture: YAML uses semantic names, regex patterns live in Python code.

**Registering Validators:**

```python
from soni.validation.registry import ValidatorRegistry
import re

@ValidatorRegistry.register("city_name")
def validate_city(value: str) -> bool:
    """Validate city name format."""
    # Regex lives here, not in YAML
    return bool(re.match(r"^[A-Za-z\s]+$", value)) and len(value) >= 2
```

**YAML Configuration (Semantic, No Regex Patterns):**

```yaml
slots:
  origin:
    type: string
    prompt: "Which city?"
    # Semantic validator name, not regex pattern
    # Zero-leakage: YAML only describes WHAT, not HOW
    validator: city_name
```

**Built-in Validators:**

The framework includes common validators (automatically registered):
- `city_name`: Validates city name format
- `future_date_only`: Validates date is in the future
- `iata_code`: Validates IATA airport code (3 uppercase letters)
- `booking_reference`: Validates booking reference format (6 alphanumeric)

**Custom Validators:**

Create custom validators by registering them:

```python
@ValidatorRegistry.register("my_custom_validator")
def validate_custom(value: str) -> bool:
    """Custom validation logic."""
    return len(value) > 10
```

Validators are automatically registered when the module is imported. Reference them in YAML by semantic name only.

### Adding Actions (Zero-Leakage Architecture)

Actions implement business logic using the ActionRegistry. This follows zero-leakage architecture: YAML defines contracts (inputs/outputs), Python implements handlers.

**Registering Actions:**

```python
from soni.actions.registry import ActionRegistry
from typing import Any

@ActionRegistry.register("my_action")
async def my_action(param: str) -> dict[str, Any]:
    """Process user input."""
    return {"result": f"Processed {param}"}
```

**YAML Configuration (Semantic, No Python Paths):**

```yaml
actions:
  my_action:
    description: "Process user input"
    # No handler path needed - registered via decorator
    # Zero-leakage: YAML only describes WHAT, not HOW
    inputs:
      - param
    outputs:
      - result
```

**Auto-Discovery:**

The runtime automatically discovers and imports action modules from the config directory:
- `actions.py` in the config directory
- `actions/__init__.py` in the config directory

Simply import your actions module (e.g., `import handlers`), and actions will be registered automatically via the `@ActionRegistry.register()` decorator.

**Example Structure:**

```
examples/my_app/
  ├── soni.yaml          # Config with action contracts
  ├── handlers.py        # Actions registered via decorator
  └── __init__.py        # Optional: imports handlers
```

When `RuntimeLoop` is initialized with `config_path="examples/my_app/soni.yaml"`, it automatically imports `handlers.py` and registers all actions.

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

## Type Hints Guidelines

### When to use `Any`

The framework uses `Any` in type hints when:
- LangGraph internal types that are not publicly exposed
- Complex function types that are difficult to express in Python
- The actual type is documented in comments/docstrings

### Best Practices

1. **Always add a comment explaining the real type:**
   ```python
   def function() -> Any:  # Returns: StateGraph[DialogueState]
   ```

2. **Document the type in docstring:**
   ```python
   """
   Returns:
       StateGraph ready for execution.
       Type: StateGraph[DialogueState] (annotated as Any due to LangGraph internals)
   """
   ```

3. **Use TypeAlias for reusable complex types (if applicable):**
   ```python
   from typing import TypeAlias

   # Type alias for LangGraph node function return type
   StateUpdate: TypeAlias = dict[str, Any]
   ```

4. **Use `TYPE_CHECKING` for imports only used in type hints:**
   ```python
   from typing import TYPE_CHECKING

   if TYPE_CHECKING:
       from langgraph.graph import StateGraph
   ```

### Examples in Codebase

- `FlowCompiler.compile_flow_to_graph()`: Returns `StateGraph[DialogueState]` (annotated as `Any`)
- `create_understand_node()`: Returns async function (annotated as `Any`)
- `_create_node_function_from_dag()`: Returns LangGraph node function (annotated as `Any`)

All these cases include comments and docstrings explaining the actual return type.

## Future Architecture

See [ADR-001](adr/ADR-001-Soni-Framework-Architecture.md) for the complete architecture vision, including:
- Zero-Leakage Architecture (v0.4.0)
- Advanced branching and jumps (v0.4.0)
- Complete Action/Validator Registry integration (v0.4.0)
