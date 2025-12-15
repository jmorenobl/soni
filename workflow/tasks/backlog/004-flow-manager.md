## Task: 004 - Flow Manager

**ID de tarea:** 004
**Hito:** 2 - Flow Management
**Dependencias:** 001, 002, 003
**Duración estimada:** 6 horas

### Objetivo

Implement FlowManager for managing the flow stack (push, pop, get_active, set_slot).

### Entregables

- [ ] `flow/manager.py` with FlowManager class
- [ ] `flow/state.py` with state helper functions
- [ ] Flow stack operations (push, pop, get_active_context)
- [ ] Slot management (set_slot, get_slot, get_all_slots)
- [ ] Unit tests with nested flow scenarios

### Implementación Detallada

**Archivo:** `src/soni/flow/manager.py`

```python
"""Flow stack management."""
import uuid
import time
from soni.core.types import DialogueState, FlowContext
from soni.core.errors import FlowStackError


class FlowManager:
    """Manages the flow stack and slot data."""
    
    def push_flow(
        self,
        state: DialogueState,
        flow_name: str,
        inputs: dict | None = None,
    ) -> str:
        """Push a new flow onto the stack.
        
        Returns the flow_id of the new flow.
        """
        flow_id = str(uuid.uuid4())
        
        context: FlowContext = {
            "flow_id": flow_id,
            "flow_name": flow_name,
            "flow_state": "active",
            "current_step": None,
            "step_index": 0,
            "outputs": {},
            "started_at": time.time(),
        }
        
        state["flow_stack"].append(context)
        state["flow_slots"][flow_id] = inputs or {}
        
        return flow_id
    
    def pop_flow(
        self,
        state: DialogueState,
        result: str = "completed",
    ) -> FlowContext:
        """Pop the top flow from the stack.
        
        Raises FlowStackError if stack is empty.
        """
        if not state["flow_stack"]:
            raise FlowStackError("Cannot pop from empty flow stack")
        
        context = state["flow_stack"].pop()
        context["flow_state"] = result
        
        return context
    
    def get_active_context(self, state: DialogueState) -> FlowContext | None:
        """Get the currently active flow context."""
        if not state["flow_stack"]:
            return None
        return state["flow_stack"][-1]
    
    def set_slot(
        self,
        state: DialogueState,
        slot_name: str,
        value: any,
    ) -> None:
        """Set a slot value for the active flow."""
        context = self.get_active_context(state)
        if context:
            flow_id = context["flow_id"]
            if flow_id not in state["flow_slots"]:
                state["flow_slots"][flow_id] = {}
            state["flow_slots"][flow_id][slot_name] = value
    
    def get_slot(
        self,
        state: DialogueState,
        slot_name: str,
    ) -> any:
        """Get a slot value from the active flow."""
        context = self.get_active_context(state)
        if context:
            flow_id = context["flow_id"]
            return state["flow_slots"].get(flow_id, {}).get(slot_name)
        return None
    
    def get_all_slots(self, state: DialogueState) -> dict:
        """Get all slots for the active flow."""
        context = self.get_active_context(state)
        if context:
            return state["flow_slots"].get(context["flow_id"], {})
        return {}
```

### TDD Cycle

```python
# tests/unit/flow/test_manager.py
class TestFlowManagerPushFlow:
    def test_push_flow_creates_context_on_empty_stack(self):
        # Arrange
        state = create_empty_dialogue_state()
        manager = FlowManager()
        
        # Act
        flow_id = manager.push_flow(state, "book_flight")
        
        # Assert
        assert len(state["flow_stack"]) == 1
        assert state["flow_stack"][0]["flow_name"] == "book_flight"

    def test_push_flow_with_inputs_stores_slots(self):
        # Arrange
        state = create_empty_dialogue_state()
        manager = FlowManager()
        
        # Act
        flow_id = manager.push_flow(state, "book_flight", inputs={"origin": "NYC"})
        
        # Assert
        assert state["flow_slots"][flow_id]["origin"] == "NYC"


class TestFlowManagerPopFlow:
    def test_pop_flow_on_empty_stack_raises_error(self):
        # Arrange
        state = create_empty_dialogue_state()
        manager = FlowManager()
        
        # Act & Assert
        with pytest.raises(FlowStackError):
            manager.pop_flow(state)
```

### Criterios de Éxito

- [ ] push_flow creates new context with UUID
- [ ] pop_flow removes top and returns it
- [ ] Slots isolated by flow_id
- [ ] 3+ level nested flow test passes
- [ ] Tests pass: `pytest tests/unit/flow/ -v`
