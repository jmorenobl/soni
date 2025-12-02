# Investigation: "start_" Prefix in Action Names

**Document Version**: 1.0
**Last Updated**: 2025-12-02
**Status**: Complete

## Summary

The `"start_"` prefix added to flow names (e.g., `"start_book_flight"`) is **intentional design** from the original architecture, intended to distinguish **flow-starting actions** from **in-flow actions**. However, this creates a mismatch that prevents `current_flow` from being activated correctly.

**Conclusion**: The prefix serves no real purpose and causes more problems than it solves. **Recommendation: Remove it.**

---

## Where the Prefix Comes From

### Location: `src/soni/core/scope.py:180`

```python
def get_available_actions(self, state: DialogueState) -> list[str]:
    """Get available actions based on current state"""
    actions = ["help", "cancel", "restart"]  # Global actions

    if state.current_flow and state.current_flow != "none":
        # In a flow: flow-specific actions
        flow_config = self.flows.get(state.current_flow)
        if flow_config:
            flow_actions = self._get_flow_actions(flow_config)
            actions.extend(flow_actions)

            # Add slots that still need to be collected
            pending_slots = self._get_pending_slots(flow_config, state)
            for slot_name in pending_slots:
                actions.append(f"provide_{slot_name}")
    else:
        # No active flow - allow starting any flow
        for flow_name in self.flows.keys():
            actions.append(f"start_{flow_name}")  # ← HERE

    return list(set(actions))
```

**Purpose (According to Code Comments)**:
- When `current_flow == "none"`: Add `"start_{flow_name}"` for each available flow
- When `current_flow != "none"`: Add actual flow actions (no prefix)

---

## Original Design Intent

From `docs/adr/ADR-001-Soni-Framework-Architecture.md:611`:

```python
# Si no hay flujo, permitir triggers de inicio de flujos
for flow_name, flow_cfg in self.flows.items():
    actions.append(f"start_{flow_name}")
```

**Design Rationale** (Inferred):

1. **Semantic clarity**: `"start_book_flight"` makes it clear this is a flow trigger, not an action within a flow
2. **Namespace separation**: Prevents collision between flow names and action names
3. **NLU prompting**: Helps LLM understand "start a new task" vs "continue current task"

---

## The Problem This Creates

### Mismatch Between NLU Output and Flow Names

1. **ScopeManager** provides: `available_actions = ["start_book_flight", "help", "cancel"]`
2. **NLU** receives these actions and returns: `command = "start_book_flight"`
3. **Flow Activation** checks: `"start_book_flight" in config.flows` → **FALSE**
4. **Result**: Flow never activates, `current_flow` stays `"none"`

### Code Path

```
ScopeManager.get_available_actions(state)
  ↓
Returns: ["start_book_flight", "help", "cancel"]
  ↓
NLU.predict(available_actions=["start_book_flight", ...])
  ↓
NLU returns: command="start_book_flight"
  ↓
routing.activate_flow_by_intent(command="start_book_flight", ...)
  ↓
Checks: "start_book_flight" in config.flows
  ↓
config.flows = {"book_flight": {...}}  ← No "start_" prefix!
  ↓
Returns: current_flow (unchanged, stays "none")
```

---

## Why the Prefix is Problematic

### Problem 1: Creates Unnecessary Complexity

**Without prefix**:
```python
available_actions = ["book_flight", "help", "cancel"]
command = "book_flight"
if command in config.flows:  # ✅ Simple, works
    activate_flow(command)
```

**With prefix**:
```python
available_actions = ["start_book_flight", "help", "cancel"]
command = "start_book_flight"
if command in config.flows:  # ❌ Doesn't work
    activate_flow(command)
# Need to strip prefix:
flow_name = command.replace("start_", "")
if flow_name in config.flows:  # ✅ Works but extra step
    activate_flow(flow_name)
```

### Problem 2: Inconsistent Naming Convention

- When IDLE: `"start_book_flight"` (with prefix)
- When in flow: `"search_flights"` (no prefix)
- User actions: `"provide_origin"` (different prefix!)

**Result**: Confusing and inconsistent.

### Problem 3: No Real Benefit

**Claimed benefit**: "Semantic clarity"
- **Reality**: NLU already knows context (`current_flow == "none"`)
- **Reality**: LLM can distinguish "start booking" vs "search flights" without prefix

**Claimed benefit**: "Namespace separation"
- **Reality**: Flow names and action names already separated by configuration structure
- **Reality**: No risk of collision (flows in `config.flows`, actions in `config.actions`)

### Problem 4: Breaks Flow Activation (Current Bug)

As documented in Problem #2 of `15-current-problems-analysis.md`:
- `current_flow` never activates
- Flow tracking broken
- Scope manager can't provide flow-specific actions

---

## Analysis: Is the Prefix Necessary?

### Scenario 1: User says "I want to book a flight" (No active flow)

**With prefix**:
```python
available_actions = ["start_book_flight", "start_modify_booking", "help"]
NLU returns: command="start_book_flight"
# Need to strip prefix to get flow name
```

**Without prefix**:
```python
available_actions = ["book_flight", "modify_booking", "help"]
NLU returns: command="book_flight"
# Directly use as flow name
```

**Difference**: None functionally, just cleaner without prefix.

### Scenario 2: NLU distinguishes flow trigger from in-flow action

**With prefix**:
```python
# When IDLE
available_actions = ["start_book_flight", "help"]
# When in flow
available_actions = ["search_flights", "confirm_booking", "help"]
```

**Without prefix**:
```python
# When IDLE
available_actions = ["book_flight", "help"]
# When in flow
available_actions = ["search_flights", "confirm_booking", "help"]
```

**Difference**: None. NLU already knows `current_flow` context, doesn't need prefix to distinguish.

### Scenario 3: Name collision between flow and action

**Hypothetical collision**:
```yaml
flows:
  book_flight: ...

actions:
  book_flight: ...  # ❌ Same name
```

**With prefix**: Collision avoided (`start_book_flight` vs `book_flight`)
**Without prefix**: Collision exists

**Analysis**: This is a **non-issue** because:
1. Flows and actions are in separate config sections
2. Flow names describe tasks ("book_flight", "cancel_booking")
3. Action names describe operations ("search_flights", "confirm_booking")
4. Natural naming convention avoids collisions

---

## Real-World Examples from Other Frameworks

### Rasa (Similar dialogue framework)

```python
# Rasa intents (no prefix)
intents:
  - book_flight
  - cancel_booking
  - greet
  - goodbye
```

No `start_` prefix. Intent name IS the flow trigger.

### DialogFlow (Google)

```json
{
  "intent": "book_flight",
  "action": "book_flight",
  "parameters": {...}
}
```

No prefix. Intent directly maps to action/flow.

### Amazon Lex

```json
{
  "intentName": "BookFlight",
  "slots": {...}
}
```

No prefix. Intent name is the trigger.

**Conclusion**: Industry standard is **no prefix**.

---

## Recommended Solution

### Option 1: Remove Prefix Entirely (RECOMMENDED)

**Change**: `src/soni/core/scope.py:180`

```python
# OLD:
for flow_name in self.flows.keys():
    actions.append(f"start_{flow_name}")

# NEW:
for flow_name in self.flows.keys():
    actions.append(flow_name)
```

**Benefits**:
- ✅ Simpler code
- ✅ Consistent naming
- ✅ Direct flow activation (no prefix stripping)
- ✅ Matches industry standards
- ✅ Fixes current_flow activation bug

**Risks**:
- Potential collision if flow and action have same name
- **Mitigation**: Document naming convention (flows = tasks, actions = operations)

### Option 2: Keep Prefix but Fix Flow Activation

**Change**: `src/soni/dm/routing.py:157`

```python
def activate_flow_by_intent(command: str | None, current_flow: str, config: Any) -> str:
    if not command:
        return current_flow

    # Strip "start_" prefix if present
    flow_name = command.replace("start_", "", 1) if command.startswith("start_") else command

    if hasattr(config, "flows") and flow_name in config.flows:
        logger.info(f"Activating flow '{flow_name}' based on intent")
        return flow_name

    return current_flow
```

**Benefits**:
- ✅ Fixes current_flow activation bug
- ✅ Maintains backward compatibility

**Risks**:
- ❌ Still have unnecessary complexity
- ❌ Inconsistent with industry standards
- ❌ Confusing for developers

---

## Impact Analysis

### Impact of Removing Prefix

**Files to change**:
1. `src/soni/core/scope.py:180` - Remove prefix generation
2. `src/soni/core/scope.py:297-298` - Remove prefix stripping in get_expected_slots
3. `tests/unit/test_scope.py:187-188` - Update test expectations
4. `tests/performance/test_scoping.py:78` - Update test expectations

**Breaking changes**:
- NLU training data may need retraining (if optimized with old prefix)
- Cached NLU results will be invalidated (cache keys change)

**Migration path**:
1. Update code (4 files)
2. Clear NLU cache
3. Re-run tests
4. Re-optimize NLU if using DSPy optimization

**Estimated effort**: 30 minutes

---

## Recommendation

**Remove the `"start_"` prefix entirely.**

**Rationale**:
1. **Simplicity**: Removes unnecessary complexity
2. **Industry standard**: Aligns with Rasa, DialogFlow, Lex
3. **Fixes bug**: Solves current_flow activation issue
4. **Better UX**: Cleaner, more intuitive action names
5. **Low risk**: Easy to implement, minimal breaking changes

**Alternative**: If concerned about collisions, add validation that rejects configs with flow/action name collisions.

---

## Implementation Plan

### Step 1: Remove Prefix (30 minutes)

```python
# File: src/soni/core/scope.py:180
# OLD:
actions.append(f"start_{flow_name}")
# NEW:
actions.append(flow_name)
```

### Step 2: Remove Prefix Stripping (10 minutes)

```python
# File: src/soni/core/scope.py:297-298
# OLD:
if action.startswith("start_"):
    potential_flow = action[6:]  # Remove "start_" prefix
# NEW:
if action in self.flows:
    potential_flow = action
```

### Step 3: Update Tests (20 minutes)

```python
# File: tests/unit/test_scope.py:187-188
# OLD:
assert "start_book_flight" in actions
assert "start_modify_booking" in actions
# NEW:
assert "book_flight" in actions
assert "modify_booking" in actions
```

### Step 4: Add Collision Detection (Optional, 30 minutes)

```python
# File: src/soni/core/config.py (in validation)
def validate_no_flow_action_collision(self):
    """Validate flow names don't collide with action names"""
    flow_names = set(self.flows.keys())
    action_names = set(self.actions.keys())
    collisions = flow_names & action_names

    if collisions:
        raise ConfigurationError(
            f"Flow names collide with action names: {collisions}. "
            f"Rename either the flow or the action to avoid collision."
        )
```

---

## Conclusion

The `"start_"` prefix was well-intentioned but creates more problems than it solves:

1. ❌ Breaks flow activation (current bug)
2. ❌ Adds unnecessary complexity
3. ❌ Inconsistent with industry standards
4. ❌ No real benefit

**Recommendation**: Remove the prefix entirely. This is a **quick win** that:
- Fixes a critical bug
- Simplifies the codebase
- Aligns with industry standards
- Takes only ~1 hour to implement

---

**Next Action**: Implement prefix removal as part of "Quick Wins" (Phase 0)
