# Soni Framework - Design Documentation v0.5

This directory contains the complete design documentation for Soni v0.5, a conversational dialogue system with automatic prompt optimization.

## Quick Start

New to Soni? Start here:

1. **[01-overview.md](01-overview.md)** - What is Soni and what problems it solves
2. **[02-architecture.md](02-architecture.md)** - Core architectural principles and design
3. **[03-components.md](03-components.md)** - System components and their responsibilities

For detailed technical design:

4. **[04-state-machine.md](04-state-machine.md)** - Dialogue state and conversation flow
5. **[05-message-flow.md](05-message-flow.md)** - Message processing pipeline
6. **[06-nlu-system.md](06-nlu-system.md)** - NLU with context enrichment
7. **[07-flow-management.md](07-flow-management.md)** - Flow stack and complex conversations
8. **[08-langgraph-integration.md](08-langgraph-integration.md)** - LangGraph patterns and usage
9. **[09-dspy-optimization.md](09-dspy-optimization.md)** - Prompt optimization with DSPy
10. **[10-dsl-specification/](10-dsl-specification/)** - DSL Specification (multi-document)

## Document Overview

| Document | Purpose | Key Topics |
|----------|---------|------------|
| [01-overview.md](01-overview.md) | System introduction | Features, goals, use cases |
| [02-architecture.md](02-architecture.md) | Architectural design | Principles, stack, component overview |
| [03-components.md](03-components.md) | Component details | RuntimeLoop, NLU, handlers, registries |
| [04-state-machine.md](04-state-machine.md) | State management | DialogueState schema, transitions |
| [05-message-flow.md](05-message-flow.md) | Message processing | Routing, NLU-first pattern, decision logic |
| [06-nlu-system.md](06-nlu-system.md) | Natural language understanding | Context enrichment, DSPy module |
| [07-flow-management.md](07-flow-management.md) | Complex conversations | Flow stack, interruptions, slot scoping |
| [08-langgraph-integration.md](08-langgraph-integration.md) | Graph execution | Checkpointing, interrupt/resume patterns |
| [09-dspy-optimization.md](09-dspy-optimization.md) | Prompt optimization | Signatures, metrics, training |
| [10-dsl-specification/](10-dsl-specification/) | DSL specification | YAML schema, step types, patterns, examples |

## Key Concepts

### Unified NLU Approach

Every user message flows through a single NLU provider with enriched context. The NLU handles:
- Slot value extraction
- Intent detection and changes
- Digression detection (questions, clarifications)
- Resume request identification

### Flow Stack

Complex conversation support through a flow stack:
- Push new flows (pauses current flow)
- Pop completed flows (resumes previous flow)
- Maintain state across interruptions

### LangGraph Integration

Native LangGraph patterns:
- `interrupt()` - Pause execution waiting for user input
- `Command(resume=)` - Continue execution after interrupt
- Automatic checkpointing via `thread_id`

### Zero-Leakage Architecture

YAML describes **WHAT** (semantics), Python implements **HOW** (logic):
- Business analysts can configure flows without coding
- Technical implementation stays in Python code
- Clear separation of concerns

## Reading Paths

### For Developers Implementing Soni

1. [02-architecture.md](02-architecture.md) - Understand the overall design
2. [03-components.md](03-components.md) - Learn component responsibilities
3. [08-langgraph-integration.md](08-langgraph-integration.md) - Master LangGraph patterns
4. [04-state-machine.md](04-state-machine.md) - Understand state management
5. [05-message-flow.md](05-message-flow.md) - Implement message processing

### For Understanding Complex Conversations

1. [07-flow-management.md](07-flow-management.md) - Flow stack mechanics
2. [05-message-flow.md](05-message-flow.md) - Decision logic and routing
3. [06-nlu-system.md](06-nlu-system.md) - Context-aware understanding

### For NLU and Prompt Optimization

1. [06-nlu-system.md](06-nlu-system.md) - NLU system design
2. [09-dspy-optimization.md](09-dspy-optimization.md) - DSPy optimization workflow

## Design Principles

All design documents follow these core principles:

1. **Explicit State Machine** - Clear tracking of conversation state and position
2. **Context-Aware Execution** - Rich context enables accurate understanding
3. **Resumable Execution** - Leverage LangGraph checkpointing for automatic resumption
4. **Zero-Leakage** - YAML for semantics, Python for implementation
5. **SOLID Principles** - Interface-based design with dependency injection
6. **Async-First** - Everything is async, no blocking operations

## Quick Reference

Common questions and answers:

| Question | Answer | Document |
|----------|--------|----------|
| How are messages processed? | Unified NLU with enriched context | [05-message-flow.md](05-message-flow.md) |
| How to handle flow interruptions? | Push new flow to stack, pause current | [07-flow-management.md](07-flow-management.md) |
| How to pause/resume execution? | Use `interrupt()` and `Command(resume=)` | [08-langgraph-integration.md](08-langgraph-integration.md) |
| How are slots scoped? | Flow-scoped slots prevent naming conflicts | [07-flow-management.md](07-flow-management.md) |
| How to transfer data between flows? | FlowContext.outputs for cross-flow data | [07-flow-management.md](07-flow-management.md) |
| How to optimize prompts? | DSPy with business metrics | [09-dspy-optimization.md](09-dspy-optimization.md) |

## Conventions

### Code Examples

All code examples in this documentation:
- Use Python 3.11+ with full type hints
- Follow async/await patterns throughout
- Include clear, descriptive variable names
- Are production-ready patterns, not pseudocode

### Diagrams

Diagrams are integrated into documents where conceptually appropriate:
- **Mermaid format** for flowcharts, sequence diagrams, and state machines
- **ASCII diagrams** for simple architectural layouts
- Diagrams illustrate concepts explained in surrounding text

### Cross-References

Documents reference each other for related concepts:
- Internal links use relative paths: `[document.md](document.md)`
- External links to LangGraph/DSPy docs included where relevant

## Technology Stack

| Component | Technology | Version | Purpose |
|-----------|-----------|---------|---------|
| Language | Python | 3.11+ | Modern async, type hints |
| Dialogue Management | LangGraph | 1.0.4+ | State graphs, checkpointing |
| NLU | DSPy | 3.0.4+ | Automatic prompt optimization |
| Web Framework | FastAPI | 0.122.0+ | Async API, WebSocket |
| Persistence | SQLite/Postgres/Redis | Latest | Flexible checkpointing |
| Validation | Pydantic | 2.12.5+ | Data validation |

## Related Documentation

- **[AGENTS.md](../../AGENTS.md)** - Development rules and conventions
- **[docs/adr/](../adr/)** - Architectural decision records
- **[examples/](../../examples/)** - Working examples and demos
- **[LangGraph Documentation](https://langchain-ai.github.io/langgraph/)** - LangGraph reference
- **[DSPy Documentation](https://dspy-docs.vercel.app/)** - DSPy reference

## Version Information

**Design Version**: v0.5
**Status**: Production-ready design specification
**Last Updated**: 2025-12-02

This documentation represents the complete, finalized design for Soni v0.5. All design decisions have been made and consolidated. The documents are ready for implementation reference.

## Contributing

When modifying design documents:

1. Ensure consistency across all affected documents
2. Update cross-references if document structure changes
3. Maintain diagram accuracy with text descriptions
4. Follow the established conventions and writing style
5. All documentation must be in English

---

**Ready to start?** Begin with [01-overview.md](01-overview.md) to understand what Soni is and what problems it solves.
