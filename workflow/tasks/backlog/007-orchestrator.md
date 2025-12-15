## Task: 007 - Orchestrator Graph

**ID de tarea:** 007
**Hito:** 4 - Dialogue Management
**Dependencias:** 006
**Duración estimada:** 6 horas

### Objetivo

Implement OrchestratorGraph that coordinates flow subgraphs and manages the main dialogue loop.

### Entregables

- [ ] `dm/orchestrator.py` - OrchestratorGraph class
- [ ] `dm/routing.py` - Command-driven routing
- [ ] `dm/nodes/understand.py` - NLU node
- [ ] `dm/nodes/execute.py` - Command execution node
- [ ] `dm/nodes/respond.py` - Response generation node
- [ ] Integration tests for flow switching

### Implementación Detallada

**Archivo:** `src/soni/dm/orchestrator.py`

```python
"""Orchestrator graph - coordinates flow subgraphs."""
from typing import Literal
from langgraph.graph import END, START, StateGraph, Command
from soni.core.config import SoniConfig
from soni.core.types import DialogueState, RuntimeContext
from soni.compiler.subgraph import SubgraphBuilder
from soni.dm.nodes import understand_node, execute_node, respond_node


class OrchestratorGraph:
    """Main dialogue graph that orchestrates flow subgraphs.
    
    Uses Runtime DI via context_schema=RuntimeContext.
    Uses Command for state updates combined with routing.
    """
    
    def __init__(self, config: SoniConfig, context: RuntimeContext):
        self.config = config
        self.context = context
        self.flow_subgraphs: dict[str, StateGraph] = {}
    
    def compile_flows(self) -> None:
        """Compile all flows to subgraphs."""
        # Pass context.du.config/etc if needed by builder
        builder = SubgraphBuilder(self.context)
        
        for flow_name, flow_config in self.config.flows.items():
            subgraph = builder.build(flow_config)
            self.flow_subgraphs[flow_name] = subgraph
    
    def build(self) -> StateGraph:
        """Build the orchestrator graph."""
        self.compile_flows()
        
        # Initialize graph with context_schema for Dependency Injection
        builder = StateGraph(DialogueState, context_schema=RuntimeContext)
        
        # Core nodes
        builder.add_node("understand", understand_node)
        builder.add_node("execute", execute_node)
        builder.add_node("respond", respond_node)
        
        # Flow subgraph nodes
        for flow_name, subgraph in self.flow_subgraphs.items():
            builder.add_node(f"flow_{flow_name}", subgraph.compile())
        
        # Edges
        # execute_node returns Command[Literal[...]], so traditional edges 
        # from "execute" are replaced by the Command's goto logic
        builder.add_edge(START, "understand")
        builder.add_edge("understand", "execute")
        
        # Edges from flows back to respond (flows must end or return correct Command)
        for flow_name in self.flow_subgraphs:
            builder.add_edge(f"flow_{flow_name}", "respond")
        
        builder.add_edge("respond", END)
        
        return builder

# dm/nodes/execute.py would look like this:
# 
# def execute_node(
#     state: DialogueState,
#     runtime: Runtime[RuntimeContext]
# ) -> Command[Literal["respond", "flow_..."]]:
#     ...
#     return Command(goto=f"flow_{name}", update=...)
```

### TDD Cycle

```python
# tests/unit/dm/test_orchestrator.py
class TestOrchestratorGraph:
    def test_compile_flows_creates_subgraph_per_flow(self):
        # Arrange
        config = SoniConfig(flows={
            "flow_a": FlowConfig(description="A", steps=[]),
            "flow_b": FlowConfig(description="B", steps=[]),
        })
        orchestrator = OrchestratorGraph(config, context={})
        
        # Act
        orchestrator.compile_flows()
        
        # Assert
        assert "flow_a" in orchestrator.flow_subgraphs
        assert "flow_b" in orchestrator.flow_subgraphs

    def test_build_creates_graph_with_core_nodes(self):
        # Arrange
        config = SoniConfig(flows={})
        orchestrator = OrchestratorGraph(config, {})
        
        # Act
        graph = orchestrator.build()
        
        # Assert
        compiled = graph.compile()
        assert compiled is not None
```

### Criterios de Éxito

- [ ] Flows compile to subgraphs
- [ ] Routing based on flow_stack
- [ ] Flow transitions work
- [ ] Integration tests pass
