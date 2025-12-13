## Task: 6.1.5 - Remove Legacy start_ Prefix Code

**ID de tarea:** 615
**Hito:** Bug Fix - Graph Recursion Issue
**Dependencias:** Task 613 (Fix Enum Serialization)
**Duración estimada:** 1-2 horas

### Objetivo

Remove legacy code that adds `start_` prefix to flow names and the corresponding workarounds. This code was left over from a partial refactoring and causes NLU commands like "start_book_flight" instead of "book_flight".

### Contexto

**Root Cause Found:** The code in `src/soni/core/scope.py` adds `start_{flow_name}` to available actions:

```python
# Line 182-183 (LEGACY CODE)
for flow_name in self.flows.keys():
    actions.append(f"start_{flow_name}")  # ❌ This is the problem!
```

This legacy code causes:
1. NLU receives `start_book_flight` as an available action
2. NLU returns `start_book_flight` as the command
3. `handle_intent_change_node` tries to push flow `start_book_flight` (doesn't exist)
4. Graph fails or enters infinite loop

**The refactoring was partial:**
- ✅ `get_available_flows()` returns flow names directly (line 423)
- ❌ `get_available_actions()` still adds `start_` prefix (line 183)
- ❌ `get_expected_slots()` has code to handle `start_` prefix (lines 300-304)
- ❌ `activate_flow_by_intent()` in routing.py handles `start_` prefix (workaround)

### Entregables

- [ ] Remove `start_` prefix code from `get_available_actions()` in `scope.py`
- [ ] Remove `start_` prefix handling from `get_expected_slots()` in `scope.py`
- [ ] Remove `start_` prefix handling from `activate_flow_by_intent()` in `routing.py`
- [ ] Update `handle_intent_change_node` to handle unrecognized commands gracefully
- [ ] Tests verify flow names are used directly (no `start_` prefix)
- [ ] All existing tests pass (update any that depend on `start_` prefix)

### Implementación Detallada

#### Paso 1: Remove start_ Prefix from get_available_actions()

**Archivo(s) a modificar:** `src/soni/core/scope.py`

**Código específico:**

Replace lines 180-183:

```python
else:
    # No active flow - allow starting any flow
    for flow_name in self.flows.keys():
        actions.append(f"start_{flow_name}")
```

With:

```python
else:
    # No active flow - flow names are provided via get_available_flows()
    # Actions here are only action handlers, not flow triggers
    pass
```

**Explicación:**
- Flow names should come from `get_available_flows()`, not as `start_*` actions
- `get_available_actions()` should only return actual action handlers
- This removes the source of the `start_` prefix problem

#### Paso 2: Remove start_ Handling from get_expected_slots()

**Archivo(s) a modificar:** `src/soni/core/scope.py`

**Código específico:**

Replace lines 296-304:

```python
# If no flow specified, try to infer from available actions
if not flow_to_check or flow_to_check == "none":
    if available_actions:
        for action in available_actions:
            if action.startswith("start_"):
                potential_flow = action[6:]  # Remove "start_" prefix
                flow_to_check = potential_flow
                logger.debug(f"Inferred flow '{flow_to_check}' from action '{action}'")
                break
```

With:

```python
# If no flow specified, return empty list - caller should provide flow_name
if not flow_to_check or flow_to_check == "none":
    return []
```

**Explicación:**
- No need to infer flow from `start_*` actions - that pattern is being removed
- The caller should provide the flow_name directly
- This simplifies the code and removes the legacy workaround

#### Paso 3: Remove start_ Handling from activate_flow_by_intent()

**Archivo(s) a modificar:** `src/soni/dm/routing.py`

**Código específico:**

Replace lines 183-188:

```python
# 2. Handle 'start_<flow>' pattern (common NLU output)
if command.startswith("start_"):
    flow_name = command[6:]  # Remove 'start_' prefix
    if flow_name in config.flows:
        logger.info(f"Activating flow '{flow_name}' based on intent (start_ prefix)")
        return flow_name
```

With:

```python
# NOTE: start_* pattern removed - NLU now receives flow names directly
# If we still get start_* commands, log warning and try to handle
if command.startswith("start_"):
    flow_name = command[6:]
    if flow_name in config.flows:
        logger.warning(
            f"Received legacy 'start_{flow_name}' command - this pattern is deprecated. "
            f"NLU should receive flow names directly."
        )
        return flow_name
```

**Explicación:**
- Keep the handler temporarily but log a warning
- This helps identify if there are still sources of `start_*` commands
- Can be removed completely once we verify no more `start_*` commands are generated

#### Paso 4: Update handle_intent_change_node for Graceful Error Handling

**Archivo(s) a modificar:** `src/soni/dm/nodes/handle_intent_change.py`

**Código específico:**

Replace lines 31-43:

```python
command = nlu_result.get("command")
if not command:
    return {"conversation_state": "error"}

# Start new flow
flow_manager.push_flow(
    state,
    flow_name=command,
    inputs={},
    reason="intent_change",
)
```

With:

```python
command = nlu_result.get("command")
if not command:
    logger.warning("No command in NLU result for intent change")
    return {
        "conversation_state": "idle",
        "last_response": "I didn't understand what you want to do. Could you rephrase?",
    }

# Check if flow exists
config = runtime.context["config"]
if command not in config.flows:
    logger.warning(
        f"Flow '{command}' not found in config. Available flows: {list(config.flows.keys())}"
    )
    return {
        "conversation_state": "idle",
        "last_response": (
            f"I don't know how to {command}. "
            f"I can help you with: {', '.join(config.flows.keys())}"
        ),
    }

# Start new flow
flow_manager.push_flow(
    state,
    flow_name=command,
    inputs={},
    reason="intent_change",
)
```

**Explicación:**
- Check if flow exists BEFORE pushing
- Return user-friendly error if flow not found
- No normalization needed - NLU now receives correct flow names

### Tests Requeridos

**Archivo de tests:** `tests/unit/test_scope_manager.py`

**Tests específicos a implementar:**

```python
def test_get_available_actions_no_start_prefix():
    """Test that get_available_actions does NOT add start_ prefix to flow names."""
    # Arrange
    scope_manager = ScopeManager(config=config_with_flows)
    state = {"flow_stack": [], "flow_slots": {}}  # No active flow

    # Act
    actions = scope_manager.get_available_actions(state)

    # Assert
    # Should NOT have start_* actions
    assert not any(a.startswith("start_") for a in actions)

def test_get_available_flows_returns_flow_names():
    """Test that get_available_flows returns flow names directly."""
    # Arrange
    scope_manager = ScopeManager(config=config_with_flows)
    state = {"flow_stack": [], "flow_slots": {}}

    # Act
    flows = scope_manager.get_available_flows(state)

    # Assert
    assert "book_flight" in flows
    assert "start_book_flight" not in flows
```

**Archivo de tests:** `tests/unit/test_nodes_handle_intent_change.py`

```python
@pytest.mark.asyncio
async def test_handle_intent_change_rejects_unknown_flow():
    """Test that handle_intent_change rejects unknown flow names."""
    # Arrange
    state = {
        "nlu_result": {
            "command": "unknown_flow",
            "message_type": "interruption",
        },
        "flow_stack": [],
        "flow_slots": {},
    }

    # Act
    result = await handle_intent_change_node(state, runtime)

    # Assert
    assert result["conversation_state"] == "idle"
    assert "I don't know how to" in result["last_response"]
```

### Criterios de Éxito

- [ ] `get_available_actions()` does NOT add `start_` prefix
- [ ] `get_expected_slots()` does NOT handle `start_` prefix
- [ ] NLU receives flow names directly (e.g., "book_flight", not "start_book_flight")
- [ ] `handle_intent_change_node` validates flow exists before pushing
- [ ] All existing tests pass (update any that depend on `start_` prefix)
- [ ] New tests pass
- [ ] Linting passes without errors
- [ ] Type checking passes without errors

### Validación Manual

**Comandos para validar:**

```bash
# Run debug scenarios
uv run python scripts/debug_scenarios.py 1

# Verify NLU receives correct flow names
# Add logging to see what available_actions and available_flows contain

# Test that "I want to book a flight" triggers "book_flight" (not "start_book_flight")
```

**Resultado esperado:**
- NLU command is "book_flight", not "start_book_flight"
- No normalization needed in routing
- Graph executes successfully
- No recursion errors

### Referencias

- `src/soni/core/scope.py` - Contains the legacy `start_` prefix code
- `src/soni/dm/routing.py` - Contains the workaround `activate_flow_by_intent`
- `src/soni/dm/nodes/handle_intent_change.py` - Needs graceful error handling

### Notas Adicionales

**Root Cause vs Workaround:**
- Task 615 originally proposed adding normalization to handle `start_` prefix
- This was a **workaround** for the real problem
- The **real fix** is to remove the legacy code that adds the prefix

**Why This Happened:**
- Partial refactoring: `get_available_flows()` was added to return clean flow names
- But `get_available_actions()` was not updated to stop adding `start_` prefixes
- Workarounds were added in routing.py to handle the inconsistency

**NO Retrocompatibilidad (Pre-v1.0 Policy):**
- Remove the legacy code completely
- Don't keep workarounds "just in case"
- Log warnings temporarily to catch any remaining sources
- Clean code is more important than backwards compatibility before v1.0
