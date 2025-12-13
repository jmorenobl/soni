## Task: 1.2 - Protocol Interfaces

**ID de tarea:** 102
**Hito:** Phase 1 - Core Foundation
**Dependencias:** Task 101 (Core Type Definitions)
**Duración estimada:** 2-3 horas

### Objetivo

Define Protocol interfaces for all major components following the Dependency Inversion Principle. This allows the framework to depend on abstractions rather than concrete implementations.

### Contexto

Protocol interfaces enable dependency injection and make the codebase more testable and maintainable. All major components (NLU, Actions, Flow Management, etc.) will implement these protocols, allowing for easy mocking and swapping of implementations.

**Reference:** [docs/implementation/01-phase-1-foundation.md](../../docs/implementation/01-phase-1-foundation.md) - Task 1.2

### Entregables

- [ ] All Protocol interfaces defined in `src/soni/core/interfaces.py`
- [ ] INLUProvider protocol with understand method
- [ ] IActionHandler protocol with execute method
- [ ] IScopeManager protocol with get_available_actions and get_available_flows methods
- [ ] INormalizer protocol with normalize method
- [ ] IFlowManager protocol with all flow management methods
- [ ] All methods have complete type hints
- [ ] Docstrings present for all protocols and methods
- [ ] No circular imports
- [ ] Mypy passes without errors
- [ ] Tests passing in `tests/unit/test_interfaces.py`

### Implementación Detallada

#### Paso 1: Create interfaces.py File

**Archivo(s) a crear/modificar:** `src/soni/core/interfaces.py`

**Código específico:**

```python
from typing import Protocol, Any
from soni.core.types import DialogueState, FlowContext

class INLUProvider(Protocol):
    """Interface for NLU providers."""

    async def understand(
        self,
        user_message: str,
        dialogue_context: dict[str, Any]
    ) -> dict[str, Any]:
        """Understand user message and return NLU result."""
        ...

class IActionHandler(Protocol):
    """Interface for action execution."""

    async def execute(
        self,
        action_name: str,
        inputs: dict[str, Any]
    ) -> dict[str, Any]:
        """Execute an action and return results."""
        ...

class IScopeManager(Protocol):
    """Interface for scope management (dynamic action filtering)."""

    def get_available_actions(
        self,
        state: DialogueState
    ) -> list[str]:
        """Get available actions based on current state."""
        ...

    def get_available_flows(
        self,
        state: DialogueState
    ) -> list[str]:
        """Get available flows based on current state."""
        ...

class INormalizer(Protocol):
    """Interface for value normalization."""

    async def normalize(
        self,
        slot_name: str,
        raw_value: Any
    ) -> Any:
        """Normalize and validate slot value."""
        ...

class IFlowManager(Protocol):
    """Interface for flow stack management."""

    def push_flow(
        self,
        state: DialogueState,
        flow_name: str,
        inputs: dict[str, Any] | None = None,
        reason: str | None = None
    ) -> str:
        """Start a new flow instance."""
        ...

    def pop_flow(
        self,
        state: DialogueState,
        outputs: dict[str, Any] | None = None,
        result: str = "completed"
    ) -> None:
        """Finish current flow instance."""
        ...

    def get_active_context(
        self,
        state: DialogueState
    ) -> FlowContext | None:
        """Get the currently active flow context."""
        ...

    def get_slot(
        self,
        state: DialogueState,
        slot_name: str
    ) -> Any:
        """Get slot value from active flow."""
        ...

    def set_slot(
        self,
        state: DialogueState,
        slot_name: str,
        value: Any
    ) -> None:
        """Set slot value in active flow."""
        ...
```

**Explicación:**
- Create interfaces.py file with all Protocol definitions
- Use `Protocol` from typing for structural subtyping
- All methods must be async where appropriate (NLU, Actions, Normalizer)
- Use proper type hints with DialogueState and FlowContext from types.py
- Use `...` as method body (Protocol requirement)
- Add docstrings for all protocols and methods

#### Paso 2: Create Unit Tests

**Archivo(s) a crear/modificar:** `tests/unit/test_interfaces.py`

**Código específico:**

```python
import pytest
from soni.core.interfaces import INLUProvider, IFlowManager
from soni.core.types import DialogueState

def test_protocol_type_checking():
    """Test that protocols can be used for type hints."""
    # Arrange
    def process_with_nlu(nlu: INLUProvider) -> None:
        """Function accepting INLUProvider."""
        pass

    # Act & Assert - This should not raise type errors
    # (actual implementation test will be in integration)
    assert INLUProvider is not None
```

**Explicación:**
- Create basic tests to verify protocols can be imported
- Test that protocols can be used as type hints
- Full implementation tests will be in integration tests when concrete implementations exist

### Tests Requeridos

**Archivo de tests:** `tests/unit/test_interfaces.py`

**Tests específicos a implementar:**

```python
import pytest
from soni.core.interfaces import (
    INLUProvider,
    IActionHandler,
    IScopeManager,
    INormalizer,
    IFlowManager
)
from soni.core.types import DialogueState

def test_protocol_type_checking():
    """Test that protocols can be used for type hints."""
    # Arrange
    def process_with_nlu(nlu: INLUProvider) -> None:
        """Function accepting INLUProvider."""
        pass

    # Act & Assert - This should not raise type errors
    # (actual implementation test will be in integration)
    assert INLUProvider is not None

def test_all_protocols_importable():
    """Test that all protocols can be imported."""
    # Arrange & Act
    protocols = [
        INLUProvider,
        IActionHandler,
        IScopeManager,
        INormalizer,
        IFlowManager
    ]

    # Assert
    assert len(protocols) == 5
    assert all(protocol is not None for protocol in protocols)
```

### Criterios de Éxito

- [ ] All Protocol interfaces defined
- [ ] Methods have complete type hints
- [ ] Docstrings present for all protocols and methods
- [ ] No circular imports
- [ ] Mypy passes (`uv run mypy src/soni/core/interfaces.py`)
- [ ] Tests passing (`uv run pytest tests/unit/test_interfaces.py -v`)
- [ ] Ruff passes (`uv run ruff check src/soni/core/interfaces.py`)

### Validación Manual

**Comandos para validar:**

```bash
# Type checking
uv run mypy src/soni/core/interfaces.py

# Tests
uv run pytest tests/unit/test_interfaces.py -v

# Linting
uv run ruff check src/soni/core/interfaces.py
uv run ruff format src/soni/core/interfaces.py
```

**Resultado esperado:**
- Mypy shows no errors
- All tests pass
- Ruff shows no linting errors
- Protocols can be imported and used as type hints
- No circular dependency issues

### Referencias

- [docs/implementation/01-phase-1-foundation.md](../../docs/implementation/01-phase-1-foundation.md) - Task 1.2
- [Python Protocol documentation](https://docs.python.org/3/library/typing.html#typing.Protocol)
- [Dependency Inversion Principle](https://en.wikipedia.org/wiki/Dependency_inversion_principle)

### Notas Adicionales

- Protocols use structural subtyping (duck typing with type checking)
- Methods marked with `...` are required by Protocol syntax
- All async methods must be properly typed
- IFlowManager methods are sync (operate on state directly)
- INLUProvider, IActionHandler, and INormalizer are async (may involve I/O)
- IScopeManager is sync (pure logic based on state)
