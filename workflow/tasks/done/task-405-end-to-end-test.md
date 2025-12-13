## Task: 4.5 - End-to-End Flow Test

**ID de tarea:** 405
**Hito:** Phase 4 - LangGraph Integration & Dialogue Management
**Dependencias:** Task 404 (Graph Builder)
**Duración estimada:** 3-4 horas

### Objetivo

Create end-to-end integration test that verifies the complete dialogue flow works correctly, including interrupt/resume patterns and multiple conversation turns.

### Contexto

This test validates that all components work together: NLU, nodes, routing, and graph execution. It uses DummyLM to avoid real LLM calls and tests the complete dialogue flow with interrupts and resumption.

**Reference:** [docs/implementation/04-phase-4-langgraph.md](../../docs/implementation/04-phase-4-langgraph.md) - Task 4.5

### Entregables

- [ ] `tests/integration/test_dialogue_flow.py` created
- [ ] Test complete booking flow with interrupts
- [ ] Test multiple conversation turns
- [ ] Test interrupt/resume pattern
- [ ] Test uses DummyLM (no real LLM calls)
- [ ] All tests passing
- [ ] Mypy passes without errors

### Implementación Detallada

#### Paso 1: Create End-to-End Test File

**Archivo(s) a crear/modificar:** `tests/integration/test_dialogue_flow.py`

**Código específico:**

```python
"""End-to-end tests for dialogue flow."""

import pytest
import dspy
from dspy.utils.dummies import DummyLM
from langgraph.types import Command

from soni.dm.builder import build_graph
from soni.du.modules import SoniDU
from soni.du.provider import DSPyNLUProvider
from soni.flow.manager import FlowManager
from soni.core.state import create_initial_state
from soni.core.scope import ScopeManager
from soni.du.normalizer import SlotNormalizer
from soni.actions.base import ActionHandler
from soni.core.config import SoniConfig
from unittest.mock import MagicMock, AsyncMock


@pytest.mark.asyncio
async def test_complete_dialogue_flow():
    """Test complete booking flow with interrupts and resumption."""
    # Arrange - Set up DummyLM
    lm = DummyLM([
        # First call: Intent detection
        {
            "result": {
                "message_type": "interruption",
                "command": "book_flight",
                "slots": [],
                "confidence": 0.95,
                "reasoning": "Booking intent",
            }
        },
        # Second call: Slot extraction
        {
            "result": {
                "message_type": "slot_value",
                "command": "book_flight",
                "slots": [
                    {"name": "origin", "value": "Madrid", "confidence": 0.9}
                ],
                "confidence": 0.9,
                "reasoning": "Origin provided",
            }
        }
    ])
    dspy.configure(lm=lm)

    # Create dependencies
    nlu_module = SoniDU()
    nlu_provider = DSPyNLUProvider(nlu_module)

    # Create minimal config for testing
    config = SoniConfig(
        flows={},
        slots={},
        actions={},
        entities={},
    )

    flow_manager = FlowManager()
    scope_manager = ScopeManager(config=config)
    normalizer = SlotNormalizer(config=config)
    action_handler = ActionHandler(config=config)

    mock_action_handler = AsyncMock()
    mock_action_handler.execute.return_value = {"booking_ref": "BK-123"}

    context = {
        "flow_manager": flow_manager,
        "nlu_provider": nlu_provider,
        "action_handler": mock_action_handler,
        "scope_manager": scope_manager,
        "normalizer": normalizer,
    }

    # Build graph
    graph = build_graph(context)

    # Act - Step 1: User starts booking
    state = create_initial_state("I want to book a flight")
    config_dict = {"configurable": {"thread_id": "test-user-1"}}

    result = await graph.ainvoke(state, config=config_dict, context=context)

    # Assert - Should have started flow
    assert result is not None
    assert "nlu_result" in result or result.get("conversation_state") is not None

    # Act - Step 2: User provides origin (if interrupted)
    snapshot = await graph.aget_state(config_dict)
    if snapshot.next:
        # Interrupted - resume with user message
        result = await graph.ainvoke(
            Command(resume="Madrid"),
            config=config_dict,
            context=context,
        )

        # Assert - Flow should continue
        assert result is not None
```

**Explicación:**
- Create integration test file
- Use DummyLM to avoid real LLM calls
- Set up all dependencies (NLU, flow manager, etc.)
- Build graph using builder
- Test multiple conversation turns
- Test interrupt/resume pattern
- Verify state updates correctly

### Tests Requeridos

**Archivo de tests:** `tests/integration/test_dialogue_flow.py`

**Tests específicos a implementar:**

```python
import pytest
import dspy
from dspy.utils.dummies import DummyLM
from langgraph.types import Command

from soni.dm.builder import build_graph
from soni.du.modules import SoniDU
from soni.du.provider import DSPyNLUProvider
from soni.flow.manager import FlowManager
from soni.core.state import create_initial_state
from soni.core.scope import ScopeManager
from soni.du.normalizer import SlotNormalizer
from soni.actions.base import ActionHandler
from soni.core.config import SoniConfig
from unittest.mock import MagicMock, AsyncMock


@pytest.mark.asyncio
async def test_complete_dialogue_flow():
    """Test complete booking flow with interrupts and resumption."""
    # Arrange - Set up DummyLM
    lm = DummyLM([
        # First call: Intent detection
        {
            "result": {
                "message_type": "interruption",
                "command": "book_flight",
                "slots": [],
                "confidence": 0.95,
                "reasoning": "Booking intent",
            }
        },
        # Second call: Slot extraction
        {
            "result": {
                "message_type": "slot_value",
                "command": "book_flight",
                "slots": [
                    {"name": "origin", "value": "Madrid", "confidence": 0.9}
                ],
                "confidence": 0.9,
                "reasoning": "Origin provided",
            }
        }
    ])
    dspy.configure(lm=lm)

    # Create dependencies
    nlu_module = SoniDU()
    nlu_provider = DSPyNLUProvider(nlu_module)

    # Create minimal config for testing
    config = SoniConfig(
        flows={},
        slots={},
        actions={},
        entities={},
    )

    flow_manager = FlowManager()
    scope_manager = ScopeManager(config=config)
    normalizer = SlotNormalizer(config=config)
    action_handler = ActionHandler(config=config)

    mock_action_handler = AsyncMock()
    mock_action_handler.execute.return_value = {"booking_ref": "BK-123"}

    context = {
        "flow_manager": flow_manager,
        "nlu_provider": nlu_provider,
        "action_handler": mock_action_handler,
        "scope_manager": scope_manager,
        "normalizer": normalizer,
    }

    # Build graph
    graph = build_graph(context)

    # Act - Step 1: User starts booking
    state = create_initial_state("I want to book a flight")
    config_dict = {"configurable": {"thread_id": "test-user-1"}}

    result = await graph.ainvoke(state, config=config_dict, context=context)

    # Assert - Should have started flow
    assert result is not None
    assert "nlu_result" in result or result.get("conversation_state") is not None

    # Act - Step 2: User provides origin (if interrupted)
    snapshot = await graph.aget_state(config_dict)
    if snapshot.next:
        # Interrupted - resume with user message
        result = await graph.ainvoke(
            Command(resume="Madrid"),
            config=config_dict,
            context=context,
        )

        # Assert - Flow should continue
        assert result is not None

@pytest.mark.asyncio
async def test_multiple_turns():
    """Test multiple conversation turns."""
    # Arrange
    lm = DummyLM([
        {"result": {"message_type": "interruption", "command": "greet", "slots": []}},
        {"result": {"message_type": "slot_value", "command": "book_flight", "slots": []}},
    ])
    dspy.configure(lm=lm)

    # ... (similar setup as above)

    # Act & Assert
    # Test multiple turns of conversation
    pass
```

### Criterios de Éxito

- [ ] End-to-end test implemented
- [ ] Test uses DummyLM (no real LLM calls)
- [ ] Test complete dialogue flow
- [ ] Test interrupt/resume pattern
- [ ] Test multiple conversation turns
- [ ] Tests passing (`uv run pytest tests/integration/test_dialogue_flow.py -v`)
- [ ] Mypy passes (`uv run mypy tests/integration/test_dialogue_flow.py`)
- [ ] Ruff passes (`uv run ruff check tests/integration/test_dialogue_flow.py`)

### Validación Manual

**Comandos para validar:**

```bash
# Type checking
uv run mypy tests/integration/test_dialogue_flow.py

# Tests
uv run pytest tests/integration/test_dialogue_flow.py -v

# Linting
uv run ruff check tests/integration/test_dialogue_flow.py
uv run ruff format tests/integration/test_dialogue_flow.py
```

**Resultado esperado:**
- Mypy shows no errors
- All tests pass
- Ruff shows no linting errors
- End-to-end flow works correctly

### Referencias

- [docs/implementation/04-phase-4-langgraph.md](../../docs/implementation/04-phase-4-langgraph.md) - Task 4.5
- [docs/design/08-langgraph-integration.md](../../docs/design/08-langgraph-integration.md) - interrupt() pattern
- [DSPy documentation](https://dspy-docs.vercel.app/) - DummyLM

### Notas Adicionales

- Use DummyLM to avoid real LLM calls in tests
- Test interrupt/resume pattern with `Command(resume=...)`
- Test multiple conversation turns
- Verify state updates correctly between turns
- Use minimal SoniConfig for testing
- Mock action handler to avoid real action execution
- Tests should be deterministic (no random behavior)
