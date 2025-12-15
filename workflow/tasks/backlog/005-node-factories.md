## Task: 005 - Node Factories

**ID de tarea:** 005
**Hito:** 3 - Compiler
**Dependencias:** 004
**Duración estimada:** 8 horas

### Objetivo

Implement NodeFactory pattern - one factory per step type that generates LangGraph nodes.

### Entregables

- [ ] `compiler/nodes/base.py` - NodeFactory protocol
- [ ] `compiler/nodes/collect.py` - CollectNodeFactory
- [ ] `compiler/nodes/action.py` - ActionNodeFactory
- [ ] `compiler/nodes/branch.py` - BranchNodeFactory
- [ ] `compiler/nodes/confirm.py` - ConfirmNodeFactory
- [ ] `compiler/nodes/say.py` - SayNodeFactory
- [ ] `compiler/nodes/while_loop.py` - WhileNodeFactory
- [ ] Unit tests for each factory

### Implementación Detallada

**Archivo:** `src/soni/compiler/nodes/base.py`

```python
"""Base protocol for node factories."""
from typing import Any, Callable, Protocol
from soni.core.config import StepConfig
from soni.core.types import DialogueState


NodeFunction = Callable[[DialogueState], dict[str, Any]]


class NodeFactory(Protocol):
    """Protocol for step type node factories."""
    
    def create(self, step: StepConfig, context: Any) -> NodeFunction:
        """Create a node function for the given step config."""
        ...
```

**Archivo:** `src/soni/compiler/nodes/collect.py`

```python
"""CollectNodeFactory - generates collect step nodes."""
from typing import Any
from soni.core.config import StepConfig
from soni.core.types import DialogueState
from soni.compiler.nodes.base import NodeFunction


class CollectNodeFactory:
    """Factory for collect step nodes."""
    
    def create(self, step: StepConfig, context: Any) -> NodeFunction:
        """Create a node that collects a slot value."""
        slot_name = step.slot
        prompt = step.message or f"Please provide {slot_name}"
        
        async def collect_node(state: DialogueState) -> dict[str, Any]:
            # Check if slot already filled
            flow_manager = context["flow_manager"]
            value = flow_manager.get_slot(state, slot_name)
            
            if value is not None:
                return {"flow_state": "active"}
            
            return {
                "flow_state": "waiting_input",
                "waiting_for_slot": slot_name,
                "response": prompt,
            }
        
        collect_node.__name__ = f"collect_{step.step}"
        return collect_node
```

### TDD Cycle

```python
# tests/unit/compiler/test_node_factories.py
class TestCollectNodeFactory:
    @pytest.mark.asyncio
    async def test_collect_node_prompts_when_slot_empty(self):
        # Arrange
        step = StepConfig(step="get_origin", type="collect", slot="origin")
        factory = CollectNodeFactory()
        mock_context = {"flow_manager": MockFlowManager(slots={})}
        
        # Act
        node = factory.create(step, mock_context)
        result = await node(create_empty_dialogue_state())
        
        # Assert
        assert result["flow_state"] == "waiting_input"
        assert result["waiting_for_slot"] == "origin"

    @pytest.mark.asyncio
    async def test_collect_node_continues_when_slot_filled(self):
        # Arrange
        step = StepConfig(step="get_origin", type="collect", slot="origin")
        factory = CollectNodeFactory()
        mock_context = {"flow_manager": MockFlowManager(slots={"origin": "NYC"})}
        
        # Act
        node = factory.create(step, mock_context)
        result = await node(create_empty_dialogue_state())
        
        # Assert
        assert result["flow_state"] == "active"
```

### Criterios de Éxito

- [ ] All 6 factories implemented
- [ ] Each factory follows SOLID principles
- [ ] Nodes are pure functions (no side effects except state)
- [ ] Tests pass for each factory
