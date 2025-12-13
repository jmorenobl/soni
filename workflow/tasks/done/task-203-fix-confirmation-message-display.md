## Task: 203 - Fix Confirmation Message Display After Action Execution

**ID de tarea:** 203
**Hito:** Confirmation Flow Fix
**Dependencias:** Task 201, Task 202
**Duración estimada:** 3-4 horas

### Objetivo

Fix the issue where after executing the `search_flights` action (Turn 4 in scenario 1), the system should display the confirmation message from the `ask_confirmation` step but instead shows the default response "How can I help you?".

### Contexto

In debug_scenarios.py scenario 1, Turn 4:
- User provides "Tomorrow" for departure_date
- System executes `search_flights` action successfully
- Current step advances to `ask_confirmation` (type: confirm)
- **Expected**: Display confirmation message with flight details
- **Actual**: Shows "How can I help you?" (default response)

The issue is that after action execution, the routing doesn't correctly navigate to the `confirm_action` node to display the confirmation message.

**Analysis excerpt:**
```
Turn 4: Provide date
User: "Tomorrow"
WARNING: No confirmation, booking_ref, or action_result found, using default response

State:
  Current Step: ask_confirmation
  Conversation State: idle  # ❌ Should be "ready_for_confirmation"
  All Slots Filled: True

Agent: "How can I help you?"  # ❌ Should show confirmation message
```

**References:**
- Analysis: `docs/analysis/ANALISIS_ERROR_CONFIRMACION.md` (section "Missing Confirmation Message Display")
- execute_action_node: `src/soni/dm/nodes/execute_action.py`
- route_after_action: `src/soni/dm/routing.py:528-566`
- confirm_action_node: `src/soni/dm/nodes/confirm_action.py`

### Entregables

- [ ] Trace execution flow from action completion to response generation
- [ ] Identify why conversation_state becomes "idle" instead of "ready_for_confirmation"
- [ ] Fix routing to ensure confirm_action node is reached
- [ ] Ensure confirmation message is displayed before waiting for user response
- [ ] Add integration test for action → confirmation flow
- [ ] Verify scenario 1 Turn 4 displays correct confirmation message

### Implementación Detallada

#### Paso 1: Trace the execution flow (Investigation)

**Files to investigate:**

1. **execute_action_node** (`src/soni/dm/nodes/execute_action.py`)
   - What conversation_state does it return after successful action?
   - Does it call advance_to_next_step?

2. **route_after_action** (`src/soni/dm/routing.py:528-566`)
   - How does it route based on conversation_state?
   - When does it route to "confirm_action" vs "generate_response"?

3. **FlowStepManager.advance_to_next_step** (`src/soni/flow/step_manager.py:145-201`)
   - When next step type is "confirm", does it set conversation_state="ready_for_confirmation"?

4. **FlowStepManager.advance_through_completed_steps** (`src/soni/flow/step_manager.py:280-438`)
   - Lines 411-414: Should set conversation_state="ready_for_confirmation" for confirm steps

**Action to take:**
```bash
# Add debug logging to trace the flow
# Check what conversation_state is returned at each step
```

#### Paso 2: Fix execute_action_node to advance to next step

**Archivo(s) a modificar:** `src/soni/dm/nodes/execute_action.py`

**Expected behavior:**

After executing an action:
1. Call `step_manager.advance_to_next_step(state, context)` to move to next step
2. If next step is `type: confirm`, this should set `conversation_state = "ready_for_confirmation"`
3. Return the updated conversation_state

**Código esperado (verificar si existe):**

```python
async def execute_action_node(state: DialogueState, runtime: Any) -> dict:
    """Execute action for current step."""

    # ... [action execution code] ...

    # ✅ After successful action, advance to next step
    step_manager = runtime.context["step_manager"]
    advance_updates = step_manager.advance_to_next_step(state, runtime.context)

    # advance_updates should contain:
    # - conversation_state: "ready_for_confirmation" (if next step is confirm)
    # - flow_stack: updated with new current_step

    return {
        "action_result": result,
        "flow_slots": flow_slots,
        **advance_updates,  # ✅ Include conversation_state and flow_stack
    }
```

**Si no existe, agregar:**
- Call to `step_manager.advance_to_next_step()` after action execution
- Merge the returned updates into the node's return dict

#### Paso 3: Verify route_after_action routing logic

**Archivo(s) a revisar:** `src/soni/dm/routing.py:528-566`

**Expected routing:**

```python
def route_after_action(state: DialogueStateType) -> str:
    conv_state = state.get("conversation_state")

    if conv_state == "ready_for_action":
        return "execute_action"  # Another action
    elif conv_state == "ready_for_confirmation":  # ✅ ADD THIS CASE
        return "confirm_action"
    elif conv_state == "completed":
        return "generate_response"
    # ... rest of cases
```

**Verificar:**
- Does the routing function handle "ready_for_confirmation" state?
- If not, add the case to route to "confirm_action"

#### Paso 4: Verify builder.py edge configuration

**Archivo(s) a revisar:** `src/soni/dm/builder.py`

**Check edge map in route_after_action:**

```python
# Around line 190-196
builder.add_conditional_edges(
    "execute_action",
    route_after_action,
    {
        "execute_action": "execute_action",
        "confirm_action": "confirm_action",  # ✅ Verify this exists
        "generate_response": "generate_response",
    },
)
```

**Verificar:**
- The edge map must include "confirm_action" as a target
- If missing, add it

#### Paso 5: Add debug logging (temporary, for validation)

**Archivo(s) a modificar:**
- `src/soni/dm/nodes/execute_action.py`
- `src/soni/dm/routing.py`

**Código temporal:**

```python
# In execute_action_node, after action execution:
logger.info(
    f"execute_action_node: Action completed, advancing to next step",
    extra={
        "current_step": state.get("flow_stack", [{}])[-1].get("current_step"),
        "action_name": action_name,
    }
)

advance_updates = step_manager.advance_to_next_step(state, runtime.context)

logger.info(
    f"execute_action_node: After advance_to_next_step",
    extra={
        "new_conversation_state": advance_updates.get("conversation_state"),
        "new_current_step": advance_updates.get("flow_stack", [{}])[-1].get("current_step") if advance_updates.get("flow_stack") else None,
    }
)

# In route_after_action:
logger.info(
    f"route_after_action: Routing after action execution",
    extra={
        "conversation_state": conv_state,
        "target": target,  # where we're routing to
    }
)
```

**Purpose:**
- Track exactly what happens after action execution
- Verify that conversation_state is set correctly
- Confirm routing target
- Remove after fix is validated

### Tests Requeridos

**Archivo de tests:** `tests/integration/test_confirmation_flow.py`

**Tests específicos a implementar:**

```python
import pytest
from soni.runtime import RuntimeLoop
from pathlib import Path


@pytest.mark.asyncio
async def test_action_to_confirmation_flow():
    """Test that after action execution, system displays confirmation message"""
    # Arrange
    config_path = Path("examples/flight_booking/soni.yaml")
    runtime = RuntimeLoop(config_path)
    runtime.config.settings.persistence.backend = "memory"
    await runtime._ensure_graph_initialized()

    user_id = "test_confirmation_flow"

    # Act - Complete flow up to confirmation
    await runtime.process_message("I want to book a flight", user_id)
    await runtime.process_message("Madrid", user_id)
    await runtime.process_message("Barcelona", user_id)
    response = await runtime.process_message("Tomorrow", user_id)

    # Get state
    config = {"configurable": {"thread_id": user_id}}
    snapshot = await runtime.graph.aget_state(config)
    state = snapshot.values

    # Assert
    # Check that we're at confirmation step
    flow_stack = state.get("flow_stack", [])
    assert len(flow_stack) > 0
    active_ctx = flow_stack[-1]
    assert active_ctx["current_step"] == "ask_confirmation"

    # Check conversation_state
    assert state.get("conversation_state") == "ready_for_confirmation" or state.get("conversation_state") == "confirming"

    # Check response contains confirmation message
    assert "flight" in response.lower()
    assert "Madrid" in response
    assert "Barcelona" in response
    # Should NOT be default response
    assert response != "How can I help you?"

    await runtime.cleanup()


@pytest.mark.asyncio
async def test_confirmation_message_includes_slots():
    """Test that confirmation message includes interpolated slot values"""
    # Arrange
    config_path = Path("examples/flight_booking/soni.yaml")
    runtime = RuntimeLoop(config_path)
    runtime.config.settings.persistence.backend = "memory"
    await runtime._ensure_graph_initialized()

    user_id = "test_confirmation_message"

    # Act
    await runtime.process_message("I want to book a flight", user_id)
    await runtime.process_message("New York", user_id)
    await runtime.process_message("Los Angeles", user_id)
    response = await runtime.process_message("2025-12-15", user_id)

    # Assert - Confirmation message should include slot values
    assert "New York" in response
    assert "Los Angeles" in response
    assert "2025-12-15" in response or "December" in response  # Date might be formatted
    assert "confirm" in response.lower() or "correct" in response.lower()

    await runtime.cleanup()
```

### Criterios de Éxito

- [ ] After action execution, `conversation_state` is set to `"ready_for_confirmation"`
- [ ] `route_after_action` correctly routes to `"confirm_action"` node
- [ ] `confirm_action_node` displays confirmation message with interpolated slots
- [ ] Scenario 1 Turn 4 displays confirmation message (not "How can I help you?")
- [ ] Integration tests pass
- [ ] No regressions in other scenarios
- [ ] Debug logging added temporarily for validation
- [ ] All tests pass: `uv run pytest tests/`

### Validación Manual

**Comandos para validar:**

```bash
# Run integration tests
uv run pytest tests/integration/test_confirmation_flow.py -v -s

# Run scenario 1 with debug output
uv run python scripts/debug_scenarios.py 1

# Check that Turn 4 shows confirmation message
# Expected output:
# Turn 4: Provide date
# User: "Tomorrow"
# State:
#   Current Step: ask_confirmation
#   Conversation State: ready_for_confirmation  # ✅ Fixed
# Agent: "I found flights for your trip:
#         - From: Madrid
#         - To: Barcelona
#         - Date: 2025-12-10
#         - Price: $299.99
#
#         Would you like to confirm this booking?"  # ✅ Correct message

# Run all scenarios
uv run python scripts/debug_scenarios.py
```

**Resultado esperado:**
- Turn 4 displays confirmation message with flight details
- conversation_state is "ready_for_confirmation"
- Response includes slot values (origin, destination, date, price)
- Asks user to confirm (yes/no)

### Referencias

- Analysis: `docs/analysis/ANALISIS_ERROR_CONFIRMACION.md`
- execute_action_node: `src/soni/dm/nodes/execute_action.py`
- route_after_action: `src/soni/dm/routing.py:528-566`
- confirm_action_node: `src/soni/dm/nodes/confirm_action.py`
- FlowStepManager: `src/soni/flow/step_manager.py`
- builder.py: `src/soni/dm/builder.py`

### Notas Adicionales

**Root cause hypothesis:**

The issue is likely in one of these places:

1. **execute_action_node doesn't call advance_to_next_step** after action execution
   - Fix: Add call to `step_manager.advance_to_next_step()` and merge updates

2. **route_after_action doesn't handle "ready_for_confirmation" state**
   - Fix: Add case for `conv_state == "ready_for_confirmation"` → return "confirm_action"

3. **builder.py edge map doesn't include "confirm_action" target**
   - Fix: Add "confirm_action": "confirm_action" to the edge map

**Expected flow (after fix):**

```
execute_action (search_flights completes)
  ↓ calls advance_to_next_step
  ↓ next step is "ask_confirmation" (type: confirm)
  ↓ returns conversation_state="ready_for_confirmation"
  ↓
route_after_action (sees "ready_for_confirmation")
  ↓ returns "confirm_action"
  ↓
confirm_action (displays confirmation message, uses interrupt())
  ↓ waits for user response
  ↓
[Next Turn: User says "yes"]
understand (detects message_type=CONFIRMATION)
  ↓
route_after_understand (routes to "handle_confirmation")
  ↓
handle_confirmation (extracts confirmation_value=True)
  ↓ returns conversation_state="ready_for_action"
  ↓
route_after_confirmation (routes to "execute_action")
  ↓
execute_action (confirm_booking)
```

**Debug strategy:**

1. Add logging at each step to trace the flow
2. Check what conversation_state is at each transition
3. Verify routing decisions match expected flow
4. Remove logging after fix is validated

**Related issue:**

This is separate from the infinite loop issue (Tasks 201-202). Even after fixing confirmation extraction, we need this fix to ensure the confirmation message is displayed in the first place.
