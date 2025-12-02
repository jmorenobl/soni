# Soni Framework - Design Documentation

This directory contains the complete design documentation for the Soni Framework, a conversational dialogue system with automatic prompt optimization.

## Purpose

This documentation was created to:
1. Address structural issues in the original implementation
2. Design a correct, efficient, and scalable architecture
3. Provide a clear implementation roadmap
4. Serve as a reference for future development

## Document Structure

### Core Architecture

1. **[01-architecture-overview.md](01-architecture-overview.md)**
   - High-level architecture and principles
   - System components and their relationships
   - Design goals and non-goals
   - Technology stack and rationale

2. **[02-state-machine.md](02-state-machine.md)**
   - Dialogue state machine design
   - State schema and lifecycle
   - State transitions and triggers
   - Persistence and checkpointing strategy

3. **[03-message-processing.md](03-message-processing.md)**
   - Message processing pipeline
   - Context-aware routing
   - NLU integration and caching
   - Decision trees and flow control

### Flow Execution

4. **[04-graph-execution-model.md](04-graph-execution-model.md)**
   - LangGraph integration strategy
   - Node execution lifecycle
   - Resumable execution and checkpoints
   - Conditional routing and branching

5. **[05-node-types.md](05-node-types.md)**
   - Understand node design
   - Collect node design
   - Action node design
   - Branch node design
   - Custom node extensibility

6. **[06-flow-compilation.md](06-flow-compilation.md)**
   - YAML DSL to graph compilation
   - DAG intermediate representation
   - Step types and their semantics
   - Optimization opportunities

### Intelligence Layer

7. **[07-nlu-architecture.md](07-nlu-architecture.md)**
   - NLU provider interface
   - DSPy integration and optimization
   - Context and scope management
   - Caching and performance strategy

8. **[08-slot-collection.md](08-slot-collection.md)**
   - Slot filling strategies
   - Direct mapping vs NLU extraction
   - Validation and normalization
   - User corrections and overrides

9. **[09-response-generation.md](09-response-generation.md)**
   - Response generation architecture
   - Template-based vs generative responses
   - Context-aware prompts
   - Multi-turn conversation flow

### Cross-Cutting Concerns

10. **[10-error-handling.md](10-error-handling.md)**
    - Error taxonomy and handling strategies
    - Recovery mechanisms
    - User-facing error messages
    - Logging and debugging

11. **[11-security-guardrails.md](11-security-guardrails.md)**
    - Input sanitization
    - Action validation and scoping
    - Rate limiting and abuse prevention
    - Audit logging

12. **[12-performance-optimization.md](12-performance-optimization.md)**
    - Caching strategies
    - Token optimization
    - Latency reduction techniques
    - Scalability considerations

### Implementation Guide

13. **[13-migration-plan.md](13-migration-plan.md)** (To be created)
    - Migration strategy from current implementation
    - Breaking changes and compatibility
    - Phased rollout approach
    - Testing and validation strategy

14. **[14-implementation-roadmap.md](14-implementation-roadmap.md)**
    - Implementation phases (5 phases, 10-12 weeks)
    - Task breakdown and dependencies
    - Success metrics and performance targets
    - Timeline estimates and risk mitigation

### Current Problems Analysis

15. **[15-current-problems-analysis.md](15-current-problems-analysis.md)**
    - Confirmed problems from execution tracing
    - Root cause analysis for each issue
    - Performance impact measurements
    - Quick wins vs redesign targets

16. **[16-start-prefix-investigation.md](16-start-prefix-investigation.md)**
    - Investigation of "start_" prefix in action names
    - Why it exists and why it's problematic
    - Recommendation to remove it
    - Implementation plan

17. **[17-state-validation-approach.md](17-state-validation-approach.md)**
    - Analysis: `transitions` library vs custom implementation
    - Why NOT to use `transitions` with LangGraph
    - Lightweight validation approach (recommended)
    - Implementation plan for state transition validation

## How to Use This Documentation

### For Understanding the System
Read documents 1-3 to understand the high-level architecture and state management.

### For Implementation
Follow the implementation roadmap (document 14) and refer to specific design documents as needed.

### For Extending the System
Read document 5 (Node Types) for adding new node types, or document 7 (NLU) for integrating new NLU providers.

### For Optimization
Refer to document 12 for performance optimization strategies.

## Design Principles

All design documents follow these core principles:

1. **Clarity over Cleverness**: Explicit, understandable code over clever abstractions
2. **Correctness First**: Get the architecture right, then optimize
3. **SOLID Principles**: Interface-based design, dependency injection, single responsibility
4. **Async-First**: Everything is async, no sync-to-async wrappers
5. **Zero-Leakage**: YAML describes WHAT, Python implements HOW
6. **Test-Driven**: Every component is designed to be testable

## Notation and Conventions

### State Machine Diagrams
```
[State] → (Trigger) → [New State]
```

### Sequence Diagrams
```
User → System: message
System → NLU: predict()
NLU → System: result
System → User: response
```

### Code Examples
All code examples are in Python 3.11+ with full type hints.

### Decision Records
Key architectural decisions are documented inline with rationale and alternatives considered.

## Contributing to Design Docs

When adding or modifying design documents:
1. Follow the existing structure and format
2. Include concrete examples
3. Document alternatives considered
4. Explain rationale for decisions
5. Update this README with new documents

## Version History

- **v1.0** (2025-12-02): Initial design documentation created based on analysis of structural issues in original implementation

## References

- [CLAUDE.md](../../CLAUDE.md) - Project instructions and conventions
- [ADR-001](../adr/001-architecture-v1.3.md) - Original architecture decision record
- [LangGraph Documentation](https://langchain-ai.github.io/langgraph/)
- [DSPy Documentation](https://dspy-docs.vercel.app/)
