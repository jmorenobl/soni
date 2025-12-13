## Task: 305 - Create State Access Helper Functions

**ID de tarea:** 305
**Hito:** Technical Debt Repayment - LOW
**Dependencias:** Ninguna
**Duración estimada:** 4-6 horas
**Prioridad:** 🟢 LOW - Can be done gradually
**Related DEBT:** DEBT-005

### Objetivo

Crear funciones helper consistentes en `src/soni/core/state.py` para acceder al estado, eliminando el patrón de acceso directo `state.get()` disperso por todo el código y reduciendo acoplamiento con la estructura del estado.

### Contexto

**Problema:**
Acceso directo a state usando `state.get()` en múltiples lugares:
```python
nlu_result = state.get("nlu_result") or {}
metadata = state.get("metadata", {})
flow_stack = state.get("flow_stack", [])
conversation_state = state.get("conversation_state")
```

**Helpers existentes (parciales):**
- `get_slot()` ✅
- `get_all_slots()` ✅

**Faltantes:**
- `get_nlu_result()`
- `get_metadata()`
- `get_conversation_state()`
- `get_flow_stack()`
- `get_current_flow_context()`

**Referencias:**
- Technical Debt: `docs/technical-debt.md` (DEBT-005)
- DIP (Dependency Inversion Principle)
- File: `src/soni/core/state.py`

### Entregables

- [ ] Helper functions agregadas a `src/soni/core/state.py`
- [ ] Consistent defaults para cada helper
- [ ] Docstrings completos
- [ ] Nodos actualizados para usar helpers (gradual, no obligatorio en este task)
- [ ] Tests unitarios para helpers
- [ ] Export en `__all__`

### Implementación Detallada

#### Paso 1: Agregar helpers a state.py

**Archivo a modificar:** `src/soni/core/state.py`

**Agregar después de las funciones existentes get_slot/get_all_slots:**

```python
# ============================================================================
# State Access Helpers (consistent defaults, reduces coupling)
# ============================================================================


def get_nlu_result(state: DialogueState | dict[str, Any]) -> dict[str, Any]:
    """Get NLU result from state with consistent defaults.

    Args:
        state: Current dialogue state

    Returns:
        NLU result dictionary, or empty dict if not set
    """
    nlu_result = state.get("nlu_result")
    return nlu_result if nlu_result is not None else {}


def get_metadata(state: DialogueState | dict[str, Any]) -> dict[str, Any]:
    """Get metadata from state with consistent defaults.

    Args:
        state: Current dialogue state

    Returns:
        Metadata dictionary, or empty dict if not set
    """
    return state.get("metadata", {})


def get_conversation_state(
    state: DialogueState | dict[str, Any],
    default: str = "idle"
) -> str:
    """Get conversation state with consistent defaults.

    Args:
        state: Current dialogue state
        default: Default conversation state if not set (default: "idle")

    Returns:
        Conversation state string
    """
    return state.get("conversation_state", default)


def get_flow_stack(state: DialogueState | dict[str, Any]) -> list[Any]:
    """Get flow stack from state with consistent defaults.

    Args:
        state: Current dialogue state

    Returns:
        Flow stack list, or empty list if not set
    """
    return state.get("flow_stack", [])


def get_current_flow_context(state: DialogueState | dict[str, Any]) -> dict[str, Any] | None:
    """Get current (top) flow context from stack.

    Args:
        state: Current dialogue state

    Returns:
        Current flow context dict, or None if stack is empty
    """
    flow_stack = get_flow_stack(state)
    return flow_stack[-1] if flow_stack else None


def get_user_message(state: DialogueState | dict[str, Any]) -> str:
    """Get user message from state.

    Args:
        state: Current dialogue state

    Returns:
        User message string, or empty string if not set
    """
    return state.get("user_message", "")


def get_last_response(state: DialogueState | dict[str, Any]) -> str:
    """Get last response from state.

    Args:
        state: Current dialogue state

    Returns:
        Last response string, or empty string if not set
    """
    return state.get("last_response", "")


def get_action_result(state: DialogueState | dict[str, Any]) -> Any:
    """Get action result from state.

    Args:
        state: Current dialogue state

    Returns:
        Action result (can be any type), or None if not set
    """
    return state.get("action_result")
```

#### Paso 2: Exportar en __all__

**En el mismo archivo `src/soni/core/state.py`, actualizar `__all__`:**

```python
__all__ = [
    # Existing exports...
    "get_slot",
    "get_all_slots",
    # New exports
    "get_nlu_result",
    "get_metadata",
    "get_conversation_state",
    "get_flow_stack",
    "get_current_flow_context",
    "get_user_message",
    "get_last_response",
    "get_action_result",
]
```

#### Paso 3: Ejemplo de uso en un nodo (opcional, para demostrar)

**Archivo a actualizar (ejemplo):** `src/soni/dm/nodes/understand.py`

**BEFORE:**
```python
nlu_result = state.get("nlu_result") or {}
metadata = state.get("metadata", {}).copy()
```

**AFTER:**
```python
from soni.core.state import get_nlu_result, get_metadata

nlu_result = get_nlu_result(state)
metadata = get_metadata(state).copy()
```

**NOTA:** Este paso es opcional en este task. Puede hacerse gradualmente en futuras PRs.

### Tests Requeridos

**Archivo:** `tests/unit/core/test_state_helpers.py`

```python
"""Tests for state access helper functions."""

import pytest
from soni.core.state import (
    get_nlu_result,
    get_metadata,
    get_conversation_state,
    get_flow_stack,
    get_current_flow_context,
    get_user_message,
    get_last_response,
    get_action_result,
)


class TestGetNLUResult:
    """Tests for get_nlu_result helper."""

    def test_returns_nlu_result_when_present(self):
        """Test returns NLU result when present in state."""
        state = {"nlu_result": {"intent": "book_flight"}}
        result = get_nlu_result(state)
        assert result == {"intent": "book_flight"}

    def test_returns_empty_dict_when_none(self):
        """Test returns empty dict when nlu_result is None."""
        state = {"nlu_result": None}
        result = get_nlu_result(state)
        assert result == {}

    def test_returns_empty_dict_when_missing(self):
        """Test returns empty dict when nlu_result not in state."""
        state = {}
        result = get_nlu_result(state)
        assert result == {}


class TestGetMetadata:
    """Tests for get_metadata helper."""

    def test_returns_metadata_when_present(self):
        """Test returns metadata when present."""
        state = {"metadata": {"key": "value"}}
        result = get_metadata(state)
        assert result == {"key": "value"}

    def test_returns_empty_dict_when_missing(self):
        """Test returns empty dict when metadata not in state."""
        state = {}
        result = get_metadata(state)
        assert result == {}


class TestGetConversationState:
    """Tests for get_conversation_state helper."""

    def test_returns_state_when_present(self):
        """Test returns conversation state when present."""
        state = {"conversation_state": "understanding"}
        result = get_conversation_state(state)
        assert result == "understanding"

    def test_returns_default_when_missing(self):
        """Test returns 'idle' default when missing."""
        state = {}
        result = get_conversation_state(state)
        assert result == "idle"

    def test_returns_custom_default(self):
        """Test returns custom default when specified."""
        state = {}
        result = get_conversation_state(state, default="custom")
        assert result == "custom"


class TestGetFlowStack:
    """Tests for get_flow_stack helper."""

    def test_returns_flow_stack_when_present(self):
        """Test returns flow stack when present."""
        stack = [{"flow_id": "flow1"}]
        state = {"flow_stack": stack}
        result = get_flow_stack(state)
        assert result == stack

    def test_returns_empty_list_when_missing(self):
        """Test returns empty list when missing."""
        state = {}
        result = get_flow_stack(state)
        assert result == []


class TestGetCurrentFlowContext:
    """Tests for get_current_flow_context helper."""

    def test_returns_top_flow_when_stack_not_empty(self):
        """Test returns top flow from stack."""
        state = {
            "flow_stack": [
                {"flow_id": "flow1"},
                {"flow_id": "flow2"},  # This should be returned
            ]
        }
        result = get_current_flow_context(state)
        assert result == {"flow_id": "flow2"}

    def test_returns_none_when_stack_empty(self):
        """Test returns None when flow stack is empty."""
        state = {"flow_stack": []}
        result = get_current_flow_context(state)
        assert result is None

    def test_returns_none_when_stack_missing(self):
        """Test returns None when flow_stack not in state."""
        state = {}
        result = get_current_flow_context(state)
        assert result is None


class TestOtherHelpers:
    """Tests for other state helpers."""

    def test_get_user_message(self):
        """Test get_user_message helper."""
        state = {"user_message": "hello"}
        assert get_user_message(state) == "hello"
        assert get_user_message({}) == ""

    def test_get_last_response(self):
        """Test get_last_response helper."""
        state = {"last_response": "How can I help?"}
        assert get_last_response(state) == "How can I help?"
        assert get_last_response({}) == ""

    def test_get_action_result(self):
        """Test get_action_result helper."""
        state = {"action_result": {"status": "success"}}
        assert get_action_result(state) == {"status": "success"}
        assert get_action_result({}) is None
```

### Criterios de Éxito

- [ ] Helper functions agregadas a `src/soni/core/state.py`
- [ ] All helpers have docstrings
- [ ] All helpers exported in `__all__`
- [ ] Tests para cada helper (20+ tests)
- [ ] Test coverage >= 95% for new helpers
- [ ] Mypy passes
- [ ] Ruff passes
- [ ] Documentation menciona uso de helpers (opcional)

### Validación Manual

```bash
# 1. Run new tests
uv run pytest tests/unit/core/test_state_helpers.py -v --cov=src/soni/core/state

# 2. Type check
uv run mypy src/soni/core/state.py

# 3. Lint
uv run ruff check src/soni/core/state.py

# 4. Verify imports work
python -c "from soni.core.state import get_nlu_result, get_metadata; print('✅ Imports work')"
```

### Referencias

- **Technical Debt:** `docs/technical-debt.md` (DEBT-005)
- **DIP:** Robert C. Martin's "Clean Architecture"
- **Existing Helpers:** `src/soni/core/state.py` (get_slot, get_all_slots)

### Notas Adicionales

**Gradual Adoption:**
- Este task crea los helpers
- La migración de nodos puede hacerse gradualmente en futuras PRs
- No es necesario actualizar todos los nodos en este task
- Prioridad: usar helpers en NUEVOS nodos primero

**Benefits:**
- Consistent defaults across codebase
- Single source of truth for state access patterns
- Easier to refactor state structure later
- Better testability (can mock helpers)
- Reduced coupling to state dict structure

**Future Extension:**
Si la estructura del state cambia:
- Solo actualizar helpers, no 50+ archivos
- Helpers pueden agregar validación
- Helpers pueden agregar logging/debugging
