## Task: 003 - Allow DU Injection in RuntimeLoop

**ID de tarea:** 003
**Hito:** Testability
**Dependencias:** Ninguna
**Duración estimada:** 1 hora

### Objetivo

Permitir inyectar un `DUProtocol` personalizado en `RuntimeLoop` para mejorar la testabilidad y permitir proveedores NLU alternativos.

### Contexto

Actualmente `RuntimeLoop.__init__()` no acepta parámetro `du`:

```python
def __init__(self, config, checkpointer=None, registry=None):
    # du se crea hardcodeado en initialize()
    self._du = SoniDU.create_with_best_model(use_cot=True)
```

Esto dificulta:
1. Tests unitarios (requieren mock de SoniDU interno)
2. Uso de proveedores NLU alternativos
3. Configuración de parámetros DSPy desde fuera

### Entregables

- [ ] Añadir parámetro `du: DUProtocol | None = None` al constructor
- [ ] Usar el DU inyectado si se proporciona
- [ ] Crear DU por defecto solo si no se inyecta
- [ ] Tests unitarios verificando inyección

### Implementación Detallada

#### Paso 1: Actualizar constructor

**Archivo(s) a modificar:** `src/soni/runtime/loop.py`

```python
def __init__(
    self,
    config: SoniConfig,
    checkpointer: BaseCheckpointSaver | None = None,
    registry: ActionRegistry | None = None,
    du: DUProtocol | None = None,  # NEW PARAMETER
):
    self.config = config
    self.checkpointer = checkpointer
    self._initial_registry = registry
    self._custom_du = du  # Store injected DU

    # ... rest unchanged
```

#### Paso 2: Actualizar initialize()

```python
async def initialize(self) -> None:
    if self._graph:
        return

    self._flow_manager = FlowManager()

    # Use injected DU or create default
    if self._custom_du:
        self._du = self._custom_du
    else:
        self._du = SoniDU.create_with_best_model(use_cot=True)

    # ... rest unchanged
```

### TDD Cycle (MANDATORY)

#### Red Phase: Write Failing Tests

**Test file:** `tests/unit/runtime/test_loop_di.py`

```python
import pytest
from unittest.mock import AsyncMock, MagicMock

from soni.core.config import SoniConfig
from soni.core.types import DUProtocol
from soni.runtime.loop import RuntimeLoop


@pytest.fixture
def minimal_config():
    """Create minimal SoniConfig for testing."""
    return SoniConfig(flows={})


class TestRuntimeLoopDI:
    """Tests for RuntimeLoop dependency injection."""

    @pytest.mark.asyncio
    async def test_accepts_custom_du_parameter(self, minimal_config):
        """Test that RuntimeLoop accepts du parameter."""
        # Arrange
        mock_du = MagicMock(spec=DUProtocol)

        # Act - should not raise
        loop = RuntimeLoop(minimal_config, du=mock_du)

        # Assert
        assert loop._custom_du is mock_du

    @pytest.mark.asyncio
    async def test_uses_injected_du_after_initialize(self, minimal_config):
        """Test that injected DU is used instead of default."""
        # Arrange
        mock_du = MagicMock(spec=DUProtocol)
        mock_du.aforward = AsyncMock()

        loop = RuntimeLoop(minimal_config, du=mock_du)

        # Act
        await loop.initialize()

        # Assert
        assert loop.du is mock_du

    @pytest.mark.asyncio
    async def test_creates_default_du_when_not_injected(self, minimal_config):
        """Test that default DU is created when none injected."""
        # Arrange
        loop = RuntimeLoop(minimal_config)

        # Act
        await loop.initialize()

        # Assert
        from soni.du.modules import SoniDU
        assert isinstance(loop.du, SoniDU)
```

**Verify tests fail:**
```bash
uv run pytest tests/unit/runtime/test_loop_di.py -v
# Expected: FAILED (du parameter doesn't exist)
```

#### Green Phase: Make Tests Pass

Implementar los cambios en `RuntimeLoop`.

```bash
uv run pytest tests/unit/runtime/test_loop_di.py -v
# Expected: PASSED ✅
```

### Criterios de Éxito

- [ ] `RuntimeLoop(config, du=my_du)` funciona
- [ ] DU inyectado se usa en `process_message()`
- [ ] Si no se inyecta, crea `SoniDU` por defecto
- [ ] `uv run pytest` pasa
- [ ] `uv run ruff check .` sin errores
- [ ] `uv run mypy src/soni` sin errores

### Validación Manual

```bash
uv run pytest tests/unit/runtime/ -v
uv run ruff check src/soni/runtime/
uv run mypy src/soni/runtime/
```

### Referencias

- `src/soni/runtime/loop.py:37-59` - Constructor actual
- `src/soni/core/types.py:136-148` - DUProtocol
