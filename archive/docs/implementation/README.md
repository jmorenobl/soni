# Soni v0.8 - Implementation Plan

## Overview

This directory contains the complete implementation plan for refactoring Soni from the current broken state to the production-ready v0.8 architecture described in `docs/design/`.

## Guiding Principles

1. **Iterative Implementation**: Build incrementally, testing at each step
2. **Bottom-Up Approach**: Start with core types and interfaces, build upward
3. **Test-Driven**: Write tests alongside implementation
4. **Zero Legacy**: Clean slate - no backwards compatibility constraints
5. **SOLID Compliance**: Follow all design principles strictly

## Implementation Strategy

### Phase-Based Approach

The implementation is divided into **5 phases**, each building on the previous:

```
Phase 1: Core Foundation (Types & Interfaces)
   ↓
Phase 2: State Management & Flow Control
   ↓
Phase 3: NLU System with DSPy
   ↓
Phase 4: LangGraph Integration & Nodes
   ↓
Phase 5: Production Readiness
```

Each phase is **independently testable** and brings the system to a working state.

### Directory Structure

```
docs/implementation/
├── README.md                    # This file
├── 00-prerequisites.md          # Setup and dependencies
├── 01-phase-1-foundation.md     # Core types and interfaces
├── 02-phase-2-state.md          # State management
├── 03-phase-3-nlu.md            # NLU system
├── 04-phase-4-langgraph.md      # Graph construction
├── 05-phase-5-production.md     # Production features
└── 99-validation.md             # Testing and validation
```

## How to Use This Plan

### Step 1: Read Prerequisites

Start with `00-prerequisites.md` to ensure your environment is ready.

### Step 2: Work Phase by Phase

**Do NOT skip phases**. Each phase:
1. Lists specific tasks in order
2. Provides implementation guidance
3. Includes test requirements
4. Has clear completion criteria

### Step 3: Follow the Task Format

Each task follows this structure:

```markdown
### Task X.Y: Task Name

**File**: `src/soni/path/to/file.py`

**What**: Brief description

**Why**: Rationale and dependencies

**Implementation**:
- Step 1
- Step 2
- ...

**Tests**:
- Test requirement 1
- Test requirement 2

**Completion Criteria**:
- [ ] Criterion 1
- [ ] Criterion 2
```

### Step 4: Validate Continuously

After each task:
- Run `uv run ruff check . && uv run ruff format .`
- Run `uv run mypy src/soni`
- Run relevant tests
- Commit if all checks pass

### Step 5: Track Progress

Move tasks through states:
- `📋 Backlog`: Not started
- `🚧 In Progress`: Currently working
- `✅ Done`: Completed and tested

## Phase Overview

### Phase 1: Core Foundation (2-3 days)

**Goal**: Establish type-safe foundation with interfaces and core types.

**Deliverables**:
- All TypedDict state structures
- Protocol interfaces (INLUProvider, IActionHandler, etc.)
- Core error classes
- FlowManager class

**Key Files**:
- `src/soni/core/types.py`
- `src/soni/core/interfaces.py`
- `src/soni/core/errors.py`
- `src/soni/flow/manager.py`

### Phase 2: State Management (2-3 days)

**Goal**: Working state machine with validation and transitions.

**Deliverables**:
- DialogueState initialization
- State transition validator
- Memory management
- State serialization tests

**Key Files**:
- `src/soni/core/state.py`
- `src/soni/core/validators.py`

### Phase 3: NLU System (3-4 days)

**Goal**: Production-ready NLU with DSPy optimization.

**Deliverables**:
- Pydantic models (NLUOutput, DialogueContext, etc.)
- DSPy signatures
- SoniDU module with async support
- DummyLM tests
- Training data examples

**Key Files**:
- `src/soni/du/models.py`
- `src/soni/du/signatures.py`
- `src/soni/du/modules.py`
- `tests/unit/test_nlu.py`

### Phase 4: LangGraph Integration (3-4 days)

**Goal**: Complete dialogue management with LangGraph.

**Deliverables**:
- All node implementations
- Routing functions
- Graph builder
- RuntimeContext injection
- End-to-end flow tests

**Key Files**:
- `src/soni/dm/nodes/*.py`
- `src/soni/dm/routing.py`
- `src/soni/dm/builder.py`

### Phase 5: Production Features (2-3 days)

**Goal**: Production-ready deployment.

**Deliverables**:
- Error handling and recovery
- Logging and metrics
- Health checks
- Configuration management
- FastAPI endpoints

**Key Files**:
- `src/soni/server/api.py`
- `src/soni/observability/metrics.py`
- `src/soni/config/loader.py`

## Estimated Timeline

- **Total**: 12-17 days
- **With buffer**: 3-4 weeks

### Daily Workflow

1. **Morning**:
   - Review current task
   - Read relevant design docs
   - Plan implementation approach

2. **Implementation**:
   - Write code following task steps
   - Write tests alongside code
   - Validate with ruff + mypy

3. **End of Day**:
   - Run full test suite
   - Commit completed tasks
   - Update progress tracking

## Success Criteria

The refactoring is complete when:

1. ✅ All 5 phases completed
2. ✅ All tests passing (minimum 80% coverage)
3. ✅ Type checking passes (`mypy src/soni`)
4. ✅ Linting passes (`ruff check .`)
5. ✅ End-to-end dialogue flows work
6. ✅ FastAPI server runs and handles requests
7. ✅ Example configuration executes successfully

## Alternative Approaches

If this phase-based approach doesn't suit your workflow, consider:

### Alternative 1: Component-First

Implement one complete vertical slice at a time:
1. Simple slot collection flow (all layers)
2. Add intent changes
3. Add digressions
4. Add complex flows

**Pros**: Earlier end-to-end validation
**Cons**: More refactoring as you add features

### Alternative 2: Spike-Then-Implement

Create quick prototypes first, then productionize:
1. Spike: Working prototype with shortcuts
2. Productionize: Add tests, error handling, etc.
3. Repeat for each major feature

**Pros**: Faster initial progress
**Cons**: Risk of technical debt

### Alternative 3: Test-First

Write all tests based on design, then implement:
1. Write comprehensive test suite
2. Implement to make tests pass

**Pros**: Confidence in completeness
**Cons**: Requires deep understanding upfront

**Recommendation**: Stick with the phase-based approach for maximum clarity and safety.

## Getting Help

### When Stuck

1. **Check Design Docs**: Answer is likely in `docs/design/`
2. **Review CLAUDE.md**: Follow coding conventions
3. **Look at Reference Code**: See `ref/` for DSPy/LangGraph examples
4. **Ask Questions**: Use the Task tool to get specific guidance

### Common Pitfalls

1. **Skipping Tests**: Always write tests alongside code
2. **Premature Optimization**: Focus on correctness first
3. **Breaking SOLID**: Review interfaces before implementation
4. **Ignoring Type Hints**: Mypy is your friend
5. **Large Commits**: Commit small, working increments

## Next Steps

1. Read `00-prerequisites.md`
2. Set up your environment
3. Start with `01-phase-1-foundation.md`
4. Follow tasks in order
5. Track progress and commit frequently

---

**Design Version**: v0.8 (Production-Ready with Structured Types)
**Implementation Start Date**: 2024-12-05
**Estimated Completion**: 3-4 weeks

Let's build this right! 🚀
