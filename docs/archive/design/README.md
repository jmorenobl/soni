# Soni Framework - Design Documentation

This directory contains the **final design documentation** for the Soni Framework, a conversational dialogue system with automatic prompt optimization.

## 🎯 Start Here

**New to this documentation?** Read in this order:

1. **[01-architecture-overview.md](01-architecture-overview.md)** - 📐 **CURRENT ARCHITECTURE**
   - Complete system design with all components
   - Design goals and principles
   - Technology stack
   - This is the definitive architectural reference

2. **[02-state-machine.md](02-state-machine.md)** - State management
   - Dialogue state schema
   - State transitions and lifecycle
   - Persistence strategy

3. **[03-message-processing.md](03-message-processing.md)** - Message handling
   - Context-aware routing
   - NLU integration
   - Decision trees

4. **[04-graph-execution-model.md](04-graph-execution-model.md)** - LangGraph integration
   - Graph execution and resumption
   - Node lifecycle
   - Conditional routing

5. **[05-complex-conversations.md](05-complex-conversations.md)** - Complex conversation patterns
   - Flow stack management
   - Digression handling
   - Multi-turn interactions

6. **[06-flow-diagrams.md](06-flow-diagrams.md)** - Visual diagrams
   - Mermaid diagrams for all flows
   - Component interactions
   - State transitions

**For Design Decisions & Evolution**:
- [20-consolidated-design-decisions.md](20-consolidated-design-decisions.md) - Design evolution and rationale

**For Future Work**:
- [21-architecture-improvements.md](21-architecture-improvements.md) - Implementation backlog (NOT current architecture)

## 📚 Core Documents

### Architecture (Final Design)

| Document | Description | Status |
|----------|-------------|--------|
| [01-architecture-overview.md](01-architecture-overview.md) | **📐 CURRENT ARCHITECTURE** - Complete system design | ✅ Final |
| [02-state-machine.md](02-state-machine.md) | Dialogue state machine design | ✅ Final |
| [03-message-processing.md](03-message-processing.md) | Message processing pipeline | ✅ Final |
| [04-graph-execution-model.md](04-graph-execution-model.md) | LangGraph execution model | ✅ Final |
| [05-complex-conversations.md](05-complex-conversations.md) | Flow stack, digressions, and complex conversation patterns | ✅ Final |
| [06-flow-diagrams.md](06-flow-diagrams.md) | Visual diagrams (Mermaid) for complex conversation flows | ✅ Final |
| [20-consolidated-design-decisions.md](20-consolidated-design-decisions.md) | **Single source of truth** - All final decisions and evolution | 📋 Reference |
| [21-architecture-improvements.md](21-architecture-improvements.md) | **📋 IMPLEMENTATION BACKLOG** - Gaps to implement in future | ⏳ Pending |

### Implementation

| Document | Description | Status |
|----------|-------------|--------|
| [14-implementation-roadmap.md](14-implementation-roadmap.md) | Phased implementation plan (10-12 weeks) | ✅ Final |
| [19-realistic-slot-collection-strategy.md](19-realistic-slot-collection-strategy.md) | Slot collection design (two-level approach) | ⚠️ Superseded - See unified NLU approach |

## 🔑 Key Design Decisions

Quick answers to common questions:

| Question | Answer | Reference |
|----------|--------|-----------|
| How to process messages? | Unified NLU with enriched context | Doc 01, 03, 20 |
| Use transitions library? | No, use custom validation | Doc 02, 20 |
| Remove "start_" prefix? | Yes, remove it | Doc 20 |
| When to call NLU? | Always (except during action execution) | Doc 03, 20 |
| Resume graph from current step? | Yes, resumable execution | Doc 04, 20 |
| How to track conversation state? | Explicit fields: conversation_state, current_step, waiting_for_slot | Doc 02, 20 |
| How to handle flow interruptions? | Push new flow to stack, pause current | Doc 05, 20 |
| How to pause/resume execution? | Use `interrupt()` to pause, `Command(resume=)` to continue | Doc 01 |
| Manual entry point selection? | NO - LangGraph handles automatically via checkpointing | Doc 01 |
| FlowStackManager as separate class? | No, helper methods in RuntimeLoop | Doc 05, 21 |
| DigressionHandler architecture? | Coordinator with KnowledgeBase + HelpGenerator | Doc 05, 21 |
| How to handle slot naming conflicts? | Flow-scoped slots (`state.flow_slots[flow_name]`) | Doc 21 |
| Cross-flow data transfer? | Flow outputs (`FlowContext.outputs`) | Doc 21 |

## 📖 Reading Paths

### For Implementation
1. Start with: [14-implementation-roadmap.md](14-implementation-roadmap.md)
2. Reference: [20-consolidated-design-decisions.md](20-consolidated-design-decisions.md)
3. Details: Documents 01-04 as needed

### For Understanding Architecture
1. **[01-architecture-overview.md](01-architecture-overview.md)** - 📐 **START HERE** - Complete current architecture
2. [02-state-machine.md](02-state-machine.md) - State management
3. [03-message-processing.md](03-message-processing.md) - Message flow
4. [04-graph-execution-model.md](04-graph-execution-model.md) - Execution
5. [05-complex-conversations.md](05-complex-conversations.md) - Complex patterns
6. [06-flow-diagrams.md](06-flow-diagrams.md) - Visual diagrams (Mermaid)
7. [20-consolidated-design-decisions.md](20-consolidated-design-decisions.md) - Design evolution and rationale

### For Message Processing Details
1. [20-consolidated-design-decisions.md](20-consolidated-design-decisions.md) - Decision summary
2. [03-message-processing.md](03-message-processing.md) - Unified NLU approach
3. [05-complex-conversations.md](05-complex-conversations.md) - Complex patterns (flow stack, digressions)

## 🗂️ Historical Documents

The `archive/` directory contains:
- Problem analysis and investigations
- Design evolution and superseded approaches
- Consolidation process documentation

These documents show the evolution of thinking but are not part of the final design. They are kept for historical reference and context.

See [archive/README.md](archive/README.md) for details.

## 🎯 Design Principles

All design documents follow these core principles:

1. **Correctness First**: Get the architecture right, then optimize
2. **Realistic Communication**: Design for how humans actually talk, not ideal cases
3. **No God Objects**: RuntimeLoop orchestrates, delegates complex logic to focused components
4. **Proper Decomposition**: Each component has a single, clear responsibility
5. **Simple Operations**: Don't extract classes for simple list/dict operations
6. **LangGraph-First**: Work with LangGraph's architecture, not against it
7. **SOLID Principles**: Interface-based design, dependency injection, single responsibility
8. **Async-First**: Everything is async, no sync-to-async wrappers
9. **Zero-Leakage**: YAML describes WHAT, Python implements HOW

## 📝 Document Conventions

### Status Indicators
- ✅ **Final** - Current design, ready for implementation
- 🔄 **Updated** - Recently updated with final decisions
- 📋 **Reference** - Analysis or decision document

### Code Examples
All code examples use:
- Python 3.11+ with full type hints
- Async/await patterns throughout
- Clear, descriptive variable names

### Diagrams
- State machines: `[State] → (Trigger) → [New State]`
- Sequence diagrams show component interactions
- Architecture diagrams show system structure

## 🔗 Related Documentation

- [AGENTS.md](../../AGENTS.md) - Development rules and conventions
- [ADR-001](../adr/001-architecture-v1.3.md) - Original architecture decision record
- [LangGraph Documentation](https://langchain-ai.github.io/langgraph/)
- [DSPy Documentation](https://dspy-docs.vercel.app/)

## 📊 Version History

- **v2.3** (2025-12-02): **LANGGRAPH ALIGNMENT** - Correct LangGraph patterns
  - All documents aligned with 01-architecture-overview.md as ground truth
  - Fixed incorrect patterns (`ainvoke_from_node`, manual entry point selection)
  - Added correct patterns (`interrupt()`, `Command(resume=)`, automatic checkpointing)
  - All documents now reference ground truth

- **v2.2** (2025-12-02): **CONSOLIDATED ARCHITECTURE** - Single source of truth
  - Doc 01 now contains complete current architecture
  - Doc 21 clarified as implementation backlog (future work)
  - Clear distinction: current architecture vs. future improvements
  - No confusion about what's implemented vs. what's planned

- **v2.1** (2025-12-02): **ARCHITECTURE REFINEMENT** - Critical analysis and improvements
  - Added doc 21: Architecture improvements with gap analysis
  - Refined component architecture (DigressionHandler decomposition)
  - Simplified flow stack operations (helper methods vs. separate class)
  - Updated docs 05, 06 with refined architecture

- **v2.0** (2025-12-02): **CLEAN STRUCTURE** - Moved historical documents to archive/
  - Final design documents only in main directory
  - Clear, unambiguous documentation structure
  - Historical evolution preserved in archive/

- **v1.1** (2025-12-02): Consolidation - Created single source of truth (doc 20)
- **v1.0** (2025-12-02): Initial design documentation

## 🤝 Contributing

When modifying design documents:
1. Update the affected document with clear rationale
2. Update document 20 if decisions change
3. Update this README if structure changes
4. All documents must remain consistent

---

**Last Updated**: 2025-12-02
**Maintained by**: Design team
**Status**: Final design documentation
