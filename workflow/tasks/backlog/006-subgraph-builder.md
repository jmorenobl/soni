## Task: 006 - Subgraph Builder

**ID de tarea:** 006
**Hito:** 3 - Compiler
**Dependencias:** 005
**Duración estimada:** 6 horas

### Objetivo

Implement SubgraphBuilder that compiles a FlowConfig into a LangGraph StateGraph.

### Entregables

- [ ] `compiler/subgraph.py` - SubgraphBuilder class
- [ ] `compiler/edges.py` - EdgeBuilder for connecting nodes
- [ ] Linear flow compilation
- [ ] Branch handling with conditional edges
- [ ] While loop handling with back-edges
- [ ] jump_to handling
- [ ] Integration tests

### Implementación Detallada

**Archivo:** `src/soni/compiler/subgraph.py`

```python
"""Subgraph builder - compiles FlowConfig to StateGraph."""
from langgraph.graph import END, START, StateGraph
from soni.core.config import FlowConfig, StepConfig
from soni.core.types import DialogueState
from soni.compiler.nodes import get_factory_for_step


class SubgraphBuilder:
    """Builds a StateGraph from a FlowConfig."""
    
    def __init__(self, context: dict):
        self.context = context
    
    def build(self, flow_config: FlowConfig) -> StateGraph:
        """Build a StateGraph from flow configuration."""
        builder = StateGraph(DialogueState)
        steps = flow_config.steps_or_process
        
        if not steps:
            return self._build_empty_graph(builder)
        
        # Create nodes
        step_names = []
        for step in steps:
            name = step.step
            step_names.append(name)
            
            factory = get_factory_for_step(step.type)
            node_fn = factory.create(step, self.context)
            builder.add_node(name, node_fn)
        
        # Create edges
        self._add_edges(builder, steps, step_names)
        
        return builder
    
    def _add_edges(
        self,
        builder: StateGraph,
        steps: list[StepConfig],
        step_names: list[str],
    ) -> None:
        """Add edges between nodes."""
        step_set = set(step_names)
        
        # START -> first step
        builder.add_edge(START, step_names[0])
        
        for i, step in enumerate(steps):
            name = step_names[i]
            next_step = step_names[i + 1] if i < len(steps) - 1 else None
            
            # Handle jump_to
            if step.jump_to:
                target = step.jump_to if step.jump_to in step_set else END
                builder.add_edge(name, target)
                continue
            
            # Use Command pattern in nodes for branching instead of complex conditional edges here
            # But for simple linear flow, we add the default edge
            if not step.jump_to and next_step:
                builder.add_edge(name, next_step)
            elif not next_step:
                builder.add_edge(name, END)
```

**Archivo:** `src/soni/compiler/nodes/__init__.py`

```python
"""Node factory registry."""
from .base import NodeFactory
from .collect import CollectNodeFactory
from .action import ActionNodeFactory
# ... other imports

def get_factory_for_step(step_type: str) -> NodeFactory:
    """Get the appropriate factory for a step type."""
    factories = {
        "collect": CollectNodeFactory(),
        "action": ActionNodeFactory(),
        # Add others
    }
    
    factory = factories.get(step_type)
    if not factory:
        raise ValueError(f"Unknown step type: {step_type}")
        
    return factory
```

### TDD Cycle

```python
# tests/unit/compiler/test_subgraph.py
class TestSubgraphBuilder:
    def test_build_linear_flow_creates_sequential_edges(self):
        # Arrange
        config = FlowConfig(
            description="Test",
            steps=[
                StepConfig(step="a", type="say", message="A"),
                StepConfig(step="b", type="say", message="B"),
            ]
        )
        builder = SubgraphBuilder(context={})
        
        # Act
        graph = builder.build(config)
        
        # Assert
        # Graph has START -> a -> b -> END
        compiled = graph.compile()
        assert compiled is not None

    def test_build_with_jump_to_creates_edge_to_target(self):
        # Arrange
        config = FlowConfig(
            description="Test",
            steps=[
                StepConfig(step="a", type="say", message="A", jump_to="c"),
                StepConfig(step="b", type="say", message="B"),
                StepConfig(step="c", type="say", message="C"),
            ]
        )
        
        # Act
        graph = SubgraphBuilder({}).build(config)
        
        # Assert - a -> c (not b)
        compiled = graph.compile()
        assert compiled is not None
```

### Criterios de Éxito

- [ ] Linear flows compile correctly
- [ ] Branch creates conditional edges
- [ ] While creates back-edges
- [ ] jump_to creates explicit edges
- [ ] Integration tests pass
