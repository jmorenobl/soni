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
- `src/soni/dm/graph.py` - Graph builder
- `src/soni/core/state.py` - DialogueState

**How it works:**
1. Graph is built from YAML configuration
2. State is managed by LangGraph checkpointing
3. Nodes execute steps (collect slots, call actions)

### 3. Runtime Loop

The runtime loop orchestrates DU and DM to process conversations.

**Key Files:**
- `src/soni/runtime.py` - RuntimeLoop

**How it works:**
1. User message arrives
2. RuntimeLoop loads state for user
3. Graph executes with current state
4. Response is extracted and returned

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

## Extension Points

### Adding Actions

Actions are Python functions that implement business logic:

```python
async def my_action(param: str) -> dict:
    return {"result": f"Processed {param}"}
```

### Adding Validators

Validators check slot values (implementation in v0.4.0):

```python
@ValidatorRegistry.register("my_validator")
def validate_my_field(value: str) -> bool:
    return value.startswith("prefix")
```

## MVP Limitations

The MVP (v0.1.0) has these limitations:
- Linear flows only (no branching)
- No explicit jumps
- Validators referenced by name only
- Action handlers by Python path (not registry)

These will be addressed in future versions.

## Future Architecture

See [ADR-001](adr/ADR-001-Soni-Framework-Architecture.md) for the complete architecture vision, including:
- Zero-Leakage Architecture (v0.4.0)
- Step Compiler (v0.3.0)
- Action/Validator Registries (v0.4.0)
