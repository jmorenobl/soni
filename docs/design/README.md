# Soni Framework - Design Documentation v2.0

This directory contains the complete design documentation for Soni v2.0, a conversational dialogue system with **Command-Driven Architecture** and automatic prompt optimization.

## What's New in v2.0

- **Command Layer**: Explicit contract between DU and DM
- **Handler Registry**: SOLID-compliant command execution
- **Conversation Patterns**: Declarative non-happy-path handling
- **Deterministic DM**: LLM interprets, DM executes deterministically

## Quick Start

New to Soni? Start here:

1. **[01-overview.md](01-overview.md)** - What is Soni and command-driven architecture
2. **[02-architecture.md](02-architecture.md)** - Core architectural principles and Handler Registry
3. **[03-components.md](03-components.md)** - Commands, Handlers, Executor, and other components

For detailed technical design:

4. **[04-state-machine.md](04-state-machine.md)** - Dialogue state and command-driven transitions
5. **[05-message-flow.md](05-message-flow.md)** - NLU → Commands → Executor flow
6. **[06-nlu-system.md](06-nlu-system.md)** - DSPy NLU with Command output
7. **[07-flow-management.md](07-flow-management.md)** - Flow stack and command-driven operations
8. **[08-langgraph-integration.md](08-langgraph-integration.md)** - LangGraph patterns and usage
9. **[09-dspy-optimization.md](09-dspy-optimization.md)** - Prompt optimization with DSPy
10. **[10-dsl-specification/](10-dsl-specification/)** - DSL Specification (multi-document)
11. **[11-commands.md](11-commands.md)** - Complete Command layer specification
12. **[12-conversation-patterns.md](12-conversation-patterns.md)** - Conversation Patterns reference

## Document Overview

| Document | Purpose | Key Topics |
|----------|---------|------------|
| [01-overview](01-overview.md) | System introduction | Command-driven architecture, features |
| [02-architecture](02-architecture.md) | Architectural design | Handler Registry, SOLID principles |
| [03-components](03-components.md) | Component details | Commands, Handlers, Executor, Registry |
| [04-state-machine](04-state-machine.md) | State management | DialogueState, command_log, transitions |
| [05-message-flow](05-message-flow.md) | Message processing | NLU→Commands→DM pipeline |
| [06-nlu-system](06-nlu-system.md) | NLU system | DSPy module, Command extraction |
| [07-flow-management](07-flow-management.md) | Flow operations | Stack operations via Commands |
| [08-langgraph](08-langgraph-integration.md) | Graph execution | Checkpointing, interrupt patterns |
| [09-dspy](09-dspy-optimization.md) | Optimization | Signatures, metrics, training |
| [10-dsl](10-dsl-specification/) | DSL specification | YAML schema, step types |
| [11-commands](11-commands.md) | Command layer | All command types and handlers |
| [12-patterns](12-conversation-patterns.md) | Conv. patterns | Correction, Clarification, etc. |

## Key Concepts

### Command-Driven Architecture

```
User Message → NLU (LLM) → Commands → CommandExecutor → DM State Machine
                 ↑                         ↑
            Interprets only          Deterministic execution
```

- **NLU produces Commands**: Pure data objects representing user intent
- **CommandExecutor executes**: Via Handler Registry (OCP)
- **DM routes on state**: Not on LLM classification

### Commands

| Command | Purpose |
|---------|---------|
| `StartFlow` | Start a new flow |
| `SetSlot` | Set a slot value |
| `CorrectSlot` | Correct a previous value |
| `CancelFlow` | Cancel current flow |
| `Clarify` | Request clarification |
| `AffirmConfirmation` | Confirm action |
| `DenyConfirmation` | Deny and optionally specify slot |
| `HumanHandoff` | Request human agent |

### Handler Registry (SOLID)

```python
registry = {
    StartFlow: StartFlowHandler(),
    SetSlot: SetSlotHandler(),
    # New command = new entry (OCP)
}

for command in commands:
    handler = registry[type(command)]
    updates = await handler.execute(command, state, context)
```

### Conversation Patterns

Declarative handling of non-happy-path:
- **Correction**: Update previous values
- **Clarification**: Answer questions without leaving flow
- **Cancellation**: Cancel current flow
- **Human Handoff**: Escalate to human agent

### Zero-Leakage Architecture

YAML describes **WHAT** (semantics), Python implements **HOW** (logic):
- Business analysts can configure flows without coding
- Technical implementation stays in Python code
- Clear separation of concerns

## Reading Paths

### For Developers Implementing Soni

1. [02-architecture.md](02-architecture.md) - Understand command-driven design
2. [03-components.md](03-components.md) - Learn Commands, Handlers, Executor
3. [11-commands.md](11-commands.md) - Complete command specification
4. [05-message-flow.md](05-message-flow.md) - Implement message processing
5. [08-langgraph-integration.md](08-langgraph-integration.md) - Master LangGraph patterns

### For Understanding Conversation Handling

1. [12-conversation-patterns.md](12-conversation-patterns.md) - Pattern reference
2. [07-flow-management.md](07-flow-management.md) - Flow stack mechanics
3. [05-message-flow.md](05-message-flow.md) - Decision logic and routing

### For NLU and Prompt Optimization

1. [06-nlu-system.md](06-nlu-system.md) - NLU with Command output
2. [09-dspy-optimization.md](09-dspy-optimization.md) - DSPy optimization workflow

## Design Principles

All design documents follow these core principles:

1. **Command-Driven DM** - LLM interprets, DM executes deterministically
2. **Handler Registry** - SOLID-compliant command execution (OCP)
3. **Explicit State Machine** - Clear tracking of conversation state
4. **Zero-Leakage** - YAML for semantics, Python for implementation
5. **SOLID Principles** - SRP, OCP, LSP, ISP, DIP throughout
6. **Async-First** - Everything is async, no blocking operations

## Technology Stack

| Component | Technology |
|-----------|------------|
| Language | Python 3.11+ |
| Dialogue Management | LangGraph 1.0.4+ |
| NLU | DSPy 3.0.4+ |
| LLM Providers | OpenAI, Anthropic |
| Web Framework | FastAPI 0.122.0+ |
| Validation | Pydantic 2.12.5+ |

---

**Design Version**: v2.0 (Command-Driven Architecture)
**Status**: Production-ready design specification
