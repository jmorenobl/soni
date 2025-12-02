# Soni Framework - Design Documentation

This directory contains the complete design documentation for the Soni Framework, a conversational dialogue system with automatic prompt optimization.

## 🎯 Quick Start: Final Decisions

**New to this documentation?** Start here:

👉 **[20-consolidated-design-decisions.md](20-consolidated-design-decisions.md)** - Single source of truth for all final design decisions

This document:
- Resolves contradictions and evolution across all design docs
- Provides quick decision lookup table
- Explains what ideas were superseded and why
- Shows the final, coherent architecture

## Purpose

This documentation was created to:
1. Address structural issues in the original implementation
2. Design a correct, efficient, and scalable architecture
3. Provide a clear implementation roadmap
4. Serve as a reference for future development

## Document Evolution

These documents represent the **evolution of design thinking** over time. Some ideas were revised as we discovered edge cases or better approaches:

- **Initial designs** (docs 00-04): Core architecture and initial approaches
- **Analysis** (docs 15-17): Investigation of specific issues
- **Evolution** (docs 18-19): Refinement of slot collection strategy
- **Final** (doc 20): Consolidated decisions

⚠️ **Important**: Always check the **Status** field in each document:
- ✅ **Final/Stable**: Current design
- ⚠️ **SUPERSEDED**: Historical, replaced by newer document
- 📋 **Reference**: Analysis or decision document

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
    - **Decision: REMOVE the prefix**
    - Implementation plan

17. **[17-state-validation-approach.md](17-state-validation-approach.md)**
    - Analysis: `transitions` library vs custom implementation
    - **Decision: Do NOT use `transitions` with LangGraph**
    - Lightweight validation approach (recommended)
    - Implementation plan for state transition validation

18. **[18-hybrid-slot-collection-strategy.md](18-hybrid-slot-collection-strategy.md)** ⚠️ **SUPERSEDED**
    - 3-tier approach with pattern extraction
    - **Status: SUPERSEDED by document 19**
    - **Reason**: Pattern extraction too simplistic for realistic user behavior
    - **Historical value**: Shows evolution of thinking

19. **[19-realistic-slot-collection-strategy.md](19-realistic-slot-collection-strategy.md)** ✅ **FINAL**
    - **Two-level DSPy-based slot collection**
    - Lightweight DSPy collector + full NLU fallback
    - Handles realistic human communication (questions, intent changes, corrections)
    - **This is the final design for slot collection**

20. **[20-consolidated-design-decisions.md](20-consolidated-design-decisions.md)** 📋 **REFERENCE**
    - **Single source of truth for all final design decisions**
    - Resolves contradictions across documents 00-19
    - Quick decision lookup table
    - Implementation roadmap (revised)

## How to Use This Documentation

### 🆕 For New Readers
1. **Start with**: [20-consolidated-design-decisions.md](20-consolidated-design-decisions.md) - Final decisions
2. **Then read**: [01-architecture-overview.md](01-architecture-overview.md) - High-level design
3. **Deep dive**: [02-state-machine.md](02-state-machine.md), [03-message-processing.md](03-message-processing.md), [04-graph-execution-model.md](04-graph-execution-model.md)

### 👨‍💻 For Implementation
1. Follow [14-implementation-roadmap.md](14-implementation-roadmap.md)
2. Reference [20-consolidated-design-decisions.md](20-consolidated-design-decisions.md) for specific decisions
3. Refer to detailed design docs (01-04) as needed

### 🔍 For Understanding Evolution
- Read [15-current-problems-analysis.md](15-current-problems-analysis.md) - What problems were found
- See [18-hybrid-slot-collection-strategy.md](18-hybrid-slot-collection-strategy.md) (superseded) vs [19-realistic-slot-collection-strategy.md](19-realistic-slot-collection-strategy.md) (final) to understand refinement process
- Check [20-consolidated-design-decisions.md](20-consolidated-design-decisions.md) "Superseded Ideas" section

### 🛠️ For Extending the System
- Read document 5 (Node Types) for adding new node types
- Read document 7 (NLU) for integrating new NLU providers
- Read document 12 for performance optimization strategies

### ❓ For Quick Answers
See the "Quick Decision Lookup" table in [20-consolidated-design-decisions.md](20-consolidated-design-decisions.md)

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

## Document Status Legend

| Symbol | Meaning |
|--------|---------|
| ✅ | Stable/Final - Current design, ready for implementation |
| ⚠️ | SUPERSEDED - Historical only, don't implement |
| 📋 | Reference - Analysis or decision document |
| 🔄 | Updated - Recently updated with final decisions |

## Version History

- **v1.1** (2025-12-02): **CONSOLIDATION** - Resolved contradictions, created single source of truth (doc 20)
  - Added consolidated design decisions document (20)
  - Updated main architecture docs with final decisions
  - Marked superseded documents (18)
  - Created consolidation summary
- **v1.0** (2025-12-02): Initial design documentation created based on analysis of structural issues in original implementation

## References

- [CLAUDE.md](../../CLAUDE.md) - Project instructions and conventions
- [ADR-001](../adr/001-architecture-v1.3.md) - Original architecture decision record
- [LangGraph Documentation](https://langchain-ai.github.io/langgraph/)
- [DSPy Documentation](https://dspy-docs.vercel.app/)
