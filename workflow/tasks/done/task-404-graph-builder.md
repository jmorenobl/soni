## Task: 4.4 - Graph Builder

**ID de tarea:** 404
**Hito:** Phase 4 - LangGraph Integration & Dialogue Management
**Dependencias:** Task 401 (Understand Node), Task 402 (Routing Functions), Task 403 (Additional Nodes)
**Duración estimada:** 3-4 horas

### Objetivo

Build LangGraph StateGraph from configuration, assembling all nodes into an executable graph with proper routing and edges.

### Contexto

The graph builder creates the complete dialogue management graph by connecting all nodes with edges and conditional routing. It uses StateGraph with DialogueState and RuntimeContext schemas for type safety.

**Reference:** [docs/implementation/04-phase-4-langgraph.md](../../docs/implementation/04-phase-4-langgraph.md) - Task 4.4

### Entregables

- [ ] `src/soni/dm/builder.py` created with `build_graph` function
- [ ] All nodes added to graph
- [ ] Entry point: START → understand
- [ ] Conditional routing from understand node
- [ ] All edges configured correctly
- [ ] Graph compiles successfully with checkpointer
- [ ] Tests passing in `tests/integration/test_graph_builder.py`
- [ ] Mypy passes without errors

### Implementación Detallada

#### Paso 1: Create builder.py File

**Archivo(s) a crear/modificar:** `src/soni/dm/builder.py`

**Código específico:**

```python
"""Graph builder for LangGraph dialogue management."""

from typing import TYPE_CHECKING

from langgraph.checkpoint.memory import InMemorySaver
from langgraph.graph import END, START, StateGraph

if TYPE_CHECKING:
    from langgraph.checkpoint.base import BaseCheckpointSaver
    from langgraph.graph.graph import CompiledStateGraph

from soni.core.types import DialogueState, RuntimeContext
from soni.dm.nodes.understand import understand_node
from soni.dm.nodes.validate_slot import validate_slot_node
from soni.dm.nodes.collect_next_slot import collect_next_slot_node
from soni.dm.nodes.handle_intent_change import handle_intent_change_node
from soni.dm.nodes.handle_digression import handle_digression_node
from soni.dm.nodes.execute_action import execute_action_node
from soni.dm.nodes.generate_response import generate_response_node
from soni.dm.routing import route_after_understand, route_after_validate


def build_graph(
    context: RuntimeContext,
    checkpointer: BaseCheckpointSaver | None = None,
) -> CompiledStateGraph:
    """
    Build LangGraph from Soni configuration.

    Args:
        context: Runtime context with dependencies
        checkpointer: Optional checkpointer (defaults to InMemorySaver)

    Returns:
        Compiled graph ready for execution
    """
    # Create graph with schemas
    builder = StateGraph(
        state_schema=DialogueState,
        context_schema=RuntimeContext,
    )

    # Add nodes
    builder.add_node("understand", understand_node)
    builder.add_node("validate_slot", validate_slot_node)
    builder.add_node("collect_next_slot", collect_next_slot_node)
    builder.add_node("handle_intent_change", handle_intent_change_node)
    builder.add_node("handle_digression", handle_digression_node)
    builder.add_node("execute_action", execute_action_node)
    builder.add_node("generate_response", generate_response_node)

    # Entry point: START → understand (ALWAYS)
    builder.add_edge(START, "understand")

    # Conditional routing from understand
    builder.add_conditional_edges(
        "understand",
        route_after_understand,
        {
            "validate_slot": "validate_slot",
            "handle_digression": "handle_digression",
            "handle_intent_change": "handle_intent_change",
            "generate_response": "generate_response",
        },
    )

    # After digression, back to understand
    builder.add_edge("handle_digression", "understand")

    # After validating slot
    builder.add_conditional_edges(
        "validate_slot",
        route_after_validate,
        {
            "execute_action": "execute_action",
            "collect_next_slot": "collect_next_slot",
        },
    )

    # After collecting slot, back to understand
    builder.add_edge("collect_next_slot", "understand")

    # After intent change, back to understand
    builder.add_edge("handle_intent_change", "understand")

    # Action → response → END
    builder.add_edge("execute_action", "generate_response")
    builder.add_edge("generate_response", END)

    # Compile with checkpointer
    if checkpointer is None:
        checkpointer = InMemorySaver()

    return builder.compile(checkpointer=checkpointer)
```

**Explicación:**
- Create new file `src/soni/dm/builder.py`
- Import all nodes and routing functions
- Create StateGraph with DialogueState and RuntimeContext schemas
- Add all nodes to graph
- Configure entry point (START → understand)
- Add conditional edges with routing functions
- Add regular edges for sequential flow
- Compile graph with checkpointer

### Tests Requeridos

**Archivo de tests:** `tests/integration/test_graph_builder.py`

**Tests específicos a implementar:**

```python
import pytest
from soni.dm.builder import build_graph
from soni.core.state import create_initial_state
from unittest.mock import AsyncMock, MagicMock
from langgraph.checkpoint.memory import InMemorySaver

@pytest.mark.asyncio
async def test_graph_construction():
    """Test graph builds without errors."""
    # Arrange
    mock_context = {
        "flow_manager": MagicMock(),
        "nlu_provider": AsyncMock(),
        "action_handler": AsyncMock(),
        "scope_manager": MagicMock(),
        "normalizer": AsyncMock(),
    }

    # Act
    graph = build_graph(mock_context)

    # Assert
    assert graph is not None
    # Graph should be compiled
    assert hasattr(graph, "nodes")

@pytest.mark.asyncio
async def test_graph_with_checkpointer():
    """Test graph builds with custom checkpointer."""
    # Arrange
    checkpointer = InMemorySaver()
    mock_context = {
        "flow_manager": MagicMock(),
        "nlu_provider": AsyncMock(),
        "action_handler": AsyncMock(),
        "scope_manager": MagicMock(),
        "normalizer": AsyncMock(),
    }

    # Act
    graph = build_graph(mock_context, checkpointer=checkpointer)

    # Assert
    assert graph is not None

@pytest.mark.asyncio
async def test_graph_entry_point():
    """Test graph has correct entry point."""
    # Arrange
    mock_context = {
        "flow_manager": MagicMock(),
        "nlu_provider": AsyncMock(),
        "action_handler": AsyncMock(),
        "scope_manager": MagicMock(),
        "normalizer": AsyncMock(),
    }

    # Act
    graph = build_graph(mock_context)

    # Assert
    # Entry point should be understand node
    # This is verified by graph structure
    assert graph is not None
```

### Criterios de Éxito

- [ ] `build_graph` function implemented
- [ ] All nodes added to graph
- [ ] Entry point configured (START → understand)
- [ ] Conditional routing configured
- [ ] All edges configured correctly
- [ ] Graph compiles successfully
- [ ] Tests passing (`uv run pytest tests/integration/test_graph_builder.py -v`)
- [ ] Mypy passes (`uv run mypy src/soni/dm/builder.py`)
- [ ] Ruff passes (`uv run ruff check src/soni/dm/builder.py`)

### Validación Manual

**Comandos para validar:**

```bash
# Type checking
uv run mypy src/soni/dm/builder.py

# Tests
uv run pytest tests/integration/test_graph_builder.py -v

# Linting
uv run ruff check src/soni/dm/builder.py
uv run ruff format src/soni/dm/builder.py
```

**Resultado esperado:**
- Mypy shows no errors
- All tests pass
- Ruff shows no linting errors
- Graph can be built and used for execution

### Referencias

- [docs/implementation/04-phase-4-langgraph.md](../../docs/implementation/04-phase-4-langgraph.md) - Task 4.4
- [docs/design/08-langgraph-integration.md](../../docs/design/08-langgraph-integration.md) - Graph building
- [LangGraph documentation](https://langchain-ai.github.io/langgraph/) - StateGraph

### Notas Adicionales

- Graph uses StateGraph with DialogueState and RuntimeContext schemas
- Entry point is always START → understand
- Conditional edges use routing functions (synchronous)
- Regular edges connect nodes sequentially
- Graph compiles with checkpointer (defaults to InMemorySaver)
- All nodes must be imported and available
- Graph structure should match the dialogue flow design
