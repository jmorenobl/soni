## Task: 324 - Tests para Patrón CLARIFICATION

**ID de tarea:** 324
**Hito:** Fase 1 - Critical Fixes
**Dependencias:** Ninguna
**Duración estimada:** 2-3 horas
**Prioridad:** 🔴 ALTA

### Objetivo

Crear tests unitarios exhaustivos para el patrón conversacional CLARIFICATION, que actualmente tiene 0% de cobertura. Este patrón permite a los usuarios preguntar por qué se necesita cierta información antes de proporcionarla.

### Contexto

Según el informe de conformidad (`docs/analysis/INFORME_CONFORMIDAD_DISENO_TESTS.md`), el patrón CLARIFICATION es un gap crítico sin tests unitarios. El diseño especifica (`docs/design/10-dsl-specification/06-patterns.md:19`):

```
User: "Why do you need my email?"
→ Runtime detects CLARIFICATION
→ Explains why information is needed
→ Re-prompts for same slot
```

**Impacto**: ALTO - Patrón conversacional fundamental sin validación.

**Estado actual**: No existe `tests/unit/test_dm_nodes_handle_clarification.py`.

### Entregables

- [ ] Archivo `tests/unit/test_dm_nodes_handle_clarification.py` creado
- [ ] Mínimo 5 tests unitarios implementados
- [ ] Tests verifican que clarification no modifica flow_stack
- [ ] Tests verifican explicación y re-prompt del mismo slot
- [ ] Todos los tests pasan con cobertura >90% del nodo
- [ ] Tests siguen patrón AAA y usan fixtures de conftest.py

### Implementación Detallada

#### Paso 1: Crear archivo de tests

**Archivo(s) a crear:** `tests/unit/test_dm_nodes_handle_clarification.py`

**Estructura base:**

```python
"""Tests for handle_clarification node."""

import pytest
from unittest.mock import AsyncMock

from soni.core.types import DialogueState, MessageType
from soni.du.types import NLUOutput
from soni.dm.nodes.handle_clarification import handle_clarification_node


@pytest.fixture
def mock_runtime():
    """Create mock runtime context."""
    runtime = AsyncMock()
    runtime.context = {
        "step_manager": AsyncMock(),
        "response_generator": AsyncMock(),
    }
    return runtime
```

#### Paso 2: Implementar test básico de explicación

**Archivo(s) a modificar:** `tests/unit/test_dm_nodes_handle_clarification.py`

**Código específico:**

```python
async def test_handle_clarification_explains_slot(
    create_state_with_flow, mock_runtime
):
    """
    User asks why slot is needed - should explain and re-prompt.

    Design Reference: docs/design/10-dsl-specification/06-patterns.md:19
    Pattern: "Clarification: User asks why information is needed → Explain, re-prompt same slot"
    """
    # Arrange
    state = create_state_with_flow("book_flight")
    state["waiting_for_slot"] = "email"
    state["conversation_state"] = "waiting_for_slot"
    state["nlu_result"] = {
        "message_type": MessageType.CLARIFICATION.value,
        "clarification_target": "email",
    }

    # Mock step config with description
    mock_runtime.context["step_manager"].get_current_step_config.return_value = {
        "slot": "email",
        "description": "We need your email to send booking confirmation",
        "type": "collect",
    }

    # Mock response generator
    mock_runtime.context["response_generator"].generate_clarification.return_value = (
        "We need your email to send booking confirmation. "
        "What is your email address?"
    )

    # Act
    result = await handle_clarification_node(state, mock_runtime)

    # Assert
    # ✅ Debe explicar por qué se necesita el slot
    assert "booking confirmation" in result["last_response"]
    # ✅ Debe re-prompt para mismo slot
    assert result["waiting_for_slot"] == "email"
    # ✅ No debe cambiar conversation_state
    assert result["conversation_state"] == "waiting_for_slot"
```

#### Paso 3: Implementar test de preservación de flow_stack

**Archivo(s) a modificar:** `tests/unit/test_dm_nodes_handle_clarification.py`

**Código específico:**

```python
async def test_handle_clarification_preserves_flow_stack(
    create_state_with_flow, mock_runtime
):
    """
    Clarification doesn't modify flow stack (design principle).

    Design Reference: docs/design/10-dsl-specification/06-patterns.md:201
    Principle: "DigressionHandler coordinates question/help handling. Does NOT modify flow stack"
    """
    # Arrange
    state = create_state_with_flow("book_flight")
    state["waiting_for_slot"] = "email"
    original_stack = state["flow_stack"].copy()

    state["nlu_result"] = {
        "message_type": MessageType.CLARIFICATION.value,
        "clarification_target": "email",
    }

    mock_runtime.context["step_manager"].get_current_step_config.return_value = {
        "slot": "email",
        "description": "For booking confirmation",
    }

    # Act
    result = await handle_clarification_node(state, mock_runtime)

    # Assert
    # ✅ CRÍTICO: flow_stack NO debe modificarse
    assert result.get("flow_stack", state["flow_stack"]) == original_stack, \
        "Clarification must NOT modify flow stack (design principle)"
```

#### Paso 4: Implementar tests adicionales

**Tests adicionales requeridos:**

1. `test_handle_clarification_re_prompts_same_slot` - Verifica re-prompt
2. `test_handle_clarification_without_description` - Edge case sin descripción
3. `test_handle_clarification_preserves_metadata` - No limpia metadata innecesariamente
4. `test_handle_clarification_during_confirmation` - Clarification durante confirmación

### TDD Cycle (MANDATORY for new features)

#### Red Phase: Write Failing Tests

**Test file:** `tests/unit/test_dm_nodes_handle_clarification.py`

**Failing tests to write FIRST:**

```python
# Test 1: Basic clarification explanation
async def test_handle_clarification_explains_slot(...):
    """Test that clarification explains slot purpose and re-prompts."""
    # Arrange
    # Act
    # Assert
    pass  # Will fail until implemented

# Test 2: Flow stack preservation
async def test_handle_clarification_preserves_flow_stack(...):
    """Test that clarification doesn't modify flow stack."""
    # Arrange
    # Act
    # Assert
    pass  # Will fail until implemented

# Test 3: Re-prompt same slot
async def test_handle_clarification_re_prompts_same_slot(...):
    """Test that clarification re-prompts for the same slot."""
    # Arrange
    # Act
    # Assert
    pass  # Will fail until implemented
```

**Verify tests fail:**
```bash
uv run pytest tests/unit/test_dm_nodes_handle_clarification.py -v
# Expected: FAILED (node may not exist or tests incomplete)
```

**Commit:**
```bash
git add tests/unit/test_dm_nodes_handle_clarification.py
git commit -m "test: add failing tests for clarification pattern"
```

#### Green Phase: Make Tests Pass

**Implement minimal code to pass tests.**

Si el nodo `handle_clarification_node` no existe, debe crearse primero en `src/soni/dm/nodes/handle_clarification.py`.

**Verify tests pass:**
```bash
uv run pytest tests/unit/test_dm_nodes_handle_clarification.py -v
# Expected: PASSED ✅
```

**Commit:**
```bash
git add src/soni/dm/nodes/handle_clarification.py tests/
git commit -m "feat: implement clarification pattern with tests"
```

#### Refactor Phase: Improve Design

**Refactor implementation while keeping tests green.**

- Add docstrings
- Improve type hints
- Extract helper functions if needed
- Tests must still pass!

**Commit:**
```bash
git add src/
git commit -m "refactor: improve clarification node implementation"
```

---

### Tests Requeridos

**Archivo de tests:** `tests/unit/test_dm_nodes_handle_clarification.py`

**Tests específicos a implementar:**

```python
# Test 1: Basic clarification
async def test_handle_clarification_explains_slot():
    """User asks why slot is needed - should explain and re-prompt."""
    # Arrange
    # Act
    # Assert
    # - Explanation in last_response
    # - waiting_for_slot preserved
    # - conversation_state unchanged

# Test 2: Flow stack preservation (CRÍTICO)
async def test_handle_clarification_preserves_flow_stack():
    """Clarification doesn't modify flow stack."""
    # Arrange
    # Act
    # Assert
    # - flow_stack unchanged

# Test 3: Re-prompt same slot
async def test_handle_clarification_re_prompts_same_slot():
    """Clarification re-prompts for the same slot."""
    # Arrange
    # Act
    # Assert
    # - waiting_for_slot unchanged
    # - Re-prompt message generated

# Test 4: Edge case - no description
async def test_handle_clarification_without_description():
    """Clarification when step has no description."""
    # Arrange
    # Act
    # Assert
    # - Graceful handling
    # - Default explanation or error

# Test 5: During confirmation
async def test_handle_clarification_during_confirmation():
    """Clarification during confirmation step."""
    # Arrange
    # Act
    # Assert
    # - Appropriate handling
```

### Criterios de Éxito

- [ ] Archivo `test_dm_nodes_handle_clarification.py` creado
- [ ] Mínimo 5 tests implementados y pasando
- [ ] Test de preservación de flow_stack implementado y pasando
- [ ] Todos los tests usan fixtures de conftest.py
- [ ] Todos los tests siguen patrón AAA
- [ ] Cobertura del nodo >90%
- [ ] Linting pasa sin errores
- [ ] Type checking pasa sin errores

### Validación Manual

**Comandos para validar:**

```bash
# Run tests
uv run pytest tests/unit/test_dm_nodes_handle_clarification.py -v

# Check coverage
uv run pytest tests/unit/test_dm_nodes_handle_clarification.py --cov=src/soni/dm/nodes/handle_clarification --cov-report=term-missing

# Linting
uv run ruff check tests/unit/test_dm_nodes_handle_clarification.py

# Type checking
uv run mypy tests/unit/test_dm_nodes_handle_clarification.py
```

**Resultado esperado:**
- Todos los tests pasan
- Cobertura >90% del nodo handle_clarification
- Sin errores de linting o type checking

### Referencias

- `docs/analysis/INFORME_CONFORMIDAD_DISENO_TESTS.md` - Issue #1: Missing CLARIFICATION Pattern Tests
- `docs/design/10-dsl-specification/06-patterns.md:19` - Especificación del patrón
- `docs/design/05-message-flow.md` - Flujo de mensajes
- `tests/unit/conftest.py` - Fixtures disponibles

### Notas Adicionales

- **Importante**: Si el nodo `handle_clarification_node` no existe, debe crearse primero siguiendo el patrón de otros nodos como `handle_digression_node`.
- **Principio crítico**: Clarification NO debe modificar `flow_stack` (igual que digression).
- **NLU Mocking**: Todos los tests deben mockear el NLU usando fixtures de `conftest.py`.
- **Design Reference**: Agregar comentarios con referencias al diseño en cada test.
