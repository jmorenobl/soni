# DialogueState Migration Analysis

## Executive Summary

The DialogueState migration from dataclass to TypedDict has uncovered a **fundamental schema incompatibility** between two parallel state management systems in the codebase:

1. **Legacy Schema** (dataclass-based): Used in `runtime/runtime.py`, `core/scope.py`, and most node factories
2. **New Schema** (TypedDict-based): Used in newer nodes (`dm/nodes/*.py`) and designed for LangGraph

These are **not interchangeable** - they have different field names and structures.

## Schema Comparison

### Legacy Schema (Dataclass)
```python
@dataclass
class DialogueState:
    messages: list[dict[str, str]]
    current_flow: str = "none"
    slots: dict[str, Any]
    pending_action: str | None
    last_response: str
    turn_count: int
    trace: list[dict[str, Any]]
    summary: str | None
```

### New Schema (TypedDict)
```python
class DialogueState(TypedDict):
    user_message: str
    last_response: str
    messages: list[dict[str, Any]]
    flow_stack: list[FlowContext]      # ← Different!
    flow_slots: dict[str, dict[str, Any]]  # ← Different!
    conversation_state: str
    current_step: str | None
    waiting_for_slot: str | None
    nlu_result: dict[str, Any] | None
    last_nlu_call: float | None
    digression_depth: int
    last_digression_type: str | None
    turn_count: int
    trace: list[dict[str, Any]]
    metadata: dict[str, Any]
```

## Key Differences

1. **Flow Management**:
   - Legacy: `current_flow: str` (single string)
   - New: `flow_stack: list[FlowContext]` (stack of flow contexts)

2. **Slot Storage**:
   - Legacy: `slots: dict[str, Any]` (flat dict)
   - New: `flow_slots: dict[str, dict[str, Any]]` (nested by flow_id)

3. **User Input**:
   - Legacy: Stored in `messages` list
   - New: Separate `user_message` field + `messages` history

4. **State Machine**:
   - Legacy: Implicit state machine
   - New: Explicit `conversation_state`, `current_step`, `waiting_for_slot`

## Impact Assessment

### Files Using Legacy Schema (Need Migration)
1. `src/soni/runtime/runtime.py` - Creates/manipulates DialogueState (lines 338-350, 398, 405, 416)
2. `src/soni/core/scope.py` - Accesses `state.current_flow` and `state.slots` (PARTIALLY FIXED)
3. `src/soni/dm/routing.py` - Uses `state.trace` directly (PARTIALLY FIXED)
4. `src/soni/runtime/conversation_manager.py` - Calls `.from_dict()` and `.to_dict()` (FIXED)
5. `src/soni/runtime/streaming_manager.py` - Calls `.to_dict()` (FIXED)

### Files Using New Schema (Already Compatible)
- `src/soni/dm/nodes/understand.py`
- `src/soni/dm/nodes/generate_response.py`
- `src/soni/dm/nodes/handle_digression.py`
- `src/soni/dm/nodes/collect_next_slot.py`
- `src/soni/dm/nodes/execute_action.py`
- `src/soni/dm/nodes/validate_slot.py`

### Files Partially Migrated
- `src/soni/dm/nodes/factories.py` - Mixed (helper functions created but some methods still use legacy patterns)

## Migration Strategies

### Option 1: Complete Migration (Recommended but Complex)
**Time Estimate**: 3-5 days

**Steps**:
1. Create bridge layer that converts between schemas
2. Update `RuntimeLoop` to use new schema exclusively
3. Update all node factories to use new schema
4. Migrate tests to new schema
5. Remove dataclass completely

**Pros**:
- Clean final state
- Full LangGraph compatibility
- Future-proof

**Cons**:
- High risk of breaking changes
- Extensive test updates required
- Complex slot management migration

### Option 2: Adapter Pattern (Pragmatic)
**Time Estimate**: 1-2 days

**Steps**:
1. Keep both schemas temporarily
2. Create bidirectional adapter functions
3. Convert at boundaries (runtime → graph, graph → runtime)
4. Migrate incrementally over time

**Pros**:
- Lower risk
- Incremental migration possible
- Tests mostly unchanged

**Cons**:
- Technical debt
- Performance overhead (conversions)
- More complex codebase

### Option 3: Schema Unification (Ideal but Time-Consuming)
**Time Estimate**: 5-7 days

**Steps**:
1. Design unified schema that supports both use cases
2. Update all components to use unified schema
3. Comprehensive test suite update
4. Documentation update

**Pros**:
- Best long-term solution
- No conversions needed
- Clear architecture

**Cons**:
- Requires design decisions (flow_stack vs current_flow?)
- Most time-consuming
- Highest risk

## Recommendation

Given the current state and project constraints, I recommend **Option 2: Adapter Pattern** as the immediate path forward, with a plan to migrate to Option 1 over the next 2-3 releases.

### Immediate Actions (Option 2)

1. **Create adapter module** (`src/soni/core/state_adapters.py`):
   ```python
   def legacy_to_new(legacy_state: DialogueStateDataclass) -> DialogueStateTypedDict:
       """Convert legacy schema to new schema."""
       # Implementation

   def new_to_legacy(new_state: DialogueStateTypedDict) -> DialogueStateDataclass:
       """Convert new schema to legacy schema."""
       # Implementation
   ```

2. **Update boundaries**:
   - `RuntimeLoop.process_message()`: Convert legacy → new before graph execution
   - Graph output: Convert new → legacy after graph execution
   - Keep legacy schema in `RuntimeLoop` for now

3. **Mark for deprecation**:
   - Add deprecation warnings to dataclass usage
   - Document migration path in CHANGELOG
   - Set target removal version (e.g., v0.6.0)

## Conclusion

The DialogueState migration reveals a deeper architectural decision point: the codebase is transitioning from a simple state machine to a more sophisticated LangGraph-based system. This requires careful planning and cannot be completed in a single PR without significant risk.

The adapter pattern provides a pragmatic path forward while allowing time for proper migration planning and execution.

## Next Steps

1. Pause current migration work
2. Implement adapter pattern (Option 2)
3. Create comprehensive test suite for adapters
4. Plan full migration roadmap for v0.5.x → v0.6.0
5. Document schema differences and migration guide for users
